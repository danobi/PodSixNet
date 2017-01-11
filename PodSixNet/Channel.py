import sys, traceback

from json import loads, dumps

class Channel():
    # This series of characters signals the end a discrete transmission
    endchars = '\0---\0'

    def __init__(self, loop, server, ip, port, transport):
        self.loop = loop
        self.server = server
        self.ip = ip
        self.port = port
        self._transport = transport
        self._incoming_buffer = ""
        self._send_queue = []

    
    def store_incoming_data(self, data):
            self._incoming_buffer += data
    

    def _perform_callbacks(self, incoming_dict):
        """Performs all callbacks associated with the incoming dictionary of data"""
        # Network() is the default callback for data regardless of what incoming_dict['action'] is
        if hasattr(self, 'Network'):
            self.Network(incoming_dict)

        # Now call any callbacks associated with incoming_dict['action']
        callback_name = 'Network_' + incoming_dict['action']
        if hasattr(self, callback_name):
            getattr(self, callback_name)(incoming_dict)
        else:
            raise NameError("This channel has no callback of action: {}".format(callback_name))

    
    def Pump(self):
        # Handle buffered incoming data
        while Channel.endchars in self._incoming_buffer:
            # Handle first message
            pickled_dict = self._incoming_buffer.split(Channel.endchars)[0]
            restored_dict = loads(pickled_dict)
            if type(restored_dict) == dict:
                self._perform_callbacks(restored_dict)

            # Save the rest of the incoming buffer for the next loop
            self._incoming_buffer = Channel.endchars.join(self._incoming_buffer.split(Channel.endchars)[1:])

        # Send outbound data
        [self._transport.write(data) for data in self._send_queue]
        self._send_queue = []

    
    def Send(self, data):
        """Adds data to the outgoing queue

        The data will be sent the next time this Channel is Pump()ed.

        Returns:
            The number of bytes sent after enoding"""
        outgoing = dumps(data) + Channel.endchars
        self._send_queue.append(outgoing.encode())
        self.loop.call_soon(self.Pump)
        return len(outgoing)

    
    def handle_connect(self):
        if hasattr(self, "Connected"):
            self.Connected()

    def handle_close(self):
        if hasattr(self, "Close"):
            self.Close()

    def handle_expt(self, exc):
        pass
