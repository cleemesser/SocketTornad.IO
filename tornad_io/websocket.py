# Original Author: Jacob Kristhammer
# 
# WebSocket protocol implementation of websocket.py[1] 
# for latest stable version of said protocol[2]

# [1] http://github.com/facebook/tornado/blob/
#     2c89b89536bbfa081745336bb5ab5465c448cb8a/tornado/websocket.py
# [2] http://tools.ietf.org/html/draft-hixie-thewebsocketprotocol-76
#
# Author: Brendan W. McAdams <bmcadams@novus.com>
# 
# Modified version of Jacob Kristhammer's tornado.websocket.WebSocketHandler
# primarily modified for improved logging, and a wrapper for 
# Socket.IO code

import functools
import hashlib
import logging
import re
import struct
import time
import tornado.escape
import tornado.web
import tornado.websocket
import tornad_io
import tornad_io.socket_io

class WebSocketIOHandler(tornad_io.socket_io.SocketIOProtocol, 
                         tornado.websocket.WebSocketHandler):
    def __init__(self, application, request, transforms, *args, **kwargs):
        tornad_io.socket_io.SocketIOProtocol.__init__(self, application, request, transforms, *args, **kwargs)
        logging.debug("Initializing WebSocketIOHandler...")
        tornado.websocket.WebSocketHandler.__init__(self, application, request)

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

    def on_message(self, message):
        """Handle incoming messages on the protocol socket
        This method *must* be overloaded
        TODO - Abstract Method imports via ABC
        """
        logging.debug("[wsio] Message On Socket: message - %s" % (message))

    def on_close(self):
        """Invoked when the protocol socket is closed."""
        logging.debug("[wsio] Closed Socket")

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
