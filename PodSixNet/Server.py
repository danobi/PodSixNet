import sys
import socket
import functools
import asyncio
from json import loads,dumps


from PodSixNet.Channel import Channel

class ProtocolServer(asyncio.Protocol):
    # channels must be a static variable since a new ProtocolServer object is created
    # for each connection
    channels = []

    def __init__(self, loop, channelClass=Channel, localaddr=("127.0.0.1", 31425), listeners=5):
        """__init__

        Args:
            loop: asyncio event loop
            channelClass: class to use for channels
            localaddr: where to serve this server at
            listeners: how many clients we can keep in our backlog (see accept(2))
        """
        self.loop = loop
        if channelClass:
            self.channelClass = channelClass
        else:
            raise TypeError("channelClass is type None")
        self.client_ip = None
        self.client_port = None
        self._need_pump = False


    def _find_channel(self, ip, port):
        """Finds and returns the channel with the requested ip & port"""
        for c in ProtocolServer.channels:
            if c.ip == ip and c.port == port:
                return c
        return None
    

    def connection_made(self, transport):
        """This implements the abstract callback from asyncio.Protocol"""
        # Create and store the client as a client Channel
        self.client_ip, self.client_port = transport.get_extra_info('peername')
        ProtocolServer.channels.append(self.channelClass(self.loop, self, self.client_ip, self.client_port, transport))

        # Send connected action over to client
        ProtocolServer.channels[-1].Send({"action": "connected"})

        # Call channel callback if it exists
        ProtocolServer.channels[-1].handle_connect()

        # Call own Connected() callback if it exists
        if hasattr(self, "Connected"):
            self.Connected(ProtocolServer.channels[-1], (self.client_ip, self.client_port))


    def connection_lost(self, exc):
        """This implements the abstract callback from asyncio.Protocol"""
        c = self._find_channel(self.client_ip, self.client_port)

        # exc is None if it's a regular close, otherwise it's an execption
        if exc:
            c.handle_expt(exc)
        else:
            c.handle_close()
            ProtocolServer.channels.remove(c)


    def eof_received(self):
        """This implements the abstract callback from asyncio.Protocol
        
        This is called when the other end has send an EOF signalling they won't
        be sending any more data"""
        # Clean up our end of the connection
        # Note that we are reusing a callback here. Not sure if that's a good idea
        self.connection_lost(None)

        # By returning None here, we close the connection
        return None


    def data_received(self, data):
        """This implements the abstract callback from asyncio.Protocol"""
        c = self._find_channel(self.client_ip, self.client_port)
        c.store_incoming_data(data.decode())
        self.loop.call_soon(self.Pump)
         

    def Pump(self):
        [c.Pump() for c in ProtocolServer.channels]
