import functools
import logging
import re
import time
import tornado.websocket
import tornado.web
import tornado.ioloop
import tornad_io
from tornad_io.socket_io import SocketIOProtocol

class PollingSocketIOHandler(SocketIOProtocol):
    def __init__(self, handler):
        tornad_io.socket_io.SocketIOProtocol.__init__(self, handler)
        logging.debug("Initializing PollingSocketIOHandler...")
        tornado.web.RequestHandler.__init__(self, self.handler.application, self.handler.request)

    def get(self, *args, **kwargs):
        logging.debug("[request] Polling GET (args: %s kwargs: %s) " % (args, kwargs))
        self.async_callback(self.open)(*args, **kwargs)

    def post(self, *args, **kwargs):
        logging.debug("[request] Polling POST (args: %s kwargs: %s) " % (args, kwargs))



class XHRPollingSocketIOHandler(PollingSocketIOHandler):
    def _write(self, message):
        self.reset_timeout()
        self.set_header("Content-Type", "text/plain; charset=UTF-8")
        self.set_header("Content-Length", len(message))
        if self.request.headers.has_key('Origin') and self.verify_origin(self.request.headers['Origin']):
            self.set_header('Access-Control-Allow-Origin', self.request.headers['Origin'])
            if self.request.headers.has_key('Cookie'):
                self.set_header('Access-Control-Allow-Credentials', True)
        self.write(message)

class XHRMultiPartSocketIOHandler(PollingSocketIOHandler):
    def __init__(self, handler):
        self.request = handler.request
        if self.request.headers.has_key('Origin') and self.verify_origin(self.request.headers['Origin']):
            self.set_header('Access-Control-Allow-Origin', self.request.headers['Origin'])
            if self.request.headers.has_key('Cookie'):
                self.set_header('Access-Control-Allow-Credentials', True)
        # TODO - CORS Preflight message
        PollingSocketIOHandler.__init__(self, handler)

    def get(self, *args, **kwargs):
        logging.debug("[Multipart] Polling GET (args: %s kwargs: %s) " % (args, kwargs))
        self.set_header('Content-Type', 'multipart/x-mixed-replace;boundary="socketio"')
        self.set_header('Connection', 'keep-alive')
        self.async_callback(self.open)(*args, **kwargs)
        self.write('--socketio\n')
        # TODO - Flush
        self.async_callback(self.open)(*args, **kwargs)

    def post(self, *args, **kwargs):
        logging.debug("[Multipart] Polling POST (args: %s kwargs: %s) " % (args, kwargs))

    def _write(self, message):
        self.reset_timeout()
        self.write("Content-Type: text/plain; charset=us-ascii\n\n")
        self.write(message + '\n')
        self.write('--socketio\n')

class JSONPPollingSocketIOHandler(PollingSocketIOHandler):
    pass

class HTMLFileSocketIOHandler(PollingSocketIOHandler):
    pass

