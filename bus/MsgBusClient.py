#!/usr/bin/python
import asyncio
import datetime
import json
import logging
import os
import time
import websockets
import threading
from queue import Queue
from bus.Message import Message, msg_from_json
from framework.util.utils import LOG

async def SendThread(ws, outbound_q, client_id):
  try:
    while True:
      while outbound_q.empty():
        await asyncio.sleep(0.001)
      msg = outbound_q.get()
      await ws.send(msg)
  except websockets.exceptions.ConnectionClosedOK:
    print(f"SendThread: Connection closed gracefully for {client_id}")
  except Exception as e:
    print(f"SendThread: Error in SendThread for {client_id}: {e}")

async def RecvThread(ws, callback, client_id):
  try:
    while True:
      message = await ws.recv()
      print(f"Received message: {message}")
      msg = json.loads(message)
      print(f"msg: {msg}")
      parsed_msg = msg_from_json(msg)
      print(f"parsed_msg: {parsed_msg}")
      callback(parsed_msg)
  except websockets.ConnectionClosed:
    print(f"Warning! socket closed. Exiting RecvThread = {client_id}")
  except json.JSONDecodeError:
    print(f"Warning! JSON decode error. Exiting RecvThread = {client_id}")
  except Exception as e:
    print(f"Warning! Error: {e}. Exiting RecvThread = {client_id}: {e}")

class MsgBusClient:
  def __init__(self, client_id):
    self.ws = None
    self.inbound_q = Queue()
    self.outbound_q = Queue()
    self.client_id = client_id
    self.base_dir = str(os.getenv('SVA_BASE_DIR'))
    log_filename = self.base_dir + '/logs/messages.log'
    self.log = LOG(log_filename).log
    self.log.debug(f"MsgBusClient.__init__() client_id: {self.client_id}")
    logging.getLogger('websockets').setLevel(logging.WARNING) # suppress DEBUG logs from websockets
    self.msg_handlers = {}
    self.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(self.loop)
    self.connect_task = self.loop.create_task(self.connect())
    self.loop.run_until_complete(self.connect_task) # wait for connect to finish.
    self.rcv_thread = threading.Thread(target=self.run_recv_thread)
    self.process_thread = threading.Thread(target=self.run_process_thread)
    self.snd_thread = threading.Thread(target=self.run_send_thread)
    self.rcv_thread.start()
    self.process_thread.start()
    self.snd_thread.start()

  async def connect(self):
    self.ws = await websockets.connect(f"ws://localhost:8181/{self.client_id}")

  def run_recv_thread(self):
    asyncio.run_coroutine_threadsafe(RecvThread(self.ws, self.rcv_client_msg, self.client_id), self.loop)

  def run_process_thread(self):
    while True:
      while self.inbound_q.empty():
        time.sleep(0.001)
      msg = self.inbound_q.get()
      self.log.debug(f"MsgBusClient(().run_process_thread() client_id: {self.client_id} msg: {msg}")
      if self.msg_handlers.get(msg['msg_type'], None) is not None:
        self.msg_handlers[msg['msg_type']](msg)
      else:
        pass

  def run_send_thread(self):
    asyncio.run_coroutine_threadsafe(SendThread(self.ws, self.outbound_q, self.client_id), self.loop)

  def on(self, msg_type, callback):
    self.msg_handlers[msg_type] = callback

  def rcv_client_msg(self, msg):
    # print(f"rcv_client_msg() msg: {msg}")
    self.inbound_q.put(msg)

  def send(self, msg_type, target, msg):
    # print(f"send_client_msg() msg_type: {msg_type} target: {target} msg: {msg}")
    self.outbound_q.put(json.dumps(Message(msg_type, self.client_id, target, msg)))

  def close(self):
    if self.ws:
      asyncio.run_coroutine_threadsafe(self.ws.close(), self.loop)
    self.loop.call_soon_threadsafe(self.loop.stop)
    self.rcv_thread.join()
    self.process_thread.join()
    self.snd_thread.join()
    self.loop.close()
    
