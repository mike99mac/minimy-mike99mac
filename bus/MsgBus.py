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
    logging.info(f'Message Bus Starting Up ...')

    def __init__(self):
        logging.info(f'Message Bus Initialized')

    async def register(self, ws: WebSocketServerProtocol) -> None:
        identifier = ws.path[1:]
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
        # pseudo abstraction violation
        # should not really care about 
        # message structure at this level
        if self.clients:
            msg = json.loads(message)
            target = msg.get('target','')
            source = msg.get('source','')
            if target == '' or source == '':
                logging.error("Error - Ill formed message. source:%s, target:%s" % (source, target))
                return False

            if target == '*':
                # broadcast
                await asyncio.wait([client.send(message) for client in self.clients])
            else: 
                # directed
                client = await self.find_client(target)
                if client == None:
                    logging.error("Error, target not found! %s, %s" % (target,msg))
                    return False
                #logging.error("SRVR send to %s, %s" % (target,message))
                await client.send(message)
                return True
                        
    async def ws_handler(self, ws: WebSocketServerProtocol, url: str) -> None:
        if (await self.register(ws)):
            try:
                await self.distribute(ws)
            finally:
                await self.unregister(ws)
        else:
            logging.warning("Warning, can't register %s, dropping connection" % (ws.path,))

    async def distribute(self, ws: WebSocketServerProtocol) -> None:
        async for message in ws:
            await self.send_to_clients(message)

if __name__ == "__main__":
    server = Server()
    start_server = websockets.serve(server.ws_handler,'localhost',4000)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server)
    loop.run_forever()
