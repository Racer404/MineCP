import websocket
import requests
import threading
import time
import json
import os

class Bot:
    def __init__(self, app_id:str='', client_secret:str=''):
        self.app_id = app_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expiresAt = None
        self.token_safety_time_margin = 50.
        self.agreed_heartbeat_interval = 60
        self.heartbeat_payload_d = None

    def update_access_token(self):
        time_now = time.time()
        update_need = True

        if self.access_token:
            time_remain = (self.token_expiresAt - self.token_safety_time_margin) - time_now
            if time_remain > 0:
                update_need = False

        if update_need:
            print("fetching new token...")
            url = "https://api.bot.qq.com/app/getAppAccessToken"
            payload = {"appId": self.app_id, "clientSecret": self.client_secret}
            response = requests.post(url, json=payload).json()
            self.access_token = response['access_token']
            self.token_expiresAt = time_now + float(response['expires_in'])

    def getWebSocketTerminal(self) -> str:
        api = "https://api.bot.qq.com/gateway"
        header = {"Authorization": "QQBot " + self.access_token}
        response = requests.get(api, headers=header)
        terminal = response.json()['url']
        return terminal

    def listenToSocket(self, url):

        def on_message(socket, message):
            print(f"Received: {message}")
            op_ = json.loads(message)['op']

            if op_ == 10:
                print("Handshake")
                self.agreed_heartbeat_interval = int(json.loads(message)['d']['heartbeat_interval'] / 1000)
                authentication_payload = {
                    "op": 2,
                    "d": {
                        "token": f"QQBot {self.access_token}",
                        "intents": 33554432,
                        "shard": [0, 1]
                    }
                }
                socket.send(json.dumps(authentication_payload))

            elif op_ == 0:
                print("Dispatch from server...")
                t_ = json.loads(message)['t']

                if t_ == 'READY':
                    print("Handshake successfully")
                    self.heartbeat_payload_d = "null"


            elif op_ == 11:
                print("pong")

        def on_error(error):
            print(f"Error: {error}")

        def on_close(socket, close_status_code, close_msg):
            print("Connection closed")

        def on_open(socket):
            print("Connected to server")
            payload = {
                "op": 2,
                "d": {
                    "token": f"QQBot {bot.access_token}",
                    "intents": 513,
                    "shard": [0, 4],
                    "properties": {
                        "$os": "linux",
                        "$browser": "my_library",
                        "$device": "my_library"
                    }
                }
            }
            ws.send(json.dumps(payload))

        def heartbeat(socket):
            while True:
                print("heartbeat function")
                self.agreed_heartbeat_interval = 10
                time.sleep(self.agreed_heartbeat_interval)

                if self.heartbeat_payload_d:
                    heartbeat_payload = {
                        "op": 1,
                        "d": self.heartbeat_payload_d
                    }
                    socket.send(json.dumps(heartbeat_payload))
                    print("ping")
                    self.heartbeat_payload_d = None


        ws = websocket.WebSocketApp(url)
        ws.on_message = on_message

        print("threading start")
        threading.Thread(
            target=heartbeat,
            args=(ws,),
            daemon=True
        ).start()

        ws.run_forever()

secret = str(os.getenv('QQ_APP_SECRET'))
bot = Bot('1905231300', secret)

bot.update_access_token()
wssTerminal = bot.getWebSocketTerminal()

bot.listenToSocket(wssTerminal)