import asyncio
from framework.util.utils import LOG, Config
import functools
import json
import os
import websockets.asyncio
from websockets.asyncio.server import serve 

class MsgBusServer:
  """ Simple WebSocket server """
  clients = {}
  identifiers = set()

  def __init__(self):
    self.base_dir = str(os.getenv('SVA_BASE_DIR'))
    log_filename = self.base_dir + '/logs/bus.log'
    self.log = LOG(log_filename).log
    self.log.debug(f"MsgBusServer.__init__(): Message Bus started - log_filename: {log_filename}")

  async def register(self, ws) -> bool:
    # dir = ws.request.path
    # identifier = f"ws://localhost:8181{dir}"
    identifier = ws.request.path.strip("/") 
    if identifier in self.identifiers:
      self.log.warning(f"MsgBusServer.register() identifier: {identifier} already registered. Connection rejected.")
      return False
    self.clients[ws] = identifier
    self.identifiers.add(identifier)
    self.log.info(f"MsgBusServer.register() saved identifier: {identifier} ws.remote_address: {ws.remote_address}")
    return True

  async def unregister(self, ws) -> None:
    if ws in self.clients:
      identifier = self.clients[ws]
      del self.clients[ws]
      self.identifiers.remove(identifier)
      self.log.info(f"MsgBusServer.unregister() removed adress {ws.remote_address} identifier: {identifier}")

  async def find_client(self, target):
    self.log.info(f"MsgBusServer.find_client() target: {target}")
    for client, identifier in self.clients.items():
      if identifier == target:
        return client
    return None

  
  async def send_to_clients(self, message): # Handle message distribution
    self.log.info(f"MsgBusServer.send_to_clients() message: {message}")
    self.log.debug(f"MsgBusServer.send_to_clients(): Connected clients: {len(self.clients)}")
    if self.clients:
      try:
        msg = json.loads(message)
        target = msg.get('target', '')
        source = msg.get('source', '')
        self.log.info(f"MsgBusServer.send_to_clients() target: {target}, source: {source}")
        if not target or not source:
          self.log.error(f"MsgBusServer.send_to_clients() ill-formed message source:{source}, target:{target}")
          return False
        if target == '*':                  # Broadcast
          await asyncio.gather(*[client.send(message) for client in self.clients])
        else:                              # Directed
          client = await self.find_client(target)
          if client is None:
            self.log.warning(f"MsgBusServer.send_to_clients() target not found: {target} message: {msg}")
            return False
          await client.send(message)
          system_monitor = await self.find_client('system_monitor') # notify a system monitor
          if system_monitor:
            await system_monitor.send(message)
          return True
      except Exception as e:
        self.log.error(f"MsgBusServer.send_to_clients(): Exception type: {type(e).__name__}, Details: {e}")
        return False

  async def ws_handler(self, ws) -> None:
    path = ws.request.path
    self.log.debug(f"MsgBusServer.ws_handler() path: {path}")
    if (await self.register(ws)):
      self.log.debug(f"MsgBusServer.ws_handler(): registered remote_address: {ws.remote_address}")
      try:
        await self.distribute(ws)
        self.log.debug(f"MsgBusServer.ws_handler() returned from distribute()")
      finally:
        self.log.debug(f"MsgBusServer.ws_handler() finally: unregistering ws")
        await self.unregister(ws)
    else:
      self.log.warning(f"MsgBusServer.ws_handler():, can't register connection - dropping")

  async def stop(self):
    self.log.info(f"MsgBusServer.stop(): stopping message bus")
  
  async def distribute(self, ws) -> None:
    self.log.debug(f"MsgBusServer.distribute(): WebSocket: {ws}")
    self.log.debug(f"MsgBusServer.distribute(): remote_address: {ws.remote_address}, state: {ws.state}")
    self.log.debug(f"MsgBusServer.distribute(): Connected clients: {len(self.clients)}")
    # self.log.debug(f"MsgBusServer.distribute(): attributes: {dir(ws)}")
    try:
      async for message in ws:
        self.log.debug(f"MsgBusServer.distribute(): received raw message: {message}")
        try:                               # process and forward the message
          result = await self.send_to_clients(message)
          self.log.debug(f"MsgBusServer.distribute(): send_to_clients() result: {result}")
        except Exception as e:
          self.log.error(f"MsgBusServer.distribute(): Error in send_to_clients: {e}")
          await asyncio.sleep(0.001)       # delay to allow other tasks to run
    except websockets.exceptions.ConnectionClosed as e:
      self.log.debug(f"MsgBusServer.distribute(): WebSocket closed: {e}")
    except Exception as e:
      self.log.error(f"MsgBusServer.distribute(): Unexpected exception: {e}")
    finally:
      self.log.debug(f"MsgBusServer.distribute(): finally: ws.state: {ws.state}")

async def main():
  server = MsgBusServer()
  print(f"MsgBusServer.main() server created")
  # async with websockets.serve(server.ws_handler, '0.0.0.0', 8181):   
  async with websockets.serve(server.ws_handler, '0.0.0.0', 8181, ping_interval=20, ping_timeout=20):   
    print(f"MsgBusServer.main() Websocket server started on port 8181")
    await asyncio.Future()                 # run forever

# main()
if __name__ == "__main__":
  asyncio.run(main())

