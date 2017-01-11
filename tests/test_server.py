import unittest
import asyncio
import functools
from json import loads, dumps

from PodSixNet.Server import ProtocolServer
from PodSixNet.Channel import Channel


class ServerTestCase(unittest.TestCase):
    connected = {"action": "connected"}
    testdata = {"action": "hello", "data": {"a": 321, "b": [2, 3, 4], "c": ["afw", "wafF", "aa", "weEEW", "w234r"], "d": ["x"] * 256}}

    class ServerChannel(Channel):
        def Network_hello(self, data):
            self.Send(data)

        def Network_connected(self, data):
            self.connected = True


    class TestServer(ProtocolServer):
        def Connected(self, channel, addr):
            pass


    async def client(self, message, future, loop):
        reader, writer = await asyncio.open_connection('127.0.0.1', 33333, loop=loop)

        # Send out our message
        writer.write(message.encode())

        # Wait for action:connected handshake
        data = await reader.readuntil(Channel.endchars.encode())
        decoded_data = data.decode().split(Channel.endchars)[0]
        self.assertTrue(self.connected == loads(decoded_data), "Initiall action:connected handshake not received")

        # Wait for the action echo payload
        data = await reader.readuntil(Channel.endchars.encode())
        decoded_data = data.decode().split(Channel.endchars)[0]
        future.set_result(decoded_data)


    async def _runTest(self, loop):
        f = asyncio.Future()
        loop.create_task(self.client(dumps(self.testdata) + Channel.endchars, f, loop))
        done, pending = await asyncio.wait([f], timeout=0.5)
        if len(done) != 1:
            self.fail("Timeout")
        self.assertTrue(self.testdata == loads(f.result()), "Sent data does not match received data (should be the same)")
        loop.stop()


    def setUp(self):
        self.loop = asyncio.get_event_loop()

        # Set up test server
        server_coro = self.loop.create_server(functools.partial(self.TestServer, self.loop, self.ServerChannel), "127.0.0.1", 33333)
        self.server = self.loop.run_until_complete(server_coro)


    def runTest(self):
        self.loop.run_until_complete(self._runTest(self.loop))


    def tearDown(self):
        self.server.close()
        self.loop.close()
