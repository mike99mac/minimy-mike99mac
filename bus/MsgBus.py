import asyncio
import json
import os
import websockets.asyncio
from websockets.asyncio.server import serve
from framework.util.utils import LOG

class MsgBusServer:
  clients = {}
  identifiers = set()

  def __init__(self):
    self.base_dir = str(os.getenv('SVA_BASE_DIR', '/tmp'))
    # log_filename = os.path.join(self.base_dir, 'logs', 'bus.log')
    # self.log = LOG(log_filename).log
    # self.log.debug("MsgBusServer.__init__(): Message Bus started")

  async def register(self, ws):
    identifier = ws.request.path.strip("/")
    if identifier in self.identifiers:
      # self.log.warning(f"MsgBusServer.register(): identifier {identifier} already registered.")
      return False
    self.clients[ws] = identifier
    self.identifiers.add(identifier)
    # self.log.info(f"MsgBusServer.register(): registered identifier: {identifier} from {ws.remote_address}")
    print(f"MsgBusServer.register(): registered identifier: {identifier} from {ws.remote_address}")
    return True

  async def unregister(self, ws):
    if ws in self.clients:
      identifier = self.clients[ws]
      del self.clients[ws]
      self.identifiers.remove(identifier)
      # self.log.info(f"MsgBusServer.unregister(): Unregistered {identifier}")

  async def find_client(self, target):
    for client in self.clients:
      if self.clients[client] == target:
        # self.log.info(f"MsgBusServer.find_client(): found client: {client}")
        return client
      else:
        # self.log.info(f"MsgBusServer.find_client(): did not find client: {client}")
        return None

  async def send_to_clients(self, message):
    # self.log.info(f"MsgBusServer.send_to_clients(): Sending message: {message}")
    print(f"MsgBusServer.send_to_clients(): Sending message: {message}")
    if self.clients:
      msg = json.loads(message)
      target = msg.get('target', '')
      if target == '*':                    # broadcast
        await asyncio.gather(*[client.send(message) for client in self.clients])
      else:                                # directed
        client = next((ws for ws, id in self.clients.items() if id == target), None)
        if client:
          await client.send(message)
        # else:
        #   self.log.warning(f"MsgBusServer.send_to_clients(): target: {target} not found msg: {msg}")
        web_ui_clients = [ws for ws, id in self.clients.items() if id.startswith("web_ui")]
        # await asyncio.gather(*[ws.send(message) for ws in web_ui_clients])
        await client.send(message)
        client2 = await self.find_client('system_monitor')
        if client2 == None:
          # self.log.debug("Error, system_monitor not found!")
          return False
        await client2.send(message)
        return True

  async def ws_handler(self, ws):
    if await self.register(ws):
      try:
        async for message in ws:
          await self.send_to_clients(message)
      finally:
        await self.unregister(ws)

async def main():
  server = MsgBusServer()
  async with serve(server.ws_handler, '0.0.0.0', 8181, ping_interval=60, ping_timeout=60):
    print("WebSocket server started on port 8181")
    await asyncio.Future()

if __name__ == "__main__":
  asyncio.run(main())

