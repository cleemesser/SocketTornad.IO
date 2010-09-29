import logging
import re
import urlparse
import functools
# Newer versions of SimpleJSON from what's in Py 2.6 etc 
# have builtin decimal support and are preferred IMHO
import simplejson as json
from decimal import Decimal

import tornado.escape
import tornado.web
import tornado.httpserver

from tornad_io import util

from tornado import ioloop

# Uses Beaker for session management which enables persistence, etc.
# 
# As to the best of my knowledge the standard Socket.IO implementation
# doesn't use cookies for session tracking we don't for now either.
# Session ID's for now go away with say a websocket dropping but are reused
# by XHR, etc
#
# TODO - Look into cookie usage

import beaker.session

FRAME = '~m~'


class SocketIOProtocol(tornado.web.RequestHandler):
    """ Base interface class for Socket.IO implementing
    adapters (specific protocols like XHRPolling, etc)

    TODO - Options handling for Timeouts, heartbeat etc

    Based on tornado.websocket.WebSocketHandler from the
    Tornado Distribution, written by Jacob Kristhammar"""


    ioloop = ioloop.IOLoop.instance()
    #ioloop = ioloop.IOLoop()

    # Indicates if it is a single bidirectional socket
    # or a set of asynch messages. Controls output handling.
    # Websockets == False, Polling = True
    asynchronous = True
    connected = False
    handshaked = False
    session = {'id': None}
    _write_queue = []
    # TODO - Pass config in at constructor
    config = {
        'timeout': 12000,
        'origins': [('*', '*')] # Tuple of (host, port)... * acceptable
    }

    _heartbeats = 0

    handler = None

    def debug(self, message):
        logging.debug("[%s | %s | %s]  %s" %
                      (getattr(self.session, 'id', None), self.request.method, self.__class__.__name__,
                       message))

    def info(self, message):
        logging.info("[%s | %s | %s]  %s" %
                      (getattr(self.session, 'id', None), self.request.method, self.__class__.__name__,
                       message))

    def error(self, message, exception, **kwargs):
        logging.error("[%s | %s | %s]  %s" %
                      (getattr(self.session, 'id', None), self.request.method, self.__class__.__name__,
                     message), exception, **kwargs)

    def warning(self, message):
        logging.warning("[%s | %s | %s]  %s" %
                       (getattr(self.session, 'id', None), self.request.method, self.__class__.__name__,
                       message))


    def __init__(self, handler):
        self.handler = handler
        self.application = self.handler.application
        self.request = self.handler.request


    def open(self, *args, **kwargs):
        """Internal method for setting up session
        invocation. Don't mess with me.
        Left with non-privated naming to stay compatible
        with existing Tornado implementation of Websockets.

        This method is similar to the Client._payload method
        from Socket.IO-Node
        """
        self.debug("Session Open. Creating session.")
        payload = []

        self.connected = True



        if not self.handshaked:
            self.session = beaker.session.Session(kwargs)
            payload.append(self.session.id)
            self.handshaked = True

        self.session['output_handle'] = self
        self.session.save()
        self.debug("Saved Session: %s" % self.session)

        payload.extend(self._write_queue)
        self._write_queue = []
        self.debug("Writing out Payload: %s \n" % (payload))
        self.send(payload)

        # TODO Logging full info on connection?
        # TODO Timeout data, etc
        if self.config['timeout']:
            self.debug("Setting up call back for %d ms" % self.config['timeout'])
            self._timeout = util.PeriodicCallback(self._heartbeat, self.config['timeout'])
            self._timeout.start()

        self.async_callback(self.on_open)(*args, **kwargs)


    def _heartbeat(self):
        # TODO - Check we *RECEIVE* heartbeats
        try:
            self._heartbeats += 1
            self.debug("Sending Heartbeat %d" % (self._heartbeats))
            self.send('~h~%d' % self._heartbeats)
        except Exception as e:
            #logging.debug("[%s] closed stream? %s Connected? %s" % (self.session.id, self.stream.closed(), self.connected))
            self.info("Connection no longer active.  Shutting down heartbeat scheduler.")
            self._timeout.stop()
            self._abort()

    def on_heartbeat(self, beat):
        if beat == self._heartbeats:
            self.debug("[%s] Received a heartbeat... " % beat)
            self.reset_timeout()
        else:
            self.warning("Mismatch on heartbeat count.  Timeout may occur. Got %d but expected %d" % (beat, self._heartbeats)) # This logging method may race

    def reset_timeout(self):
        pass

    def verify_origin(self, origin):
        self.info("Verify Origin: %s" % origin)
        origins = self.config['origins']
        url = urlparse.urlparse(origin)
        host = url.hostname
        port = url.port
        return filter(lambda t: (t[0] == '*' or t[0].lower() == host.lower()) and (t[1] == '*' or  t[1] == int(port)), origins)

    def send(self, message):
        """Message to send data to the client.
        Encodes in Socket.IO protocol and
        ensures it doesn't send if session
        isn't fully open yet."""
        self.debug("Writing a message: %s[ Session : %s ] " % (message, self.session))

        if self.asynchronous:
            out_fh = self.session['output_handle']
        else:
            out_fh = self

        self.debug("Am I asnychronous? %s out_fh: %s" % (self.asynchronous, out_fh))

        if isinstance(message, list):
            for m in message:
                out_fh.send(m)
        else:
            self.async_callback(out_fh._write)(
                                self._encode(message))


    def _encode(self, message):
        """Encode message in Socket.IO Protocol.

        TODO - Custom Encoder support for simplejson?"""
        encoded = ''
        if isinstance(message, list):
            for m in message:
                encoded += self._encode(message)
        elif not isinstance(message, (unicode, str)) and isinstance(message, (object, dict)):
            """
            Strings are objects... messy test.
            """
            if message is not None:
                encoded += self._encode('~j~' + json.dumps(message, use_decimal=True))
        else:
            encoded += "%s%d%s%s" % (FRAME, len(message), FRAME, message)

        self.debug("Encoded Message: %s" % encoded)

        return encoded

    def _decode(self, message):
        """decode message from Socket.IO Protocol."""
        messages = []
        self.debug("Decoding Message: %s" % message)
        parts = message.split("~m~")[1:]
        for i in range(1, len(parts), 2):
            l = int(parts[i - 1])
            data = parts[i]
            if len(data) != l:
                # TODO - Fail on invalid length?
                self.warning("Possibly invalid message. Expected length '%d', got '%d'" % (l, len(data)))
            # Check the frame for an internal message
            in_frame = data[:3]
            if in_frame == '~h~':
                self.async_callback(self.on_heartbeat)(int(data[3:]))
                continue
            elif in_frame == '~j~':
                data = json.loads(data[3:], parse_float=Decimal)
            messages.append(data)

        return messages

    def _on_message(self, message):
        """ Internal handler for new incoming messages.
        After decoding, invokes on_message"""
        messages = self._decode(message)
        for msg in messages:
            self.async_callback(self.on_message)(msg)

    def _write(self, message):
        """Write method which all protocols must define to
        indicate how to push to their wire"""
        self.warning("[socketio protocol] Default call to _write. NOOP. [%s]" % message)
        pass


    def async_callback(self, callback, *args, **kwargs):
        """Wrap callbacks with this if they are used on asynchronous requests.

        Catches exceptions properly and closes this connection if an exception
        is uncaught.
        """
        if args or kwargs:
            callback = functools.partial(callback, *args, **kwargs)
        def wrapper(*args, **kwargs):
            try:
                return callback(*args, **kwargs)
            except Exception, e:
                self.error("Uncaught exception in %s",
                              self.request.path, exc_info=True)
                self._abort()
        #logging.debug("[socketio protocol] Setup callback wrapper for async: %s" % callback)
        return wrapper

    def _abort(self):
        self.connected = False
        #self.stream.close()

    def on_open(self, *args, **kwargs):
        """Invoked when a protocol socket is opened...
        Passes in the args & kwargs from the route
        as Tornado deals w/ regex groups, via _execute method.
        See the tornado docs and code for detail."""
        self.handler.on_open(*args, **kwargs)

    def on_message(self, message):
        """Handle incoming messages on the protocol socket
        This method *must* be overloaded
        TODO - Abstract Method imports via ABC
        """
        self.handler.on_message(message)

    def on_close(self):
        """Invoked when the protocol socket is closed."""
        self.handler.on_close()
