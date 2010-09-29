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

    connected = False
    handshaked = False
    session = None
    _write_queue = []
    options = {
        'timeout': 12000
    }

    _heartbeats = 0

    handler = None

    def __init__(self, handler):
        logging.debug("Initializing SocketIOProtocol...")
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
        logging.debug("Session Open. Creating session.")
        payload = []

        self.connected = True

        if not self.handshaked:
            self.session = beaker.session.Session({})
            logging.debug("Generated a beaker session: %s [id: %s]" % (self.session, self.session.id))
            payload.append(self.session.id)
            self.handshaked = True

        payload.extend(self._write_queue)
        self._write_queue = []
        logging.debug("\n Writing out Payload: %s \n" % (payload))
        self.send(payload)

        # TODO Logging full info on connection?
        # TODO Timeout data, etc
        if self.options['timeout']:
            logging.debug("Setting up call back for %d ms" % self.options['timeout'])
            self._timeout = util.PeriodicCallback(self._heartbeat, self.options['timeout'])
            self._timeout.start()

        self.async_callback(self.on_open)(*args, **kwargs)


    def _heartbeat(self):
        # TODO - Check we *RECEIVE* heartbeats
        if self.stream.socket == None:
            logging.debug("[%s] closed stream? %s Connected? %s" % (self.session.id, self.stream.closed(), self.connected))
            logging.info("Connection no longer active.  Shutting down heartbeat scheduler.")
            self._timeout.stop()
            self._abort()
        else:
            self._heartbeats += 1
            logging.debug("[%s] Sending Heartbeat %d" % (self.session.id, self._heartbeats))
            self.send('~h~%d' % self._heartbeats)

    def on_heartbeat(self, beat):
        if beat == self._heartbeats:
            logging.debug("[%s] Received a heartbeat... " % beat)
            self.reset_timeout()
        else:
            logging.warning("Mismatch on heartbeat count.  Timeout may occur. Got %d but expected %d" % (beat, self._heartbeats)) # This logging method may race

    def reset_timeout(self):
        pass


    def send(self, message):
        """Message to send data to the client.
        Encodes in Socket.IO protocol and
        ensures it doesn't send if session
        isn't fully open yet."""
        logging.debug("[%s] Writing a message: %s {%s}" % (self.session.id, message, type(message)))
        if isinstance(message, list):
            for m in message:
                self.send(m)
        else:
            self.async_callback(self._write)(
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
                logging.debug("Encoding an Object or Dictionary: %s" % message)
                encoded += self._encode('~j~' + json.dumps(message, use_decimal=True))
        else:
            encoded += "%s%d%s%s" % (FRAME, len(message), FRAME, message)

        logging.debug("Encoded Message: %s", encoded)

        return encoded

    def _decode(self, message):
        """decode message from Socket.IO Protocol."""
        messages = []
        logging.debug("Decoding Message: %s", message)
        parts = message.split("~m~")[1:]
        for i in range(1, len(parts), 2):
            l = int(parts[i - 1])
            data = parts[i]
            if len(data) != l:
                # TODO - Fail on invalid length?
                logging.warning("Possibly invalid message. Expected length '%d', got '%d'" % (l, len(data)))
            # Check the frame for an internal message
            in_frame = data[:3]
            if in_frame == '~h~':
                logging.debug("Heartbeat frame.")
                self.async_callback(self.on_heartbeat)(int(data[3:]))
                continue
            elif in_frame == '~j~':
                logging.debug("JSON Data.")
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
        logging.warning("[socketio protocol] Default call to _write. NOOP. [%s]" % message)
        pass

    def timed_callback(self, callback, time, *args, **kwargs):
        cb = async_callback(callback, *args, **kwargs)
        logging.debug("Callback: %s Timer: %s" % (db, time))

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
                logging.error("Uncaught exception in %s",
                              self.request.path, exc_info=True)
                self._abort()
        #logging.debug("[socketio protocol] Setup callback wrapper for async: %s" % callback)
        return wrapper

    def _abort(self):
        self.connected = False
        self.stream.close()

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
