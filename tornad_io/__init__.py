import logging
import re
import urlparse
# Newer versions of SimpleJSON from what's in Py 2.6 etc 
# have builtin decimal support and are preferred IMHO
import simplejson as json

import tornado.escape
import tornado.web
import tornado.httpserver

import tornad_io.websocket
import tornad_io.socket_io

logging.getLogger().setLevel(logging.DEBUG)
# TODO - Monkey Patchable package object?
PROTOCOLS = {
    "xhr-polling": None,
    "xhr-multipart": None,
    "jsonp-polling": None,
    "htmlfile": None,
    "websocket": type('WebSocketIOHandler', (tornad_io.websocket.WebSocketIOHandler,), {}),
    "flashsocket": type('FlashSocketIOHandler', (tornad_io.websocket.WebSocketIOHandler,), {}), # TODO - Bind flash policy server
}

class SocketIOHandler(tornado.web.RequestHandler):

    protocol = None

    def __init__(self, application, request):
        tornado.web.RequestHandler.__init__(self, application, request)
        self.active = True
        self.stream = request.connection.stream
        self.application = application
        self.request = request

    def _execute(self, transforms, *args, **kwargs):
        self.conn_args = args
        self.conn_kwargs = kwargs
        try:
            # NOTE - Putting extra parens in your extraRE may cause breakage.
            # TODO - Support named groups?
            extra = args[:-2]
            proto_type, proto_init = args[-2:]
            logging.debug("Initializing %s(%s) ... Extra Data: %s" % (proto_type, proto_init, extra))
            protocol = PROTOCOLS.get(proto_type, None)
            if protocol and issubclass(protocol, tornad_io.socket_io.SocketIOProtocol):
                self.protocol = protocol(self)
                self.protocol._execute(transforms, *extra, **kwargs)
            else:
                raise Exception("Handler for protocol '%s' is currently unavailable." % protocol)
        except ValueError as e:
            logging.warning("Malformed request received: %s" % e)
            self._abort(400)
            return

    def send(self, message):
        """Message to send data to the client.
        Encodes in Socket.IO protocol and
        ensures it doesn't send if session
        isn't fully open yet."""
        self.protocol.send(message)

    def on_open(self, *args, **kwargs):
        """Invoked when a protocol socket is opened...
        Passes in the args & kwargs from the route
        as Tornado deals w/ regex groups, via _execute method.
        See the tornado docs and code for detail."""
        logging.debug("[socketio protocol] Opened Socket: args - %s, kwargs - %s" % (args, kwargs))

    def on_message(self, message):
        """Handle incoming messages on the protocol socket
        This method *must* be overloaded
        TODO - Abstract Method imports via ABC
        """
        logging.debug("[socketio protocol] Message On Socket: message - %s" % (message))
        raise NotImplementedError

    def on_close(self):
        """Invoked when the protocol socket is closed."""
        logging.debug("[socketio protocol] Closed Socket")


    def _abort(self, error_code=None):
        """ Kill the connection """
        self.active = False
        self.stream.close()
        self.protocol._abort()
        if error_code:
            raise HTTPError(error_code)

    @classmethod
    def routes(cls, resource, extraRE=None, extraSep=None):
        # TODO - Support named groups
        #return (r"/%s/((xhr-polling|xhr-multipart|jsonp-polling|htmlfile)/)?/?/(\d*)/(%s)" % (resource, extraRE), cls)
        if extraRE:
            if extraRE[0] != '(':
                extraRE = r"(%s)" % extraRE
            if extraSep:
                extraRE = extraSep + extraRE
        else:
            extraRE = "()"

        protoRE = "(%s)" % "|".join(PROTOCOLS.keys())
        logging.debug("ProtoRE: %s" % protoRE)
        return (r"/%s%s/%s/?/?(\d*)" % (resource, extraRE, protoRE), cls)


class TestHandler(SocketIOHandler):
    def on_message(self, message):
        logging.debug("[echo] %s" % message)
        self.send("[echo] %s" % message)

testRoute = TestHandler.routes("searchTest", "(123)(.*)", extraSep='/')
application = tornado.web.Application([
    testRoute
])

if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

