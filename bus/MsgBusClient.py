import asyncio
import json
from bus.Message import Message, msg_from_json
import os
from asyncio import Queue
from framework.util.utils import LOG, Config
from websockets import connect

async def SendThread(ws, outbound_q, client_id):
  while True:
    while outbound_q.empty():
      await asyncio.sleep(0.001)           # asyncio-friendly sleep
    msg = await outbound_q.get()
    await ws.send(msg)

async def RecvThread(ws, callback, client_id):
  while True:
    try:
      message = await ws.recv()            # await recv
      callback(msg_from_json(json.loads(message)))
    except Exception as e:
      print(f"Error in RecvThread: {e}")
      break

async def process_inbound_messages(inbound_q, msg_handlers, client_id):
  while True:
    while inbound_q.empty():
      await asyncio.sleep(0.001)
    msg = inbound_q.get()
    if msg_handlers.get(msg['msg_type']):
      msg_handlers[msg['msg_type']](msg)

class MsgBusClient:
  def __init__(self, client_id):
    self.client_id = client_id
    self.base_dir = str(os.getenv('SVA_BASE_DIR'))
    log_filename = self.base_dir + '/logs/bus.log'
    self.log = LOG(log_filename).log
    self.log.debug(f"MsgBusClient.__init__(): Initialized for client_id: {self.client_id}")

    self.inbound_q = Queue()
    self.outbound_q = Queue()
    self.msg_handlers = {}
    self.ws = None                         # webSocket connection placeholder

  async def connect_and_run(self):         # create webSocket connection
    try:
      self.ws = await connect(f"ws://localhost:8181/{self.client_id}")
      self.log.debug(f"MsgBusClient.connect_and_run(): Connected to client_id: {self.client_id}")

      # create asyncio tasks
      asyncio.create_task(RecvThread(self.ws, self.rcv_client_msg, self.client_id))
      asyncio.create_task(SendThread(self.ws, self.outbound_q, self.client_id))
      asyncio.create_task(process_inbound_messages(self.inbound_q, self.msg_handlers, self.client_id))
    except Exception as e:
      self.log.error(f"MsgBusClient.connect_and_run(): Connection error: {e}")

  def on(self, msg_type, callback):
    self.msg_handlers[msg_type] = callback
    self.log.debug(f"MsgBusClient.on(): Registered handler for msg_type: {msg_type}")

  def rcv_client_msg(self, msg):
    self.inbound_q.put(msg)

  async def send(self, msg_type, target, msg):
    await self.outbound_q.put(json.dumps(Message(msg_type, self.client_id, target, msg)))
    self.log.debug(f"MsgBusClient.send(): Sending message: {msg}")

  async def close(self):
    await self.ws.close()

