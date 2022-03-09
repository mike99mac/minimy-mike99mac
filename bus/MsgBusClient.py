#!/usr/bin/python
from websocket import create_connection
import datetime, json, time, asyncio, websockets
from bus.Message import Message, msg_from_json
import threading
from queue import Queue

async def SendThread(ws, outbound_q, client_id):
    while True:
        while outbound_q.empty():
            time.sleep(0.001)

        msg = outbound_q.get() 
        ws.send( msg )
        #print("[%s]MsgBusClient sent:%s" % (client_id, msg))

async def RecvThread(ws, callback, client_id):
    alive = True
    while alive:
        try:
            callback( msg_from_json( ( json.loads( ws.recv() ) ) ) )
        except:
            print("Warning! socket closed OR callback error. Exiting RecvThread = %s" % (client_id,))
            alive = False

# helper routine to allow thread to call async function
def rcv_bridge(ws, callback, client_id):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop( loop )
    loop.run_until_complete( RecvThread(ws, callback, client_id) )
    loop.close()

def process_inbound_messages(inbound_q, msg_handlers, client_id):
    # this is where you handle bus.on() events
    while True:
        while inbound_q.empty():
            time.sleep(0.001)

        msg = inbound_q.get() 
        #print("[%s]received:%s" % (client_id, msg))

        # see if msg type is a registered event
        if msg_handlers.get( msg['msg_type'], None ) is not None:
            msg_handlers[msg['msg_type']]( msg )
        else:
            #print("Warning no message handler registered %s" % (msg,))
            pass


def snd_bridge(ws, outbound_q, client_id):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop( loop )
    loop.run_until_complete( SendThread(ws, outbound_q, client_id) )
    loop.close()


class MsgBusClient:
    def __init__(self, client_id):
        self.ws = ''
        self.inbound_q = Queue()
        self.outbound_q = Queue()
        self.msg_handlers = {}
        self.client_id = client_id
        self.ws = create_connection("ws://localhost:4000/%s" % (self.client_id,))

        threading.Thread( target=rcv_bridge, args=(self.ws, self.rcv_client_msg,self.client_id) ).start()
        threading.Thread( target=process_inbound_messages, args=(self.inbound_q, self.msg_handlers, self.client_id) ).start()

        threading.Thread( target=snd_bridge, args=(self.ws, self.outbound_q, self.client_id) ).start()

    def on(self, msg_type, callback):
        self.msg_handlers[msg_type] = callback

    def rcv_client_msg(self, msg):
        self.inbound_q.put(msg)

    def send(self, msg_type, target, msg):
        self.outbound_q.put( json.dumps( Message(msg_type, self.client_id, target, msg) ) )

    def close(self):
        self.ws.close()
