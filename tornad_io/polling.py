import functools
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
        self.debug("Initializing PollingSocketIOHandler...")
        tornado.web.RequestHandler.__init__(self, self.handler.application, self.handler.request)

    @tornado.web.asynchronous
    def get(self, *args, **kwargs):
        self.debug("[request] Polling GET (args: %s kwargs: %s) " % (args, kwargs))
        self.async_callback(self.open)(*args, **kwargs)

    @tornado.web.asynchronous
    def post(self, *args, **kwargs):
        self.debug("[request] Polling POST (args: %s kwargs: %s) " % (args, kwargs))

    @tornado.web.asynchronous
    def options(self, *args, **kwargs):
        """Called for Cross Origin Resource Sharing Preflight message... Returns access headers."""
        self.debug("OPTIONS (args: %s kwargs: %s headers: %s) " % (args, kwargs, self.request.headers))
        if self.request.headers.has_key('Origin') and self.verify_origin(self.request.headers['Origin']):
            self.set_header('Access-Control-Allow-Origin', self.request.headers['Origin'])
            if self.request.headers.has_key('Cookie'):
                self.set_header('Access-Control-Allow-Credentials', True)
        self.finish()





class XHRPollingSocketIOHandler(PollingSocketIOHandler):
    @tornado.web.asynchronous
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

    @tornado.web.asynchronous
    def get(self, *args, **kwargs):
        self.debug("[Multipart] Polling GET (args: %s kwargs: %s) " % (args, kwargs))
        self.set_header('Content-Type', 'multipart/x-mixed-replace;boundary="socketio"')
        self.set_header('Connection', 'keep-alive')
        self.write('--socketio\n')
        self.open(*args, **kwargs)
        #self.async_callback(self.open)(*args, **kwargs)

    @tornado.web.asynchronous
    def post(self, *args, **kwargs):
        self.set_header('Content-Type', 'text/plain')
        data = self.get_argument('data')
        self.debug("[Multipart] Polling POST data: %s" % (data))
        #self.async_callback(self._on_message)(
        #        data.decode("utf-8", "replace"))
        self._on_message(data.decode("utf-8", "replace"))
        self.write('ok')
        


    @tornado.web.asynchronous
    def _write(self, message):
        self.reset_timeout()
        if self.request.headers.has_key('Origin') and self.verify_origin(self.request.headers['Origin']):
            self.set_header('Access-Control-Allow-Origin', self.request.headers['Origin'])
            if self.request.headers.has_key('Cookie'):
                self.set_header('Access-Control-Allow-Credentials', True)
        self.write("Content-Type: text/plain; charset=us-ascii\n\n")
        self.write(message + '\n')
        self.write('--socketio\n')
        self.flush()
        self.debug("%s" % self.__dict__)
        self.debug("Sent ('%s') and flushed." % message)

class JSONPPollingSocketIOHandler(PollingSocketIOHandler):
    pass

class HTMLFileSocketIOHandler(PollingSocketIOHandler):
    pass

