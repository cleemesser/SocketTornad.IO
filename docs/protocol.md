Socket-Tornad.IO: Socket.IO for Pythonistas
===========================================

The `Socket.IO` protocol is designed to emulate WebSockets on a variety of fallback protocols for a variety of browsers:

- WebSocket 
- WebSocket over Flash 
- XHR Polling
- XHR Multipart Streaming
- iFrame
- JSONp Polling


This project emulates this functionality in Tornado.

## Protocol Notes

This covers protocol version '0.6'.

A message is sent by the browser for which protocol to use based on the browser's capabilities.

The message indicators are:

- Websocket: "websocket" (both native and emulated websocket AFAIK - flash socket is a sep. proto)
- Flash Socket: "flashsocket"
- iFrame: "htmlfile"
- XHR Multipart: "xhr-multipart"
- XHR Polling: "xhr-polling"
- JSONp Polling: "jsonp-polling"

Each one fires off a specific internal transport...

XHR Polling and JSONP Polling have 3 settings for themselves:

- timeout, defaulted to null ... appears to set heartbeats?
- closeTimeout, integer defaulted to 8000 - number of milliseconds with no traffic to close?
- duration, integer defaulted to 20000 - number of milliseconds to poll?!

On server listen for both request and upgrade...

HTTP Upgrade?

On request run a check on request and response.... 
call the listeners with this,req, res to find one capable of responding

On upgrade check req, socket, true, head... destroy socket if false


### Check Method
check method....  Takes request, response, bool httpUpgrade, headers.
_serveClient path, req, res -- attempts websocket?
otherwise.... look for fallback transport and pass to onConnect / onConnection

Path parts.... part 2 is session id? 1 is transport?

Attach a client object to listeners

Sessions


## Client Object

Takes options - timeout (8000), heartbeatInterval ( 10000) , closeTimeout (0)


frame: "~m~"
heartbeat: "~h~"
json data: "~j~"


broadcast? appears to go to all people listening

### _onMessage - receive message

Decodes using what I assume is standard websocket protocol.

Then looks for datagram indicators of ~j~ and ~h~


## XHR-Polling

### onConnect

#### GET
  set timeout
  establish connection....

#### POST
  'data' event:
    body += message

  'end' event:
    Headers ... Content-Type text/plain
    verify origin headers via Access-Control-Allow-Origin & Allow-Credentials
    otherwise, if origin fails... 401 unauthorized
    message comes in via querystring - parse and handle via onMessage

  200 ,headers
  'ok'

### _write message:
  Content-type text/plain
  content-length
  origin
  200
  message
  'close' (from client _onClose)


## XHR-Multipart

### onConnect

verify origin run including allow-origin & allow-credentials
check access-control-request-method {line 19}

#### GET

Content-Type 'multipart/x-mixed-replace;boundary="socketio"'
Connection keep-alive

onClose w/ end
useChunkedEncodingByDefault = true
shouldKeepAlive = true
200, headers
write(--socketio\n)
? flush? 

#### POST

Content-Type text/plain
'data' event:
  body += message
'end' event:
  parse querystring and pass to message handler
  200,headers
  'ok'

### _write message:

  write 

    Content--Type: text/plain
         <- ; charset=us-ascii (if length === 1 && charCodeAt(0) ==== 6 else "")
    \n\n

    message + "\n"
    "--socketio\n"
    ?flush?

## Websocket *SHOULD* Work like normal websocket.  Will test as needed.


## JSONP-Polling 
  INHERITS from XHR-Polling
  !!!! TODO !!! http://github.com/LearnBoost/Socket.IO-node/blob/master/lib/socket.io/transports/jsonp-polling.js

## iFrame (Htmlfile)

### onConnect

#### GET
  onClose w/ end
  useChunkedEncodingByDefault = true
  shouldKeepAlive = true
  Headers:
    Content-Type text/html
    Connection keep-alive
    Transfer-Encoding chunked

  write 200, headers
  write '<html><body>' + (' ' * 244)
  ? flush ?

#### POST

Content-Type text/plain
'data' event:
  body += message
'end' event:
  parse querystring and pass to message handler
  200,headers
  'ok'

### _write message

write("<script>parent.s_(" + JSON.stringify(message) + ", document);</script>");
? flush ?

## FlashSocket

Either inherits from WebSocket and adds policy server or is JUST policy server...
 
