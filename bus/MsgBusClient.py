import datetime 
import paho.mqtt.client as mqtt
from collections import defaultdict
import json

class Message(dict):
    def __init__(self, msg_type, source, target, data):
        self.msg_type = msg_type
        self.source = source
        self.target = target
        self.data = data
        dict.__init__(self, msg_type=msg_type, source=source, target=target, data=data, ts=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

class MsgBusClient:
  _instances = {}

  def __new__(cls, client_id, *args, **kwargs):
    if client_id in cls._instances:
      return cls._instances[client_id]
    instance = super().__new__(cls)
    cls._instances[client_id] = instance
    return instance

  def __init__(self, client_id, broker="localhost", port=1883):
    if hasattr(self, '_initialized') and self._initialized:
      return
    self.client_id = client_id
    self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id)
    self.client.on_connect = self.on_connect
    self.handlers = defaultdict(list)
    try:
      self.client.connect(broker, port, 60)
      self.client.loop_start()
    except Exception as e:
      print(f"An error occurred while connecting to the MQTT broker: {e}")

    self._initialized = True
  
  def on_connect(self, client, userdata, flags, rc):
    if rc == 0:
      print(f"Connected client: {client} userdata: {userdata} flags: {flags}")
      self.client.subscribe("#")
    else:
      print(f"Failed to connect to MQTT broker with result code {rc}")
  
  def on(self, msg_type, handler):
    self.handlers[msg_type].append(handler)
  
  def send(self, msg_type, target, msg):
    message = Message(msg_type, self.client_id, target, msg)
    self.client.publish(msg_type, json.dumps(message))
  
  def disconnect(self):
    try:
      self.client.loop_stop()
      self.client.disconnect()
    except Exception as e:
      print(f"An error occurred while disconnecting from the MQTT broker: {e}")
