import websockets
import asyncio
import json
import time, os


class HttpWSSProtocol(websockets.WebSocketServerProtocol):
    rwebsocket = None
    rddata = None
    async def handler(self):
        try:
            request_line, headers = await websockets.http.read_message(self.reader)
            method, path, version = request_line[:-2].decode().split(None, 2)
            websockets.accept()
        except Exception as e:
            print(e.args,16)
            self.writer.close()
            self.ws_server.unregister(self)

            raise

        # TODO: Check headers etc. to see if we are to upgrade to WS.
        if path == '/ws':
            # HACK: Put the read data back, to continue with normal WS handling.
            self.reader.feed_data(bytes(request_line))
            self.reader.feed_data(headers.as_bytes().replace(b'\n', b'\r\n'))

            return await super(HttpWSSProtocol, self).handler()
        else:
            try:
                return await self.http_handler(method, path, version)
            except Exception as e:
                print(e, 33)
            finally:

                self.writer.close()
                self.ws_server.unregister(self)


    async def http_handler(self, method, path, version):
        response = ''
        try:

            googleRequest = await self.reader._buffer.decode('utf-8')
            print(googleRequest)
            googleRequestJson = json.loads(googleRequest)
            
            req = googleRequestJson['queryResult']['intent']['displayName']
            ESPparameters = googleRequestJson['queryResult']['parameters']
            if  req == 'control':
                ESPparameters['query'] = 'cmd'
            elif req == 'Level':
                ESPparameters['query'] = 'tank'
            elif req == 'Light':
                ESPparameters['query'] = '?'
            else:
                print("Unkown intent")
                
            # send command to ESP over websocket
            if self.rwebsocket== None:
                print("Device is not connected!")
                return
            await self.rwebsocket.send(json.dumps(ESPparameters))

            #Wait for response and send it back to Dialogueflow as is
            self.rddata = await self.rwebsocket.recv()
            print(self.rddata)
            state = json.loads(self.rddata)['state']
            level = json.loads(self.rddata)['level']
            cmnd = json.loads(self.rddata)['query']
            
            if cmnd == 'cmd':
                self.rddata = 'Turning '+state
            elif cmnd == '?':
                self.rddata = 'It is Turned '+state
            elif cmnd == 'tank':
                self.rddata = 'The water tank is '+level+'% full'
            else:
                self.rddata = 'There was a problem while communicating'
                
            response = '\r\n'.join([
                'HTTP/1.1 200 OK',
                'Content-Type: application/json',
                '',
                '{"payload": { "google": { "expectUserResponse": true, "richResponse": { "items": [{ "simpleResponse": { "textToSpeech": "'+self.rddata+'" }}]}}}, "fulfillmentMessages": [ { "text": { "text": [ "'+self.rddata+'" ]}  } ] }',
            ])
        except Exception as e:
            print(e, 87)
        self.writer.write(response.encode())

def updateData(data):
    HttpWSSProtocol.rddata = data

async def ws_handler(websocket, path):
    game_name = 'g1'
    try:
        HttpWSSProtocol.rwebsocket = websocket
        await websocket.send(json.dumps({'event': 'OK'}))
        data ='{"empty":"empty"}'
        while True:
            data = await websocket.recv()
            updateData(data)
    except Exception as e:
        print(e, 103)
    finally:
        print("Done")



port = int(os.getenv('PORT', 5687))
start_server = websockets.serve(ws_handler, '', port, klass=HttpWSSProtocol)
# logger.info('Listening on port %d', port)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
