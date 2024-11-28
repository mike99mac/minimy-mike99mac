import asyncio
import json
import logging
import websockets
#from websockets import WebSocketServerProtocol
from websockets import serve 

logging.basicConfig(level=logging.INFO)

class Server:
  """ Simple WebSocket server """
  clients = {}
  identifiers = set()
  logging.info('Message Bus Starting Up ...')

  def __init__(self):
    logging.info('Message Bus Initialized')

  async def register(self, ws) -> bool:
    logging.info(f"Server.register(): ws.skill_remote_address: {ws.remote_address}")
    identifier = ws.remote_address[1]      # save port number as identifier
    if identifier in self.identifiers:
      logging.warning(f"Identifier {identifier} already registered. Connection rejected.")
      return False
    self.clients[ws] = identifier
    self.identifiers.add(identifier)
    logging.info(f'{ws.remote_address} Connected: {identifier}')
    return True

  async def unregister(self, ws) -> None:
    if ws in self.clients:
      identifier = self.clients[ws]
      del self.clients[ws]
      self.identifiers.remove(identifier)
      logging.info(f'{ws.remote_address} Disconnected: {identifier}')

  async def find_client(self, target):
    for client, identifier in self.clients.items():
      if identifier == target:
        return client
    return None

  async def send_to_clients(self, message): # Handle message distribution
    if self.clients:
      try:
        msg = json.loads(message)
        target = msg.get('target', '')
        source = msg.get('source', '')
        if not target or not source:
          logging.error(f"Error - Rejected ill-formed message. source:{source}, target:{target}")
          return False

        if target == '*':                  # Broadcast
          await asyncio.gather(*[client.send(message) for client in self.clients])
        else:                              # Directed
          client = await self.find_client(target)
          if client is None:
            logging.warning(f"Error, target not found! target:{target}, message:{msg}")
            return False
          await client.send(message)
          system_monitor = await self.find_client('system_monitor') # notify a system monitor
          if system_monitor:
            await system_monitor.send(message)
          return True
      except Exception as e:
        logging.error(f"Error during message distribution: {e}")
        return False

  #async def ws_handler(self, ws, path):
  async def ws_handler(self, ws):
    if await self.register(ws):
      try:
        async for message in ws:
          await self.send_to_clients(message)
      except websockets.ConnectionClosed as e:
        logging.info(f"Connection closed: {e}")
      finally:
        await self.unregister(ws)
    else:
      logging.warning(f"Cannot register connection - dropping connection")

async def main():
  server = Server()
  async with serve(server.ws_handler, '0.0.0.0', 8181):
    logging.info("Server is running...")
    await asyncio.Future()  # Keep the server running indefinitely

if __name__ == "__main__":
  asyncio.run(main())

