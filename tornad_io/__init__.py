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
import tornad_io.websocket.flash
import tornad_io.polling
import tornad_io.socket_io

import beaker.session

logging.getLogger().setLevel(logging.DEBUG)
# TODO - Monkey Patchable package object?
PROTOCOLS = {
    "xhr-polling": tornad_io.polling.XHRPollingSocketIOHandler,
    "xhr-multipart": tornad_io.polling.XHRMultiPartSocketIOHandler,
    "jsonp-polling": tornad_io.polling.JSONPPollingSocketIOHandler,
    "htmlfile": tornad_io.polling.HTMLFileSocketIOHandler,
    "websocket": tornad_io.websocket.WebSocketIOHandler,
    "flashsocket": tornad_io.websocket.flash.FlashSocketIOHandler,
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
            extra = kwargs['extra']
            proto_type = kwargs['protocol']
            proto_init = kwargs['protocol_init']
            session_id = kwargs['session_id']
            logging.debug("request method %s" % self.request.method)
            logging.debug("Initializing %s(%s) Session ID: %s... Extra Data: %s [PATH: %s XHR PATH: %s]" % (proto_type, proto_init, session_id, extra, kwargs['resource'], kwargs.get('xhr_path', None)))
            protocol = PROTOCOLS.get(proto_type, None)
            if protocol and issubclass(protocol, tornad_io.socket_io.SocketIOProtocol):
                self.protocol = protocol(self)
                if kwargs['session_id']:
                    self.protocol.info("Session ID passed to invocation... (%s)" % kwargs['session_id'])
                    sess = beaker.session.Session(kwargs, id=kwargs['session_id'])
                    if sess.is_new:
                        raise Exception('Invalid Session ID.  Could not find existing client in sessions.')

                    if not sess.has_key('output_handle') and sess['output_handle']:
                        raise Exception('Invalid Session.  Could not find a valid output handle.')

                    self.protocol.handshaked = True
                    self.protocol.connected = True
                    self.protocol.session = sess
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
            if extraRE[0] != '(?P<extra>':
                if extraRE[0] == '(':
                    extraRE = r'(?P<extra>%s)' % extraRE
                else:
                    extraRE = r"(?P<extra>%s)" % extraRE
            if extraSep:
                extraRE = extraSep + extraRE
        else:
            extraRE = "(?P<extra>)"

        protoRE = "(%s)" % "|".join(PROTOCOLS.keys())
        route = (r"/(?P<resource>%s)%s/(?P<protocol>%s)/?/?(?P<protocol_init>\d*?)/?(?P<session_id>[0-9a-zA-Z]*?)/?(?P<xhr_path>\w*?)" % (resource, extraRE, protoRE), cls)
        logging.debug("Route: '%s'" % str(route))
        return route


class TestHandler(SocketIOHandler):
    def on_message(self, message):
        logging.debug("[echo] %s" % message)
        self.send("[echo] %s" % message)

testRoute = TestHandler.routes("searchTest", "(?P<sec_a>123)(?P<sec_b>.*)", extraSep='/')
application = tornado.web.Application([
    testRoute
])

if __name__ == "__main__":
    #flash_policy = tornad_io.websocket.flash.FlashPolicyServer()
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

