import datetime
from framework.util.utils import LOG, Config
import os

class Message(dict):
  def __init__(self, msg_type, source, target, data):
    self.base_dir = str(os.getenv('SVA_BASE_DIR'))
    log_filename = self.base_dir + '/logs/bus.log'
    self.log = LOG(log_filename).log
    self.log.debug(f"Message.__init__(): msg_type: {msg_type}, source: {source}, target: {target}, data: {data}")
    self.msg_type = msg_type
    self.source = source
    self.target = target
    self.data = data
    dict.__init__(self, msg_type=msg_type, source=source, target=target, data=data, ts=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def msg_from_json(packet):
  m = Message(packet['msg_type'],packet['source'],packet['target'],packet['data'])
  m.ts = packet['ts']
  return m
