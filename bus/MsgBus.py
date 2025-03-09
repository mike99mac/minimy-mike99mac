import paho.mqtt.client as mqtt
import json
from collections import defaultdict

class MsgBus:
  def __init__(self, broker="localhost", port=1883):
    self.client = mqtt.Client(protocol=mqtt.MQTTv311, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    self.client.on_connect = self.on_connect
    self.client.on_msg = self.on_msg
    self.handlers = defaultdict(list)
    try:
      self.client.connect(broker, port, 60)
      self.client.loop_start()
    except Exception as e:
      print(f"An error occurred while connecting to the MQTT broker: {e}")

  def on_connect(self, client, userdata, flags, rc):
    if rc == 0:
      print(f"Connected with result code {rc}")
      self.client.subscribe("#")
    else:
      print(f"Failed to connect to MQTT broker with result code {rc}")

  def on_msg(self, client, userdata, msg):
    message = json.loads(msg.payload.decode())
    for handler in self.handlers[message['type']]:
      handler(Message(message['type'], message['data']))

  def on(self, message_type, handler):
    self.handlers[message_type].append(handler)

  def send(self, message_type, data):
    message = {"type": message_type, "data": data}
    self.client.publish(message_type, json.dumps(message))

  def disconnect(self):
    try:
      self.client.loop_stop()
      self.client.disconnect()
    except Exception as e:
      print(f"An error occurred while disconnecting from the MQTT broker: {e}")

bus = MsgBus()

