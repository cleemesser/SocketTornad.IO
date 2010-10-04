SocketTornad.IO
===============
Release 0.1.2
^^^^^^^^^^^^^
Brendan W. McAdams bmcadams@novus.com
-------------------------------------

Contributors
~~~~~~~~~~~~

`Matt Swanson <http://github.com/swanson>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Implementation of the `Socket.IO <http://socket.io>`_ Websocket
emulation protocol in Python on top of the non-blocking
`Tornado Web Framework <http://www.tornadoweb.org/>`_. Socket.IO is
a JavaScript library for providing full emulation of Websockets for
browsers which don't support it. While the client-side programmer
codes as if they have a constantly open bi-directional
communication channel, Socket.IO will (if the browser doesn't
support Websockets) use several fallback protocols to provide the
behavior. These fallback protocols require a negotiation between
the client and server to determine an agreeable protocol; the
`reference implementation <http://github.com/learnboost/socket.io-node>`_
of the server is done in Node.JS which was less than agreeable to
our needs. There are also implementations in Ruby Rack and Go but
we rejected those for simlar reasons to Node.JS.

This version is designed for making
`Pythonistas <http://python.net/~goodger/projects/pycon/2007/idiomatic/handout.html>`_
happy.

Implementing SocketTornad.IO
============================

As a user your only major requirement is to subclass
``tornad_io.socket_io.SocketIOHandler``. This base class provides
Tornado Handler logic for the entire Socket.IO protocol - it
automatically responds to protocol handshakes and notifies you of
three events, represented by Python methods on your class:


1. ``on_open``: Called when a Socket.IO handshake completes
   successfully and a client is brought online. Gets a copy of the
   ``*args`` and ``**kwargs`` from the request... can be used for you
   as a user to do further authentication of the connection. By way of
   example, we lookup certain authorization information once a
   connection finishes and decide if we'll allow the connection to
   continue.
   **This is not a required method - you need not implement it if you don't care about it.**
2. ``on_close``: Called when a Socket.IO connection is fully
   closed. Passes no arguments, but lets you do any cleanup of
   database handles, etc.
   **This is not a required method - you need not implement it if you don't care about it.**
3. ``on_message``: The main method. This is invoked whenever the
   browser client sends a message. It is automatically decoded, and
   any JSON will be passed as a fully parsed Python object. This
   method receives a single argument of ``message`` which contains the
   parsed message. You can respond with the ``self.send`` method (see
   below)

You can send messages to the client by use of the ``self.send``
method. This takes a single argument of ``message`` and transmits
it to the client. If you pass a string it will be pased "as is" to
the browser; if you want to send JSON you should pass a ``dict``
in, which will be JSON encoded and marked as JSON in the Socket.IO
wire format. An Object is also acceptable as long as *simplejson*
is able to encode it to JSON.

There *is* fallback code for the JSON import - if you don't have
``simplejson`` installed it will import the ``json`` module (based
on ``simplejson``) which has been included with Python since 2.6
instead (thanks to `swanson <http://github.com/swanson>`_ for the
patch). However, the version of ``json`` which ships with Python
lacks built in support for encoding ``decimal.Decimal`` objects,
which is why we prefer (as specified in ``setup.py``)
``simplejson >= 2.1``. If you do not have an appropriate version of
``simplejson`` installed and try to send an object or ``dict``
containing ``decimal.Decimal`` instances to the client, you may
encounter errors.

For those of you who know Tornado already, do *not* call the
``self.write`` method unless you want things to act weird.
``self.write`` still (in the current iteration) sends raw data to
the client - but Socket.IO uses a wire format which requires
certain encoding. Anything you pass via ``self.write`` will likely
not be understood by the client.

This is an example handler:

::

    class EchoHandler(SocketIOHandler):
        def on_open(self, *args, **kwargs):
            logging.info("Socket.IO Client connected with protocol '%s' {session id: '%s'}" % (self.protocol, self.session.id))
            logging.info("Extra Data for Open: '%s'" % (kwargs.get('extra', None)))
    
        def on_message(self, message):
            logging.info("[echo] %s" % message)
            self.send("[echo] %s" % message)
    
        def on_close(self):
            logging.info("Closing Socket.IO Client for protocol '%s'" % (self.protocol))

This handler is meant to be simple: It merely echoes back any
message it receives to the client. Were you to test this in your
browser your console will reflect back what you send:

::

    > socket.send("OMG! Ponies!")
    [echo] OMG! Ponies!

(In this case I have my test page set to print any messages to
``console.log()``.)

Useful properties
-----------------

Every subclass of ``SocketIOHandler`` has a few useful properties
attached to it:


-  ``protocol``: This is a string containing the name of the
   protocol currently being used to communicate with the client.
-  ``session``: This is a `Beaker <http://beaker.groovie.org>`_
   Session object which can be used to track information about the
   connection in question. We use it internally to direct output to
   the right place in polling. Feel free to save your own data - just
   make sure to call ``self.session.save()`` if you modify it or your
   changes will be lost.

Configuring SocketTornad.IO
===========================

Routes (e.g. how clients access you)
------------------------------------

It is necessary in Tornado set up your 'resources' (known in some
frameworks as 'routes') which define what paths are valid and what
controllers handle the request. Because the paths Socket.IO uses to
negotiate the connection and speak (esp. in the fallback protocols)
are hairy, we have instead created a ClassMethod on
``SocketIOHandler`` which allows you to easily get the correct
route for your service:

::

    echoRoute = EchoHandler.routes("echoTest", "(?P<sec_a>123)(?P<sec_b>.*)", extraSep='/')

This returns the data structure which Tornado expects to configure
itself, with all requests for '/echoTest' pointed at the
EchoHandler class. For the curious, the structure returned looks
like this:

::

    ('/(?P<resource>echoTest)/(?P<extra>(?P<sec_a>123)(?P<sec_b>.*))/(?P<protocol>(websocket|xhr-multipart|htmlfile|jsonp-polling|flashsocket|xhr-polling))/?(?P<session_id>[0-9a-zA-Z]*?)/?((?P<protocol_init>\\d*?)|(?P<xhr_path>\\w*?))/?(?P<jsonp_index>\\d*?)', <class 'tornad_io.EchoHandler'>)

Hence the ``routes`` classmethod to easily configure with...
``resource`` can be any valid string, including, if necessary, a
Regular Expression. Any requests beginning with your ``resource``
parameter will be routed to ``EchoHandler`` for processing. The
additional cruft in there are regular expressions to handle the
myriad of extra path information Socket.IO ships to find a valid
protocol.

We also accept two additional optional parameters to configure
routes (only the ``resource`` parameter is required).


-  ``extraRE`` is an optional string containing a regular
   expression for 'extra' information to capture on the URL. In my
   case, I have a PHP process pass an authenticated secure token to
   the Tornado process on each request to help identify and authorize
   a user. I pass this as part of the Socket.IO ``resource`` - while
   my Tornado resource is configured as 'echoTest', I want to capture
   and separate the additional secure token. By setting up an
   ``extraRE`` SocketTornad.IO will automatically save the extra data
   in ``**kwargs['extra']`` - specifically accessible in ``on_open``
   for further authentication. You *MAY* put capture groups inside
   ``extraRE`` - if you name them they are available from ``on_open``
   in ``**kwargs``, otherwise they will be in unnamed buckets inside
   of ``*args*``.

-  ``extraSep`` indicates a character to separate the 'base'
   ``resource`` and ``extraRE`` with. By default there is none - they
   are expected to run together. I typically set ``extraSep`` to a '/'
   character.


After that you simply need to pass the configured route to
Tornado:

::

    application = tornado.web.Application([
        echoRoute
    ])

Service Settings (ports, etc)
-----------------------------

You can configure the service very easily by passing arguments into
the Tornado application object. There are currently 4 user
configurable properties:


-  **enabled\_protocols**: This is a ``list`` of the Socket.IO
   protocols the server will respond to requests for. Clients try them
   one by one until the server and client both find one they both
   support. The possibilities are:
-  *websocket*: Standard HTML5 Spec Websockets. Our implementation
   uses the one built into Tornado with a slight tweak to message
   receipt to enable decoding of the special Socket.IO wire encoding
   format. (Works in Chrome and any other browser with native
   Websocket support)
-  *flashsocket*: HTML5 Websockets emulated in Flash for older
   browsers like Firefox. *EXACTLY* the same implementation wise to
   *websocket*, but starts up a Flash policy server which is necessary
   for Flash sockets to work. (Tested in IE8, and Firefox 3)
-  *xhr-multipart*: XMLHTTPRequest (AJAX) Multipart messaging.
   Opens and long polls a GET request to send from server to client,
   client sends a POST to send client to server. Uses multipart &
   chunking to send a continuous stream of messages down the same open
   GET channel. Best option after *websocket*/*flashsocket*. (Tested
   in IE8, Firefox 3 and Chrome)
-  *xhr-polling*: XMLHTTPRequest (AJAX) Long Polling. Client polls
   on a GET until a message is available, closes the GET after getting
   a message and then opens a new one until a message is available.
   (Tested in IE8, Firefox 3 - does NOT work with Chrome at all)
-  *jsonp-polling*: Identical protocol to *xhr-polling* but pushes
   Javascript script data via JSONp. (Tested in IE8, Firefox 3 - does
   NOT work with Chrome at all)
-  *htmlfile*: Appears to be for much older IE browsers w/o proper
   AJAX support, creates an AJAX HTMLFile control and does some iframe
   nastiness. I haven't found a browser that properly supports this so
   if you test it let me know ... Copied implementation from reference
   Node code.

The default setting is to enable *ALL* protocols, i.e.:

::

        ['websocket', 'flashsocket', 'xhr-multipart', 'xhr-polling', 'jsonp-polling', 'htmlfile']


-  **socket\_io\_port**: The port for the Socket IO Server to
   listen on.
   *This configuration setting is ignored unless you explicitly use the ``SocketIOServer`` class to start Tornado (See below).*
-  **flash\_policy\_file** A fully qualified path to a Flash Policy
   XML File. A default permissive one is included in this distribution
   as ``flashpolicy.xml``; by default the Flash service looks for
   ``flashpolicy.xml`` in the same directory as the current execution.
   *This configuration setting is ignored unless you explicitly use the ``SocketIOServer`` class to start Tornado (See below).*
-  **flash\_policy\_port** The port for the Flash policy server to
   listen on. This defaults to port **843** - Flash absolutely
   *will not* connect to any other port so if you change this, make
   sure you setup a portmap on the frontend. Without a valid policy
   service Flash fallback sockets will not work.
   *This configuration setting is ignored unless you explicitly use the ``SocketIOServer`` class to start Tornado (See below).*

Configuring these settings is done by passing them to the
``tornado.web.Application`` constructor as kwargs:

::

    application = tornado.web.Application([
        echoRoute 
    ], enabled_protocols=['websocket', 'flashsocket', 'xhr-multipart', 'xhr-polling'],
       flash_policy_port=8043, flash_policy_file='/etc/lighttpd/flashpolicy.xml', socket_io_port=8888)

Starting Up
===========

Best Way: SocketIOServer
------------------------

The SocketTornad.IO distribution contains a modified version of the
Tornado ``HTTPServer`` class designed to automatically read the
necessary configuration settings and start everything up. If
``flashsocket`` is enabled it will start the Flash Policy server,
and it starts the Socket.IO Service for you (as opposed to you
starting it up manually).

Assuming you set the configuration options on your ``Application``
instance (or are happy with the defaults) you need merely
instantiate a ``tornad_io.SocketIOServer``:

::

    if __name__ == "__main__":
        socketio_server = SocketIOServer(application)

Starting Manually
-----------------

If you'd like more control over how you start everything up you can
start things manually, similar to the
`Tornado Docs <http://www.tornadoweb.org/documentation>`_. This
requires booting the IOLoop yourself:

::

    if __name__ == "__main__":
        flash_policy = tornad_io.websocket.flash.FlashPolicyServer(port=8043, policy_file="/etc/lighttpd/flashpolicy.xml")
        http_server = tornado.httpserver.HTTPServer(application)
        http_server.listen(8888)
        tornado.ioloop.IOLoop.instance().start()

Examples
========

Chatroom Example
----------------

There is a chatroom example application contributed by
`swanson <http://github.com/swanson>`_. It is in the
``examples/chatroom`` directory. For instructions, please see its
`README <http://github.com/novus/SocketTornad.IO/blob/master/examples/chatroom/README.md>`_.


