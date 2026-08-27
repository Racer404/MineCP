import websocket
import requests
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

    def listenToSocket(self, on_receive_method):

        on_receive_method()

def wssMessage(ws):
    print("received")
    breakpoint()

secret = str(os.getenv('QQ_APP_SECRET'))
bot = Bot('1905231300', secret)

bot.update_access_token()
wssTerminal = bot.getWebSocketTerminal()

server_url = wssTerminal

def on_message(ws, message):
    print(f"Received: {message}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

def on_open(ws):
    print("Connected to server")
    # Send a message once the connection is open
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

ws = websocket.WebSocketApp(
        server_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

# Run the connection perpetually with a 60-second ping interval
ws.run_forever(ping_interval=60, ping_timeout=10)

bot.listenToSocket(on_message)