import asyncio
import websockets

class MessageBusServer:
  async def ws_handler(self, websocket):
    print(f"New connection from path: {websocket.remote_address}")
    try:
      # Example handler: Echo received messages back to the client
      async for message in websocket:
        print(f"Received message: {message}")
        await websocket.send(f"Echo: {message}")
    except Exception as e:
      print(f"Error in ws_handler: {e}")
    finally:
      print(f"Connection closed for path: {path}")

async def main():
  server = MessageBusServer()
  async with websockets.serve(server.ws_handler, '0.0.0.0', 8181):
    await asyncio.Future()                 # run forever

if __name__ == "__main__":
  asyncio.run(main())
