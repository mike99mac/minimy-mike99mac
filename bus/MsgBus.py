import asyncio
import json
import logging
import websockets
from websockets import WebSocketServerProtocol

logging.basicConfig(level=logging.INFO)

class Server:
    """ simple websocket server """
    clients = {}
    identifiers = set()
    logging.info('Message Bus Starting Up ...')

    def __init__(self):
        logging.info('Message Bus Initialized')

    async def register(self, ws: WebSocketServerProtocol) -> None:
        identifier = ws.path[1:]
        # print(f"Server.register() identifier = {identifier} self.identifiers = {self.identifiers}")
        if identifier in self.identifiers:
            return False
 
        self.clients[ws] = identifier
        self.identifiers.add(identifier)
        logging.info(f'{ws.remote_address} Connected: {identifier}')
        return True

    async def unregister(self, ws: WebSocketServerProtocol) -> None:
        identifier = self.clients[ws]
        del self.clients[ws]
        self.identifiers.remove(identifier)
        logging.info(f'{ws.remote_address} Disconnected: {identifier}')

    async def find_client(self, target):
        for client in self.clients:
            if self.clients[client] == target:
                return client
        return None

    async def send_to_clients(self, message):
        """
        pseudo abstraction violation should not really care about message structure at this level
        """
        if self.clients:
            msg = json.loads(message)
            target = msg.get('target','')
            source = msg.get('source','')
            if target == '' or source == '':
                logging.error("Error - Rejected ill formed message. source:%s, target:%s" % (source, target))
                return False

            if target == '*':
                # broadcast
                # got this warning on the line below - how to fix?    -MM
                # DeprecationWarning: The explicit passing of coroutine objects to asyncio.wait() 
                # is deprecated since Python 3.8, and scheduled for removal in Python 3.11.
                #await asyncio.wait([client.send(message) for client in self.clients])
                # fix from Mike Gray 
                await asyncio.gather(*[client.send(message) for client in self.clients])
            else:                          # directed
                client = await self.find_client(target)
                if client == None:
                    logging.warning("Error, target not found! %s, %s" % (target,msg))
                    return False

                await client.send(message)
                client2 = await self.find_client('system_monitor')
                if client2 == None:
                    logging.debug("Error, system_monitor not found!")
                    return False
                await client2.send(message)
                return True
                        
    async def ws_handler(self, ws: WebSocketServerProtocol, url: str) -> None:
        if (await self.register(ws)):
            try:
                await self.distribute(ws)
            finally:
                await self.unregister(ws)
        else:
            logging.warning(f"Warning, can't register {ws.path}, dropping connection")

    async def distribute(self, ws: WebSocketServerProtocol) -> None:
        async for message in ws:
            await self.send_to_clients(message)

if __name__ == "__main__":
    server = Server()
    # only allow local (on device) access
    # allow external devices to access the msg bus
    # start_server = websockets.serve(server.ws_handler,'0.0.0.0',4000)
    # switch to port 8181  -MM
    start_server = websockets.serve(server.ws_handler,'0.0.0.0',8181)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server)
    loop.run_forever()
