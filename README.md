# SocketTornad.IO
## Brendan W. McAdams <bmcadams@novus.com>

Implementation of the [Socket.IO][socket_io] Websocket emulation protocol in Python on top of the non-blocking [Tornado Web Framework][tornado].  Socket.IO is a JavaScript library for providing full emulation of Websockets for browsers which don't support it.  While the client-side programmer codes as if they have a constantly open bi-directional communication channel, Socket.IO will (if the browser doesn't support Websockets) use several fallback protocols to provide the behavior.  These fallback protocols require a negotiation between the client and server to determine an agreeable protocol; the [reference implementation][socket_io_node] of the server is done in [Node.JS][node] which was less than agreeable to our needs.  There are also implementations in [Ruby Rack][socket_io_rack] and [Go][socket_io_go] but we rejected those for simlar reasons to Node.JS.

This version is designed for making [Pythonistas](http://python.net/~goodger/projects/pycon/2007/idiomatic/handout.html) happy.

# Implementing SocketTornad.IO

As a user your only major requirement is to subclass `tornad_io.socket_io.SocketIOHandler`.  This base class provides Tornado Handler logic for the entire Socket.IO protocol - it automatically responds to protocol handshakes and notifies you of three events, represented by Python methods on your class:

1. `on_open`: Called when a Socket.IO handshake completes successfully and a client is brought online.  Gets a copy of the `\*args` and `\*\*kwargs` from the request... can be used for you as a user to do further authentication of the connection.  By way of example, we lookup certain authorization information once a connection finishes and decide if we'll allow the connection to continue.  **This is not a required method - you need not implement it if you don't care about it.**
2. `on_close`: Called when a Socket.IO connection is fully closed.  Passes no arguments, but lets you do any cleanup of database handles, etc.  **This is not a required method - you need not implement it if you don't care about it.**
3. `on_message`: The main method.  This is invoked whenever the browser client sends a message.  It is automatically decoded, and any JSON will be passed as a fully parsed Python object.  This method receives a single argument of `message` which contains the parsed message.  You can respond with the `self.send` method (see below)

# Configuring SocketTornad.IO

## Service Settings (ports, etc)
You can configure the service very easily by passing arguments into the Tornado application object.  There are currently 4 user configurable properties:
    
* **enabled_protocols**:  This is a `list` of the Socket.IO protocols the server will respond to requests for.  Clients try them one by one until the server and client both find one they both support.  The possibilities are:
 - *websocket*: Standard HTML5 Spec Websockets.  Our implementation uses the one built into Tornado with a slight tweak to message receipt to enable decoding of the special Socket.IO wire encoding format. (Works in Chrome and any other browser with native Websocket support)
 - *flashsocket*: HTML5 Websockets emulated in Flash for older browsers like Firefox.  *EXACTLY* the same implementation wise to *websocket*, but starts up a Flash policy server which is necessary for Flash sockets to work. (Tested in IE8, and Firefox 3)
 - *xhr-multipart*: XMLHTTPRequest (AJAX) Multipart messaging.  Opens and long polls a GET request to send from server->client, client sends a POST to send client->server.  Uses multipart & chunking to send a continuous stream of messages down the same open GET channel. Best option after *websocket*/*flashsocket*. (Tested in IE8, Firefox 3 and Chrome)
 - *xhr-polling*: XMLHTTPRequest (AJAX) Long Polling.  Client polls on a GET until a message is available, closes the GET after getting a message and then opens a new one until a message is available.  (Tested in IE8, Firefox 3 - does NOT work with Chrome at all)
 - *jsonp-polling*: Identical protocol to *xhr-polling* but pushes Javascript script data via JSONp.  (Tested in IE8, Firefox 3 - does NOT work with Chrome at all)
 - *htmlfile*: Appears to be for much older IE browsers w/o proper AJAX support, creates an AJAX HTMLFile control and does some iframe nastiness.  I haven't found a browser that properly supports this so if you test it let me know ... Copied implementation from reference Node code.

 The default setting is to enable *ALL* protocols, i.e.:
    
        ['websocket', 'flashsocket', 'xhr-multipart', 'xhr-polling', 'jsonp-polling', 'htmlfile']

* **socket_io_port**: The port for the Socket IO Server to listen on.  *This configuration setting is ignored unless you explicitly use the `SocketIOServer` class to start Tornado (See below).*
* **flash_policy_file**  A fully qualified path to a Flash Policy XML File.  A default permissive one is included in this distribution as `flashpolicy.xml`; by default the Flash service looks for `flashpolicy.xml` in the same directory as the current execution.  *This configuration setting is ignored unless you explicitly use the `SocketIOServer` class to start Tornado (See below).*
* **flash_policy_port** The port for the Flash policy server to listen on.  This defaults to port **843** - Flash absolutely *will not* connect to any other port  so if you change this, make sure you setup a portmap on the frontend.  Without a valid policy service Flash fallback sockets will not work. *This configuration setting is ignored unless you explicitly use the `SocketIOServer` class to start Tornado (See below).*
 
Configuring these settings is done by passing them to the `tornado.web.Application` constructor as kwargs:

    application = tornado.web.Application([
        testRoute
    ], enabled_protocols=['websocket', 'flashsocket', 'xhr-multipart', 'xhr-polling'],
       flash_policy_port=8043, flash_policy_file='/etc/lighttpd/flashpolicy.xml', socket_io_port=8888)



# Starting Up
## Best Way: SocketIOServer

The SocketTornad.IO distribution contains a modified version of the Tornado `HTTPServer` class designed to automatically read the necessary configuration settings and start everything up.  If `flashsocket` is enabled it will start the Flash Policy server, and it starts the Socket.IO Service for you (as opposed to you starting it up manually). 

Assuming you set the configuration options on your `Application` instance (or are happy with the defaults) you need merely instantiate a `tornad_io.SocketIOServer`:

    if __name__ == "__main__":
        socketio_server = SocketIOServer(application)

## Starting Manually

If you'd like more control over how you start everything up you can start things manually, similar to the [Tornado Docs][tornado_docs].  This requires booting the IOLoop yourself:

    if __name__ == "__main__":
        flash_policy = tornad_io.websocket.flash.FlashPolicyServer(port=8043, policy_file="/etc/lighttpd/flashpolicy.xml")
        http_server = tornado.httpserver.HTTPServer(application)
        http_server.listen(8888)
        tornado.ioloop.IOLoop.instance().start()


[socket_io]: http://socket.io "Socket.IO"
[socket_io_node]: http://github.com/learnboost/socket.io-node "Socket.IO Node Server"
[socket_io_go] http://github.com/madari/go-socket.io "Socket.IO Go Server" 
[socket_io_rack] http://github.com/markjeee/Socket.IO-rack "Socket.IO Ruby Rack Server"
[tornado]: http://www.tornadoweb.org/ "Tornado"
[tornado_docs]: http://www.tornadoweb.org/documentation "Tornado Docs"
[node] http://nodejs.org "Node.JS"

