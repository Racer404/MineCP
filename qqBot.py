from typing import Callable

import websocket
import requests
import threading
import time
import json

class Bot:
    def __init__(self, app_id:str='', client_secret:str='', debug:bool=False):
        self.app_id = app_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expiresAt = None
        self.token_safety_time_margin = 50.
        self.agreed_heartbeat_interval = 60
        self.heartbeat_payload_d = None
        self.group_at_message_callback:Callable[[str],None] | None = None
        self.group_message_callback:Callable[[str],None] | None = None
        self.debug = debug

    def update_access_token(self):
        if self.debug:
            print("[qqBot.py] Updating access token")
        time_now = time.time()
        update_need = True

        if self.access_token:
            time_remain = (self.token_expiresAt - self.token_safety_time_margin) - time_now
            if time_remain > 0:
                update_need = False

        if update_need:
            if self.debug:
                print("[qqBot.py] Fetching a new access token...")

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

    def replyGroupRawText(self, group_openid:str, content:str, msg_id:str):
        api = f"https://api.bot.qq.com/v2/groups/{group_openid}/messages"
        header = {"Authorization": "QQBot " + self.access_token}
        payload = {
            "msg_type": 0,
            "content": content,
            "msg_id" : msg_id
        }
        response = requests.post(api, headers=header, json=payload)
        return response

    def sendGroupRawText(self, group_openid:str, content:str):
        api = f"https://api.bot.qq.com/v2/groups/{group_openid}/messages"
        header = {"Authorization": "QQBot " + self.access_token}
        payload = {
            "msg_type": 0,
            "content": content
        }
        response = requests.post(api, headers=header, json=payload)
        return response

    def listenToSocket(self, url):
        def on_message(socket, message):
            op_ = json.loads(message)['op']

            if op_ == 10:
                if self.debug:
                    print("[qqBot.py] Handshake from server")
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
                if self.debug:
                    print("[qqBot.py] Handshake authentication sent")

            elif op_ == 0:
                if self.debug:
                    print("[qqBot.py] Dispatch from server")
                t_ = json.loads(message)['t']

                if t_ == 'READY':
                    if self.debug:
                        print("[qqBot.py] Handshake successfully")
                    self.heartbeat_payload_d = "null"

                elif t_ == 'GROUP_AT_MESSAGE_CREATE':
                    if self.debug:
                        print("[qqBot.py] GROUP_AT_MESSAGE_CREATE")
                    self.heartbeat_payload_d = json.loads(message)['s']
                    if self.group_at_message_callback is not None:
                        self.group_at_message_callback(message)

                elif t_ == 'GROUP_MESSAGE_CREATE':
                    if self.debug:
                        print("[qqBot.py] GROUP_MESSAGE_CREATE")
                    self.heartbeat_payload_d = json.loads(message)['s']
                    if self.group_message_callback is not None:
                        self.group_message_callback(message)
            elif op_ == 11:
                print("[qqBot.py] Pong!")

            if self.debug:
                print(f"[qqBot.py] Message from socket: {message}")

        def heartbeat(socket):
            while True:
                time.sleep(self.agreed_heartbeat_interval)

                if self.heartbeat_payload_d:
                    heartbeat_payload = {
                        "op": 1,
                        "d": self.heartbeat_payload_d
                    }
                    socket.send(json.dumps(heartbeat_payload))
                    print("[qqBot.py] Ping!")

        ws = websocket.WebSocketApp(url)
        ws.on_message = on_message

        threading.Thread(
            target=heartbeat,
            args=(ws,),
            daemon=True
        ).start()

        ws.run_forever()