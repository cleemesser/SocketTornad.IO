#!/usr/bin/env python
# 
# Search service which runs on port 8888
# 
import functools
import hashlib
import logging
import re
import struct
import time
import tornado.escape
import tornado.web
import tornado.websocket
import tornado.httpserver
import urlparse
import simplejson as json

logging.getLogger().setLevel(logging.DEBUG)

class SocketIOProtocol(tornado.web.RequestHandler):
    """ Based on tornado.websocket.WebSocketHandler by
    Jacob Kristhammar"""
    def open(self, *args, **kwargs):
        """Invoked when a protocol socket is opened."""
        print "[default] Opened Socket: args - %s, kwargs - %s" % (args, kwargs)

    def on_message(self, message):
        """Handle incoming messages on the protocol socket
        This method *must* be overloaded
        TODO - Abstract Method imports via ABC
        """
        print "[default] Message On Socket: message - %s" % (message)
        raise NotImplementedError

    def on_close(self):
        """Invoked when the protocol socket is closed."""
        print "[default] Closed Socket"

class WebSocketIOHandler(SocketIOProtocol, tornado.websocket.WebSocketHandler):
    def open(self, *args, **kwargs):
        """Invoked when a protocol socket is opened."""
        logging.debug("[wsio] Opened Socket: args - %s, kwargs - %s" % (args, kwargs))

    def on_message(self, message):
        """Handle incoming messages on the protocol socket
        This method *must* be overloaded
        TODO - Abstract Method imports via ABC
        """
        print "[wsio] Message On Socket: message - %s" % (message)

    def on_close(self):
        """Invoked when the protocol socket is closed."""
        print "[wsio] Closed Socket"

    def _handle_challenge(self, challenge):
        logging.debug("Challenge %s" % challenge.encode('hex'))
        tornado.websocket.WebSocketHandler._handle_challenge(self, challenge)

    def _receive_message(self):
        logging.debug("Receive Message... ")
        self.stream.read_bytes(1, lambda b: logging.debug("Frame Type: %s" % b.encode('hex')))
        #tornado.websocket.WebSocketHandler._receive_message(self)


# TODO - Monkey Patchable package object?
PROTOCOLS = {
    "xhr-polling": None,
    "xhr-multipart": None,
    "jsonp-polling": None,
    "htmlfile": None,
    "websocket": type('WebSocketIOHandler', (WebSocketIOHandler,), {}),
    "flashsocket": type('FlashSocketIOHandler', (WebSocketIOHandler,), {}), # TODO - Bind flash policy server
}

#    "websocket": type('WebSocketIOHandler', (SocketIOProtocol,tornado.websocket.WebSocketHandler), {}),
    #"flashsocket": type('FlashSocketIOHandler', (SocketIOProtocol,tornado.websocket.WebSocketHandler), {}), # TODO - Bind flash policy server

class SocketIOHandler(tornado.web.RequestHandler):

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
            extra = args[:-2]
            protocol, proto_init = args[-2:]
            print "Initializing %s(%s) ... Extra Data: %s" % (protocol, proto_init, extra)
            handler = PROTOCOLS.get(protocol, None)
            if handler and issubclass(handler, SocketIOProtocol):
                handler = handler(self.application, self.request)
                print "Handler: %s" % handler
                handler._execute(transforms, extra)
            else:
                raise Exception("Handler for protocol '%s' is currently unavailable." % protocol)
        except ValueError as e:
            print "Malformed request received: %s" % e
            self._abort(400)
            return



    def _abort(self, error_code=None):
        """ Kill the connection """
        self.active = False
        self.stream.close()
        if error_code:
            raise HTTPError(error_code)

    @classmethod
    def routes(cls, resource, extraRE=None, extraSep=None):
        #return (r"/%s/((xhr-polling|xhr-multipart|jsonp-polling|htmlfile)/)?/?/(\d*)/(%s)" % (resource, extraRE), cls)
        if extraRE:
            if extraRE[0] != '(':
                extraRE = r"(%s)" % extraRE
            if extraSep:
                extraRE = extraSep + extraRE
        else:
            extraRE = "()"

        protoRE = "(%s)" % "|".join(PROTOCOLS.keys())
        print "ProtoRE: %s" % protoRE
        return (r"/%s%s/%s/?/?(\d*)" % (resource, extraRE, protoRE), cls)


testRoute = SocketIOHandler.routes("searchTest", "(123)(.*)", extraSep='/')
print testRoute
application = tornado.web.Application([
    testRoute
])

if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

