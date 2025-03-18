import asyncio
from websockets import WebSocketServerProtocol, serve

class MessageBusServer:
  async def ws_handler(self, websocket, path):
    # Your websocket handler logic here
    pass

async def main():
  server = MessageBusServer()
  async with serve(server.ws_handler, '0.0.0.0', 8181):
    await asyncio.Future()  # run forever

if __name__ == "__main__":
  asyncio.run(main())
