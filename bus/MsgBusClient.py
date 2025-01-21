import asyncio
import json
from bus.Message import Message, msg_from_json
import os
from asyncio import Queue
from framework.util.utils import LOG, Config
import websockets.asyncio
from websockets.asyncio.client import connect

async def SendThread(ws, outbound_q, client_id):
  while True:
    while outbound_q.empty():
      await asyncio.sleep(0.001)           # asyncio-friendly sleep
    msg = await outbound_q.get()
    await ws.send(msg)


async def RecvThread(ws, callback, client_id):
  while True:
    try:
      message = await ws.recv()
      print(f"RecvThread received message: {message}") 
      await callback(msg_from_json(json.loads(message)))
    except websockets.exceptions.ConnectionClosed as e:
      print(f"Connection closed: {e}")
      break
    except Exception as e:
      print(f"Error in RecvThread: {e}")
      break

async def process_inbound_messages(inbound_q, msg_handlers, client_id):
  while True:
    while inbound_q.empty():
      await asyncio.sleep(0.001)
    msg = await inbound_q.get()
    print(f"Processing message: {msg.msg_type} handlers: {msg_handlers.keys()}")  # Debug
    if msg.msg_type in msg_handlers:
      msg_handlers[msg.msg_type](msg)
    else:
      print(f"No handler found for message type: {msg.msg_type}")  # Debug

class MsgBusClient:
  def __init__(self, client_id):
    self.client_id = client_id
    self.base_dir = str(os.getenv('SVA_BASE_DIR'))
    log_filename = self.base_dir + '/logs/bus.log'
    self.log = LOG(log_filename).log
    self.log.debug(f"MsgBusClient.__init__(): Initialized for client_id: {self.client_id} log_filename: {log_filename}")
    self.inbound_q = Queue()
    self.outbound_q = Queue()
    self.msg_handlers = {}
    self.ws = None                         # webSocket connection placeholder

  async def connect_and_run(self):         # create webSocket connection
    self.log.debug(f"MsgBusClient.connect_and_run(): Starting connection for client_id: {self.client_id}")
    try:
      self.ws = await connect(f"ws://localhost:8181/{self.client_id}")
      self.log.debug(f"MsgBusClient.connect_and_run(): WebSocket connected for {self.client_id}")
      recv_task = asyncio.create_task(RecvThread(self.ws, self.rcv_client_msg, self.client_id)) # Create and log each task
      self.log.debug("MsgBusClient.connect_and_run(): RecvThread task created")
      send_task = asyncio.create_task(SendThread(self.ws, self.outbound_q, self.client_id))
      self.log.debug("MsgBusClient.connect_and_run(): SendThread task created")
      process_task = asyncio.create_task(process_inbound_messages(self.inbound_q, self.msg_handlers, self.client_id))
      self.log.debug("MsgBusClient.connect_and_run(): process_inbound_messages task created")
    except Exception as e:
      self.log.error(f"MsgBusClient.connect_and_run(): Connection error: {e}")
  
  def on(self, msg_type, callback):
    self.msg_handlers[msg_type] = callback
    self.log.debug(f"MsgBusClient.on(): Registered callback for msg_type: {msg_type}")

  async def rcv_client_msg(self, msg):
    self.log.debug(f"MsgBusClient.rcv_client_msg(): msg: {msg}")
    await self.inbound_q.put(msg)

  async def send(self, msg_type, target, msg):
    self.log.debug(f"MsgBusClient.send(): msg_type: {msg_type} target: {target} msg: {msg} client_id: {self.client_id}")
    await self.outbound_q.put(json.dumps(Message(msg_type, self.client_id, target, msg)))

  async def close(self):
    await self.ws.close()

# main() 

