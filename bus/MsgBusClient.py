import asyncio
import datetime
import json
import paho.mqtt.client as mqtt
from queue import Queue
import threading
import time
from collections import defaultdict

class Message(dict):
  def __init__(self, msg_type, source, target, data):
    self.msg_type = msg_type
    self.source = source
    self.target = target
    self.data = data
    dict.__init__(self, msg_type=msg_type, source=source, target=target, data=data,
                  ts=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def msg_from_json(packet):
  m = Message(packet['msg_type'], packet['source'], packet['target'], packet['data'])
  m.ts = packet['ts']
  return m

async def SendThread(mqtt_client, outbound_q, client_id):
  while True:
    while outbound_q.empty():
      time.sleep(0.001)
    msg = outbound_q.get()
    mqtt_client.publish(msg['msg_type'], json.dumps(msg))  # Send message to the appropriate topic
    print(f"client_id: {client_id} sent msg: {msg}")

def process_inbound_messages(inbound_q, msg_handlers, client_id):
  while True:
    while inbound_q.empty():
      time.sleep(0.001)
    msg = inbound_q.get()
    print(f"[{client_id}] received: {msg}")
    if msg_handlers.get(msg['msg_type'], None) is not None:
      msg_handlers[msg['msg_type']](msg)
    else:
      print(f"Warning! No message handler registered for msg: {msg}")

def snd_bridge(mqtt_client, outbound_q, client_id):
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  loop.run_until_complete(SendThread(mqtt_client, outbound_q, client_id))
  loop.close()

class MsgBusClient:
  _instances = {}

  def __new__(cls, client_id, *args, **kwargs):
    if client_id in cls._instances:
      return cls._instances[client_id]
    instance = super().__new__(cls)
    cls._instances[client_id] = instance
    return instance

  def __init__(self, client_id, broker="localhost", port=1883):
    self.inbound_q = Queue()
    self.outbound_q = Queue()
    self.msg_handlers = {}
    self.client_id = client_id
    self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id)
    self.client.on_connect = self.on_connect
    self.client.on_message = self.on_message  # Handle received messages
    self.handlers = defaultdict(list)

    # Start worker threads
    threading.Thread(target=process_inbound_messages, args=(self.inbound_q, self.msg_handlers, self.client_id)).start()
    threading.Thread(target=snd_bridge, args=(self.client, self.outbound_q, self.client_id)).start()

    try:
      self.client.connect(broker, port, 60)
      self.client.loop_start()
    except Exception as e:
      print(f"An error occurred while connecting to the MQTT broker: {e}")

    self._initialized = True

  def on_connect(self, client, userdata, flags, rc):
    if rc == 0:
      print(f"Connected client: {client} userdata: {userdata} flags: {flags}")
      self.client.subscribe("test/topic")  # Adjust this as needed
    else:
      print(f"Failed to connect to MQTT broker with result code {rc}")

  def on_message(self, client, userdata, msg):
    try:
      message = msg_from_json(json.loads(msg.payload.decode("utf-8")))
      self.inbound_q.put(message)  # Push received message to inbound queue
    except Exception as e:
      print(f"Error processing received message: {e}")

  def on(self, msg_type, handler):
    self.handlers[msg_type].append(handler)

  def send(self, msg_type, target, msg):
    message = Message(msg_type, self.client_id, target, msg)
    self.client.publish(msg_type, json.dumps(message))  # Publish to the relevant topic

  def disconnect(self):
    try:
      self.client.loop_stop()
      self.client.disconnect()
    except Exception as e:
      print(f"An error occurred while disconnecting from the MQTT broker: {e}")

