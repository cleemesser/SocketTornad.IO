import functools
import logging
import re
import time
import tornado.websocket
import tornado.ioloop
import tornad_io
import tornad_io.socket_io

class WebSocketIOHandler(tornad_io.socket_io.SocketIOProtocol, 
                         tornado.websocket.WebSocketHandler):

    def __init__(self, handler):
        tornad_io.socket_io.SocketIOProtocol.__init__(self, handler)
        logging.debug("Initializing WebSocketIOHandler...")
        tornado.websocket.WebSocketHandler.__init__(self, self.handler.application, self.handler.request)

    def _on_end_delimiter(self, frame):
        """ Override the default on_message handler to decode first """
        logging.debug("Got an end delimiter: %s" % frame.decode('utf8', 'replace'))
        if not self.client_terminated:
            self.async_callback(self._on_message)(
                    frame[:-1].decode("utf-8", "replace"))
            self._receive_message()

    def on_open(self, *args, **kwargs):
        """Invoked when a protocol socket is opened."""
        logging.debug("[wsio] Opened Socket: args - %s, kwargs - %s" % (args, kwargs))

    def _abort(self):
        logging.debug("Aborting WebSocketIOHandler.")
        self.client_terminated = True
        self.stream.close()

    def _write(self, message):
        """Sends the given message to the client of this Web Socket."""
        if isinstance(message, dict):
            message = tornado.escape.json_encode(message)
        if isinstance(message, unicode):
            message = message.encode("utf-8")
        assert isinstance(message, str)
        logging.debug("Writing WebSocket Message: %s" % (message))
        self.stream.write("\x00" + message + "\xff")

