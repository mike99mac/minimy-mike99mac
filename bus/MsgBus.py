import asyncio
from framework.util.utils import LOG, Config
import json
import os
import websockets
from websockets.asyncio.server import serve 

class Server:
  """ Simple WebSocket server """
  clients = {}
  identifiers = set()

  def __init__(self):
    self.base_dir = str(os.getenv('SVA_BASE_DIR'))
    log_filename = self.base_dir + '/logs/bus.log'
    self.log = LOG(log_filename).log
    self.log.debug(f"Server.__init__(): Message Bus started - log file: {self.base_dir}/bus.log")

  async def register(self, ws) -> bool:
    self.log.info(f"Server.register(): ws.skill_remote_address: {ws.remote_address}")
    identifier = ws.remote_address[1]      # save port number as identifier
    if identifier in self.identifiers:
      self.log.warning(f"Server.register() identifier: {identifier} already registered. Connection rejected.")
      return False
    self.clients[ws] = identifier
    self.identifiers.add(identifier)
    self.log.info(f"Server.register() remote_address {ws.remote_address} Connected: {identifier}")
    return True

  async def unregister(self, ws) -> None:
    if ws in self.clients:
      identifier = self.clients[ws]
      del self.clients[ws]
      self.identifiers.remove(identifier)
      self.log.info(f"Server.unregister() removed adress {ws.remote_address} identifier: {identifier}")

  async def find_client(self, target):
    self.log.info(f"Server.find_client() target: {target}")
    for client, identifier in self.clients.items():
      if identifier == target:
        return client
    return None

  async def send_to_clients(self, message): # Handle message distribution
    self.log.info(f"Server.send_to_clients() message: {message}")
    if self.clients:
      try:
        msg = json.loads(message)
        target = msg.get('target', '')
        source = msg.get('source', '')
        if not target or not source:
          self.log.error(f"Server.send_to_clients() ill-formed message source:{source}, target:{target}")
          return False
        if target == '*':                  # Broadcast
          await asyncio.gather(*[client.send(message) for client in self.clients])
        else:                              # Directed
          client = await self.find_client(target)
          if client is None:
            self.log.warning(f"Server.send_to_clients() target not found: {target} message: {msg}")
            return False
          await client.send(message)
          system_monitor = await self.find_client('system_monitor') # notify a system monitor
          if system_monitor:
            await system_monitor.send(message)
          return True
      except Exception as e:
        self.log.error(f"Server.send_to_clients() message distribution error: {e}")
        return False

  def stop(self):
    self.log.info(f"Server.stop(): stopping message bus")

  #async def ws_handler(self, ws, path):
  async def ws_handler(self, ws):
    if await self.register(ws):
      self.log.debug(f"Server.ws_handler() Client registered")
      try:
        async for message in ws:
          self.log.debug(f"Server.ws_handler() Received message: {message}")
          await self.send_to_clients(message)
      except websockets.ConnectionClosed as e:
        self.log.warning(f"Server.ws_handler() connection closed with exception: {e}")
      finally:
        await self.unregister(ws)
    else:
      self.log.warning(f"Server.ws_handler() cannot register connection - dropping it")

  async def main(self):
    async with serve(server.ws_handler, '0.0.0.0', 8181):
      await self.stop 

# main()
if __name__ == "__main__":
  server = Server()
  asyncio.run(server.main())

