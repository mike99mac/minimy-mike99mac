import asyncio
import websockets

async def connect_to_websocket():
    uri = "ws://localhost:8181/system_skill"
    try:
        async with websockets.connect(uri) as websocket:
            print("WebSocket connection established.")
            
            # Send a message to the WebSocket server
            await websocket.send("Hello from Python client")
            
            # Wait for and print a response
            response = await websocket.recv()
            print(f"Message from server: {response}")
    except Exception as e:
        print(f"WebSocket connection error: {e}")

# Run the connection function
asyncio.run(connect_to_websocket())

