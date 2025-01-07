import asyncio
from framework.util.utils import LOG, Config
import functools
import json
import os
import websockets.asyncio
from websockets.asyncio.server import serve 

class Server:
  """ Simple WebSocket server """
  clients = {}
  identifiers = set()

  def __init__(self):
    self.base_dir = str(os.getenv('SVA_BASE_DIR'))
    log_filename = self.base_dir + '/logs/bus.log'
    self.log = LOG(log_filename).log
    self.log.debug(f"Server.__init__(): Message Bus started - log_filename: {log_filename}")

  async def register(self, ws) -> bool:
    self.log.info(f"Server.register() ws.remote_address: {ws.remote_address}")
    identifier = ws.remote_address[1]      # save port number as identifier
    if identifier in self.identifiers:
      self.log.warning(f"Server.register() identifier: {identifier} already registered. Connection rejected.")
      return False
    self.clients[ws] = identifier
    self.identifiers.add(identifier)
    self.log.info(f"Server.register() Connected identifier: {identifier}")
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
        self.log.info(f"Server.send_to_clients() target: {target}, source: {source}")
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

  #async def ws_handler(self, ws, url: str) -> None:
  async def ws_handler(self, ws) -> None:
    self.log.info(f"Server.ws_handler(): ws: {str(ws)}")
    if (await self.register(ws)):
      try:
        await self.distribute(ws)
      finally:
        await self.unregister(ws)
    else:
      self.log.warning(f"Server.ws_handler():, can't register {ws.path} dropping connection")

  async def distribute(self, ws) -> None:
    self.log.info(f"Server.distribute(): ws: {str(ws)}")
    async for message in ws:
      await self.send_to_clients(message)

  async def stop(self):
    self.log.info(f"Server.stop(): stopping message bus")

  # path has been removed from the new asyncio websockets handler
  # async def ws_handler(self, ws, path):
  """
  async def ws_handler(self, ws):
    print(f"Server.ws_handler() ws: {ws}")
    if await self.register(ws):
      self.log.debug(f"Server.ws_handler() Client registered")
      try:
        async for message in ws:
          self.log.debug(f"Server.ws_handler() Received message: {message}")
          await self.send_to_clients(message)
      except websockets.ConnectionClosed as e:
        print(f"Connection closed: {e}")
      except Exception as e:
        self.log.warning(f"Server.ws_handler() unhandled exception: {e}")
      finally:
        await self.unregister(ws)
    else:
      self.log.error(f"Server.ws_handler() cannot register connection - dropping it")
    """

async def main():
  server = Server()
  print(f"Server.main() server created")
  async with websockets.serve(server.ws_handler, '0.0.0.0', 8181):   
    print(f"Server.main() Websocket server started on port 8181")
    await asyncio.Future()                 # run forever

# main()
if __name__ == "__main__":
  asyncio.run(main())

