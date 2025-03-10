from collections import defaultdict
from framework.util.utils import LOG, Config
import json
import os
import paho.mqtt.client as mqtt

class Message:
  def __init__(self, type, data):
    self.type = type
    self.data = data

class MsgBusClient:
  def __init__(self, client_id, broker="localhost", port=1883):
    print(f"MsgBusClient.__init__(): client_id: {client_id}")
    self.client_id = client_id
    self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id)
    self.client.on_connect = self.on_connect
    self.client.on_msg = self.on_msg
    self.handlers = defaultdict(list)
    try:
      self.client.connect(broker, port, 60)
    except ConnectionRefusedError:
      print(f"Connection to MQTT broker at {broker}:{port} refused.")
      return
    except Exception as e:
      print(f"An error occurred while connecting to the MQTT broker: {e}")
      return
    self.client.loop_start()

  def on_connect(self, client, userdata, flags, rc):
    if rc == 0:
      print(f"MsgBusClient.on_connect(): connected to MQTT client_id: {self.client_id}")
      self.client.subscribe("#")
    else:
      print(f"MsgBusClient.on_connect(): failed to connect to MQTT rc: {rc}")

  def on_msg(self, client, userdata, msg):
    print(f"MsgBusClient.on_msg(): client: {client} userdata: {userdata}")
    msg = json.loads(msg.payload.decode())
    for handler in self.handlers[msg['type']]:
      handler(Message(msg['type'], msg['data']))

  def on(self, msg_type, handler):
    self.handlers[msg_type].append(handler)

  def send(self, msg_type, target, data):
    msg = {
        "type": msg_type,
        "source": self.client_id,
        "target": target,
        "data": data
    }
    self.client.publish(msg_type, json.dumps(msg))

