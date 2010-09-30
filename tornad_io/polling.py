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
        self.async_callback(self.open)(*args, **kwargs)

    @tornado.web.asynchronous
    def post(self, *args, **kwargs):
        pass


    @tornado.web.asynchronous
    def options(self, *args, **kwargs):
        """Called for Cross Origin Resource Sharing Preflight message... Returns access headers."""
        self.debug("OPTIONS (args: %s kwargs: %s headers: %s) " % (args, kwargs, self.request.headers))
        self.preflight()
        self.finish()

    @tornado.web.asynchronous
    def preflight(self):
        """Called for Cross Origin Resource Sharing Preflight message... Returns access headers."""
        if self.verify_origin():
            self.set_header('Access-Control-Allow-Origin', self.request.headers['Origin'])
            if self.request.headers.has_key('Cookie'):
                self.set_header('Access-Control-Allow-Credentials', True)
            return True
        else:
            return False





class XHRPollingSocketIOHandler(PollingSocketIOHandler):

    config = {
        'timeout': None, # No heartbeats in polling
        'duration': 20000,
        'closeTimeout': 8000,
        'origins': [('*', '*')], # Tuple of (host, port)... * acceptable
    }

    @tornado.web.asynchronous
    def get(self, *args, **kwargs):
        self.session['output_handle'] = self # Stays handle as long as polling runs.
        ## IMPORTANT - Capture the output handle now as *THIS* is the polling method
        # TODO - Buffering of messages in case nothing is open? This *COULD* potentially race
        # Runs for the poll time and then writes '' and closes.
        def pollingTimeout():
            try:
                if not self._finished:
                    self._write('')
                    self.finish()
            except:
                pass # Ignore any errors, channel is probably just closed

        timeout = time.time() + self.config['duration'] / 1000.0
        self.io_loop.add_timeout(timeout, pollingTimeout)
        self.debug("Polling until %d (and then closing channel)" % timeout)
        self.open(*args, **kwargs)

    @tornado.web.asynchronous
    def post(self, *args, **kwargs):
        self.set_header('Content-Type', 'text/plain')
        data = self.get_argument('data')
        if not self.preflight():
            raise tornado.web.HTTPError(401, "unauthorized")
        self.async_callback(self._on_message)(
                data.decode("utf-8", "replace"))
        self.write('ok')
        self.finish()

    @tornado.web.asynchronous
    def _write(self, message):
        self.reset_timeout()
        self.preflight()
        self.set_header("Content-Type", "text/plain; charset=UTF-8")
        self.set_header("Content-Length", len(message))
        self.write(message)
        self.finish()

class XHRMultiPartSocketIOHandler(PollingSocketIOHandler):

    @tornado.web.asynchronous
    def get(self, *args, **kwargs):
        self.set_header('Content-Type', 'multipart/x-mixed-replace;boundary="socketio"')
        self.set_header('Connection', 'keep-alive')
        self.write('--socketio\n')
        self.open(*args, **kwargs)

    @tornado.web.asynchronous
    def post(self, *args, **kwargs):
        self.set_header('Content-Type', 'text/plain')
        self.preflight()
        data = self.get_argument('data')
        self.async_callback(self._on_message)(
                data.decode("utf-8", "replace"))
        self.write('ok')
        self.finish()


    @tornado.web.asynchronous
    def _write(self, message):
        self.reset_timeout()
        self.preflight()
        self.write("Content-Type: text/plain; charset=us-ascii\n\n")
        self.write(message + '\n')
        self.write('--socketio\n')
        self.flush()

class JSONPPollingSocketIOHandler(PollingSocketIOHandler):
    config = {
        'timeout': None, # No heartbeats in polling
        'duration': 20000,
        'closeTimeout': 8000,
        'origins': [('*', '*')], # Tuple of (host, port)... * acceptable
    }
    pass

class HTMLFileSocketIOHandler(PollingSocketIOHandler):
    pass

