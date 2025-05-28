import asyncio
import datetime 
import json
import logging
import os 
import threading
import redis.asyncio as redis 
from framework.util.utils import LOG

class Message:
  def __init__(self, msg_type, source, target, payload):
    self.data = {
      "msg_type": msg_type,
      "source": source,
      "target": target,
      "payload": payload,
      # uncomment to get a timestamp in every message
      # "timestamp": datetime.datetime.utcnow().isoformat() 
    }

  def __getitem__(self, key):
    return self.data[key]

  def to_json(self):
    return json.dumps(self.data)

def msg_from_json(json_input):
  # Parses a JSON string or a dictionary into a message object (here, a dictionary).
  if isinstance(json_input, str):
    data = json.loads(json_input)
  elif isinstance(json_input, dict):
    data = json_input
  else:
    raise TypeError("Input must be a JSON string or a dictionary")
  return data                              # Return a dictionary

class MsgBus:
  def __init__(self, client_id, redis_host="localhost", redis_port=6379):
    self.client_id = client_id
    self.redis_host = redis_host
    self.redis_port = redis_port
    self.base_dir = str(os.getenv("SVA_BASE_DIR"))
    log_filename = self.base_dir + "/logs/messages.log"
    self.log = LOG(log_filename).log
    self.log.debug(f"MsgBus.__init__() client_id: {self.client_id}")
    logging.getLogger("asyncio").setLevel(logging.WARNING) # fewer msgs from asyncio
    self.redis_conn = None
    self.pubsub_client = None
    self.listener_task = None # For the pubsub listener
    self.inbound_q = asyncio.Queue()
    self.outbound_q = asyncio.Queue()
    self.msg_handlers = {}
    self.loop = asyncio.new_event_loop()
    self.shutdown_event = asyncio.Event()
    self._core_tasks = [] # To keep track of publisher/processor tasks
    self.event_loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
    self.event_loop_thread.start()

    # Initialize resources and start tasks, blocking __init__ until basic setup is done
    init_future = asyncio.run_coroutine_threadsafe(self.init_core_tasks(), self.loop)
    try:
      init_future.result(timeout=10) # Block for up to 10 seconds
      # self.log.info(f"MsgBus.__init__() Initialization complete. Listening on channel: {self._get_client_channel()}")
    except Exception as e:
      self.log.error(f"MsgBus.__init__() Failed during initialization: {e}")
      self.loop.call_soon_threadsafe(self.loop.stop) # Signal loop to stop
      if self.event_loop_thread.is_alive():
        self.event_loop_thread.join(timeout=2)
      if self.redis_conn: # Try to close if it was created
          close_future = asyncio.run_coroutine_threadsafe(self.redis_conn.close(), self.loop)
          try:
              close_future.result(timeout=1)
          except Exception:
              pass                         # ignore errors during cleanup on init failure
      raise ConnectionError(f"MsgBus for {self.client_id} failed to initialize: {e}") from e

  def _run_event_loop(self):
    asyncio.set_event_loop(self.loop)
    try:
      # self.log.debug("MsgBus._run_event_loop(): Event loop started.")
      self.loop.run_forever()
    except Exception as e:
      self.log.error(f"MsgBus._run_event_loop(): Event loop crashed: {e}")
    finally:
      self.log.debug("MsgBus._run_event_loop(): Event loop shutting down.")
      if not self.shutdown_event.is_set(): # loop stopped unexpectedly
        pending = [task for task in asyncio.all_tasks(loop=self.loop) if task is not asyncio.current_task()]
        if pending:
          self.log.debug(f"MsgBus._run_event_loop(): Cancelling {len(pending)} outstanding tasks.")
          for task in pending:
            task.cancel()
          # self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True)) # This might be tricky here
      # Ensure loop is closed if it"s still running due to run_until_complete calls in finally
      # This part is complex, primarily `loop.stop()` should be called from another thread or `call_soon_threadsafe`
      # And `loop.close()` after `run_forever` completes.
      # self.log.debug("MsgBus._run_event_loop(): Event loop finished.")

  async def init_core_tasks(self):
    # self.log.debug("MsgBus.init_core_tasks(): Connecting to Redis...")
    self.redis_conn = redis.Redis(
      host=self.redis_host,
      port=self.redis_port,
    )
    try:
      await self.redis_conn.ping()
      # self.log.info("MsgBus.init_core_tasks(): Successfully connected to Redis.")
    except Exception as e:
      self.log.error(f"MsgBus.init_core_tasks(): Redis ping failed: {e}")
      if self.redis_conn:
        await self.redis_conn.close()      # Clean up connection if ping fails
      raise

    # Start the Pub/Sub listener
    self.pubsub_client = self.redis_conn.pubsub()
    await self.pubsub_client.subscribe(self._get_client_channel())
    self.listener_task = self.loop.create_task(self._subscriber_loop())
    # self.log.debug("MsgBus.init_core_tasks(): Subscriber loop task created.")

    # Start other core tasks
    self._core_tasks.append(self.loop.create_task(self._publisher_loop()))
    self._core_tasks.append(self.loop.create_task(self._processor_loop()))
    # self.log.debug("MsgBus.init_core_tasks(): Publisher and Processor loop tasks created.")

  def _get_client_channel(self):
    return f"bus:channel:{self.client_id}"

  def _get_target_channel(self, target_client_id):
    return f"bus:channel:{target_client_id}"

  async def _subscriber_loop(self):
    # self.log.debug(f"MsgBus._subscriber_loop(): Subscriber loop started. Listening on {self._get_client_channel()}")
    try:
      while not self.shutdown_event.is_set():
        try:
          # timeout helps to periodically check shutdown_event
          message = await self.pubsub_client.get_message(ignore_subscribe_messages=True, timeout=1.0)
          if message and message.get("type") == "message":
            try:
              msg_data_str = message["data"].decode("utf-8") # assumes messages are UTF-8 encoded JSON strings
              # self.log.debug(f"MsgBus._subscriber_loop(): Received raw message")
              parsed_msg = msg_from_json(msg_data_str)
              await self.inbound_q.put(parsed_msg)
            except json.JSONDecodeError:
              self.log.error(f'MsgBus._subscriber_loop(): JSON decode for message: {message["data"]}')
            except Exception as e:
              self.log.error(f"MsgBus._subscriber_loop(): Error message: {e}")
          elif message is None and self.shutdown_event.is_set(): # Timeout and shutdown requested
            break
        except redis.exceptions.ConnectionError as e:
          self.log.error(f"MsgBus._subscriber_loop(): Subscriber Redis connection error: {e}. Attempting to reconnect...")
          await asyncio.sleep(5)           # wait before retrying (implement more robust backoff later)
          try:
            if self.pubsub_client: await self.pubsub_client.close() # Close old pubsub
            if self.redis_conn: await self.redis_conn.close() # Close old connection
            self.redis_conn = redis.asyncio.Redis(host=self.redis_host, port=self.redis_port)
            await self.redis_conn.ping()
            self.pubsub_client = self.redis_conn.pubsub()
            await self.pubsub_client.subscribe(self._get_client_channel())
            # self.log.info("MsgBus._subscriber_loop(): Reconnected to Redis and resubscribed.")
          except Exception as recon_e:
            self.log.error(f"MsgBus._subscriber_loop(): Failed to reconnect to Redis: {recon_e}")
            await asyncio.sleep(5)         # wait before next attempt
        except asyncio.CancelledError:
          self.log.debug("MsgBus._subscriber_loop(): Subscriber loop cancelled.")
          break
        except Exception as e:
          self.log.error(f"MsgBus._subscriber_loop(): Unexpected error in subscriber loop: {e}")
          if self.shutdown_event.is_set(): break
          await asyncio.sleep(1)           # avoid tight loop on unexpected errors
    finally:
      self.log.debug("MsgBus._subscriber_loop(): Subscriber loop stopped.")
      if self.pubsub_client:
        try:
          await self.pubsub_client.unsubscribe(self._get_client_channel())
          await self.pubsub_client.close()
        except Exception as e:
          self.log.error(f"MsgBus._subscriber_loop(): Error closing pubsub client: {e}")

  async def _publisher_loop(self):
    # self.log.debug("MsgBus._publisher_loop(): Publisher loop started.")
    try:
      while not self.shutdown_event.is_set() or not self.outbound_q.empty():
        try:                               # wait for an item with a timeout to allow checking shutdown_event
          message_to_send = await asyncio.wait_for(self.outbound_q.get(), timeout=1.0)
          if message_to_send:
            target_channel, json_payload = message_to_send
            # self.log.debug(f"MsgBus._publisher_loop(): Publishing to {target_channel}: {json_payload}")
            await self.redis_conn.publish(target_channel, json_payload)
            self.outbound_q.task_done()
        except asyncio.TimeoutError:
          if self.shutdown_event.is_set() and self.outbound_q.empty():
            break                          # exit if shutdown and queue is empty
          continue                         # loop again to check shutdown_event or wait for message
        except redis.exceptions.ConnectionError as e:
            self.log.error(f"MsgBus._publisher_loop(): Redis connection error: {e}. Message might be lost or requeued if logic added.")
            # Basic recovery: wait and hope connection returns for next message.
            # For critical messages, add retry or dead-letter queue logic.
            await asyncio.sleep(5)
        except asyncio.CancelledError:
          self.log.debug("MsgBus._publisher_loop(): Publisher loop cancelled.")
          # Potentially requeue messages from outbound_q if needed
          break
        except Exception as e:
          self.log.error(f"MsgBus._publisher_loop(): Error in publisher loop: {e}")
          if self.shutdown_event.is_set(): break
          await asyncio.sleep(1) # Avoid tight loop on unexpected errors
    finally:
      self.log.debug("MsgBus._publisher_loop(): Publisher loop stopped.")

  async def _processor_loop(self):
    # self.log.debug("MsgBus._processor_loop(): Processor loop started.")
    try:
      while not self.shutdown_event.is_set() or not self.inbound_q.empty():
        try:                               # wait for an item with a timeout
          msg = await asyncio.wait_for(self.inbound_q.get(), timeout=1.0)
          if msg:
            # self.log.debug(f"MsgBus._processor_loop(): Processing msg")
            msg_type = msg.get("msg_type") 
            if msg_type and self.msg_handlers.get(msg_type):
              try:
                self.msg_handlers[msg_type](msg) # Call the registered handler
              except Exception as e:
                self.log.error(f"MsgBus._processor_loop(): Error in msg_type {msg_type}: {e} msg: {msg}")
            else:
              self.log.warning(f"MsgBus._processor_loop(): No handler for msg_type: {msg_type} or msg_type is None.")
            self.inbound_q.task_done()
        except asyncio.TimeoutError:
          if self.shutdown_event.is_set() and self.inbound_q.empty():
            break
          continue
        except asyncio.CancelledError:
          self.log.debug("MsgBus._processor_loop(): Processor loop cancelled.")
          break
        except Exception as e:
          self.log.error(f"MsgBus._processor_loop(): Error in processor loop: {e}")
          if self.shutdown_event.is_set(): break
          await asyncio.sleep(1)
    finally:
      self.log.debug("MsgBus._processor_loop(): Processor loop stopped.")

  def on(self, msg_type, callback):
    # Register a callback for a specific message type
    self.log.debug(f"MsgBus.on(): Registering handler for msg_type: {msg_type}")
    self.msg_handlers[msg_type] = callback

  def send(self, msg_type, target_client_id, payload):
    # Send a message to a target client
    if self.shutdown_event.is_set():
      self.log.warning("MsgBus.send(): Shutdown in progress. Cannot send message.")
      return
    message_obj = Message(
      msg_type=msg_type,
      source=self.client_id,
      target=target_client_id,
      payload=payload
    )
    json_payload = message_obj.to_json() # Serialize the message to JSON
    target_channel = self._get_target_channel(target_client_id)
    # next line commented as it adds lots of log entries
    # self.log.debug(f"MsgBus.send(): Queueing message for {target_channel}: {json_payload}")
    # Put (channel, payload) tuple onto the outbound queue
    try:
      # If send() is called from the event loop"s thread, put_nowait is fine.
      # If called from external threads (likely), use run_coroutine_threadsafe.
      if threading.get_ident() == self.event_loop_thread.ident:
          self.outbound_q.put_nowait((target_channel, json_payload))
      else:
          asyncio.run_coroutine_threadsafe(
              self.outbound_q.put((target_channel, json_payload)),
              self.loop
          ).result(timeout=5)              # add timeout to prevent indefinite blocking
    except asyncio.QueueFull:
        self.log.error(f"MsgBus.send(): Outbound queue is full. Message to {target_channel} dropped.")
    except Exception as e:
        self.log.error(f"MsgBus.send(): Failed to queue message for {target_channel}: {e}")

  def close(self):
    self.log.info("MsgBus.close(): Initiating shutdown...")
    if self.shutdown_event.is_set():
      self.log.warning("MsgBus.close(): Shutdown already in progress.")
      return
    if self.loop.is_running():             # Signal all async tasks to stop
      self.loop.call_soon_threadsafe(self.shutdown_event.set)
    else:                                  # loop isn"t running, can"t use call_soon_threadsafe effectively
      self.shutdown_event.set() # Set it synchronously, tasks might not see it if loop dead
    # Wait for the core tasks (publisher, processor) to finish
    # These tasks check shutdown_event and queue emptiness.
    # The subscriber_loop (self.listener_task) is handled separately due to pubsub.get_message blocking.
    # Cancel and await tasks
    all_tasks_to_wait_for = []
    if self.listener_task and not self.listener_task.done():
        all_tasks_to_wait_for.append(self.listener_task)
    for task in self._core_tasks:
      if task and not task.done():
        # task.cancel() # Optionally cancel if they don"t exit via shutdown_event quickly
        all_tasks_to_wait_for.append(task)
    if all_tasks_to_wait_for and self.loop.is_running():
        self.log.debug(f"MsgBus.close(): Waiting for {len(all_tasks_to_wait_for)} tasks to complete...")
        # Create a future to await these tasks from the calling thread
        tasks_done_future = asyncio.run_coroutine_threadsafe(
            asyncio.gather(*all_tasks_to_wait_for, return_exceptions=True),
            self.loop
        )
        try:
            tasks_done_future.result(timeout=10) # Wait for tasks to finish
            self.log.debug("MsgBus.close(): Core tasks completed.")
        except asyncio.TimeoutError:
            self.log.warning("MsgBus.close(): Timeout waiting for tasks to complete during close. Forcing cancellation.")
            for task_future in all_tasks_to_wait_for: # Iterate over original list of tasks
                if not task_future.done(): # Check if it"s actually a future/task object
                    # This cancellation is from the external thread via run_coroutine_threadsafe
                    cancel_future = asyncio.run_coroutine_threadsafe(self._cancel_task(task_future), self.loop)
                    try:
                        cancel_future.result(timeout=2)
                    except Exception as e_cancel:
                        self.log.error(f"MsgBus.close(): Error cancelling task: {e_cancel}")
        except Exception as e:
            self.log.error(f"MsgBus.close(): Error waiting for tasks during close: {e}")
    if self.redis_conn:                     # close Redis connection
      self.log.debug("MsgBus.close(): Closing Redis connection.")
      if self.loop.is_running():
        close_future = asyncio.run_coroutine_threadsafe(self.redis_conn.close(), self.loop)
        try:
          close_future.result(timeout=5)
          # self.log.debug("MsgBus.close(): connection closed.")
        except Exception as e:
          self.log.error(f"MsgBus.close(): Error closing connection: {e}")
      else:                                # Fallback if loop is not running
        try:
          self.log.warning("MsgBus.close(): Loop not running, cannot call async redis_conn.close().")
        except Exception as e:
          self.log.error(f"MsgBus.close(): Error trying to close Redis connection without running loop: {e}")
    if self.loop.is_running():             # Stop the event loop itself
      # self.log.debug("MsgBus.close(): Stopping event loop.")
      self.loop.call_soon_threadsafe(self.loop.stop)
    if self.event_loop_thread.is_alive():      # Wait for the event loop thread to finish
      # self.log.debug("MsgBus.close(): Joining event loop thread.")
      self.event_loop_thread.join(timeout=5)
      if self.event_loop_thread.is_alive():
        self.log.warning("MsgBus.close(): Event loop thread did not join cleanly.")
    if not self.loop.is_closed():
      self.log.debug("MsgBus.close(): Closing asyncio loop object.")
      pass                                 # loop should close itself when _run_event_loop() finishes.
    self.log.info("MsgBus.close(): MsgBus closed.")

  async def _cancel_task(self, task):
    if task and not task.done():
        task.cancel()
        try:
            await task                     # allow cancellation to propagate
        except asyncio.CancelledError:
            self.log.debug(f'(MsgBus._cancel_task(): {task.get_name() if hasattr(task, "get_name") else "unknown"} successfully cancelled.')
        except Exception as e:
            self.log.error(f'MsgBus._cancel_task(): Exception during task cancellation wait for {task.get_name() if hasattr(task, "get_name") else "unknown"}: {e}')

