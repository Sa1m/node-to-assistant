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
        except Exception as e:
            print(e.args)
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
                print(e)
            finally:
                self.writer.close()
                self.ws_server.unregister(self)

    async def http_handler(self, method, path, version):
        response = ''
        try:

            googleRequest = self.reader._buffer.decode('utf-8')
            googleRequestJson = json.loads(googleRequest)
            
            req = googleRequestJson['queryResult']['intent']['displayName']
            ESPparameters = googleRequestJson['queryResult']['parameters']
            if  req == 'Ctrl-light':
                ESPparameters['query'] = 'cmd'
            elif req == 'Level':
                ESPparameters['query'] = 'tank'
            elif req == 'Light':
                ESPparameters['query'] = '?'
            elif req == 'Calib-diameter':
                ESPparameters['query'] = 'calib_d'
            elif req == 'Calib-height':
                ESPparameters['query'] = 'calib_h'
            elif req == 'Calib':
                ESPparameters['query'] = 'calib'
            elif req == 'Reset':
                ESPparameters['query'] = 'rst'
            elif req == 'Thresh':
                ESPparameters['query'] = 'thresh'
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
            diameter = json.loads(self.rddata)['diameter']
            height = json.loads(self.rddata)['height']
            thresh = json.loads(self.rddata)['thresh']

            
            if cmnd == 'cmd':
                self.rddata = 'Turning '+state
            elif cmnd == '?':
                self.rddata = 'It is Turned '+state
            elif cmnd == 'tank':
                self.rddata = 'The water tank is '+level+'% full'
            elif cmnd == 'calib_d':
                self.rddata = 'Tank Diameter is set to '+diameter+'cm'
            elif cmnd == 'calib_h':
                self.rddata = 'Tank Height is set to '+height+'cm'
            elif cmnd == 'calib':
                self.rddata = 'Tank Height is '+height+'cm and Diameter is '+diameter+'cm with Threshold of '+thresh+'cm'
            elif cmnd == 'rst':
                self.rddata = 'Reset successfully'
            elif cmnd == 'thresh':
                self.rddata = 'Measuring Threshold is set to '+thresh+'cm'
            else:
                self.rddata = 'There was a problem while communicating'
                
            response = '\r\n'.join([
                'HTTP/1.1 200 OK',
                'Content-Type: application/json',
                '',
                '{"payload": { "google": { "expectUserResponse": true, "richResponse": { "items": [{ "simpleResponse": { "textToSpeech": "'+self.rddata+'" }}]}}}, "fulfillmentMessages": [ { "text": { "text": [ "'+self.rddata+'" ]}  } ] }',
            ])
        except Exception as e:
            print(e)
        self.writer.write(response.encode())

def updateData(data):
    HttpWSSProtocol.rddata = data

async def ws_handler(websocket, path):
    try:
        HttpWSSProtocol.rwebsocket = websocket
        await websocket.send(json.dumps({'event': 'OK'}))
        data ='{"empty":"empty"}'
        while True:
            data = await websocket.recv()
            updateData(data)
    except Exception as e:
        print(e)
    finally:
        print("Done")

port = int(os.getenv('PORT', 5687))
start_server = websockets.serve(ws_handler, '', port, klass=HttpWSSProtocol)
# logger.info('Listening on port %d', port)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
