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

class SocketIOHandler(tornad_io.socket_io.SocketIOProtocol):

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
                protocol = protocol.__init__(self, self.application, self.request, transforms, *extra, **kwargs)
                protocol._execute(transforms, *extra, **kwargs)
            else:
                raise Exception("Handler for protocol '%s' is currently unavailable." % protocol)
        except ValueError as e:
            logging.warning("Malformed request received: %s" % e)
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
        logging.debug("ProtoRE: %s" % protoRE)
        return (r"/%s%s/%s/?/?(\d*)" % (resource, extraRE, protoRE), cls)


testRoute = SocketIOHandler.routes("searchTest", "(123)(.*)", extraSep='/')
application = tornado.web.Application([
    testRoute
])

if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

