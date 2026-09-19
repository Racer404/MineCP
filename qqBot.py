from typing import Callable

import websocket
import requests
import threading
import time
import json

class Bot:
    def __init__(self, app_id:str='', client_secret:str='', debug:bool=False):
        self.require_reconnect = False
        self.app_id = app_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expiresAt = None
        self.token_safety_time_margin = 50.
        self.agreed_heartbeat_interval = 60
        self.current_message_sequence = None
        self.socket_session_id = None
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
        self.update_access_token()
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
            data = json.loads(message)
            op_ = data.get('op')

            # CRITICAL: Always update the sequence number for ALL OpCode 0 events
            if op_ == 0:
                if "s" in data and data["s"] is not None:
                    self.current_message_sequence = data["s"]

                if self.debug:
                    print("[qqBot.py] Dispatch from server")
                t_ = data.get('t')

                if t_ == 'READY':
                    self.socket_session_id = data["d"]["session_id"]
                    if self.debug:
                        print(f"[qqBot.py] Handshake successfully, session id = {self.socket_session_id}")

                elif t_ == 'GROUP_AT_MESSAGE_CREATE':
                    if self.debug:
                        print("[qqBot.py] GROUP_AT_MESSAGE_CREATE")
                    if self.group_at_message_callback is not None:
                        self.group_at_message_callback(message)

                elif t_ == 'GROUP_MESSAGE_CREATE':
                    if self.debug:
                        print("[qqBot.py] GROUP_MESSAGE_CREATE")
                    if self.group_message_callback is not None:
                        self.group_message_callback(message)

            elif op_ == 10:
                if self.debug:
                    print("[qqBot.py] Handshake request from server")
                self.agreed_heartbeat_interval = int(data['d']['heartbeat_interval'] / 1000)

                # Check if we should RESUME or IDENTIFY
                if self.require_reconnect and hasattr(self, 'socket_session_id'):
                    if self.debug:
                        print("[qqBot.py] Sending Resume payload (OpCode 6)...")
                    self.update_access_token()
                    payload = {
                        "op": 6,
                        "d": {
                            "token": f"QQBot {self.access_token}",
                            "session_id": self.socket_session_id,
                            "seq": self.current_message_sequence
                        }
                    }
                    self.require_reconnect = False  # Reset flag after resuming
                else:
                    if self.debug:
                        print("[qqBot.py] Sending Identify payload (OpCode 2)...")
                    self.current_message_sequence = None  # Initialize properly as None, not "null"
                    payload = {
                        "op": 2,
                        "d": {
                            "token": f"QQBot {self.access_token}",
                            "intents": 33554432,
                            "shard": [0, 1]
                        }
                    }
                socket.send(json.dumps(payload))

            elif op_ == 11:
                if self.debug:
                    print("[qqBot.py] Pong!")

            elif op_ == 7:
                if self.debug:
                    print("[qqBot.py] Server request reconnect. Closing connection to trigger resume...")
                self.require_reconnect = True
                socket.close()  # This breaks ws.run_forever() and starts the reconnect loop

            if self.debug:
                print(f"[qqBot.py] Message from socket: {message}")

        def heartbeat(socket):
            while True:
                # Use a default fallback if interval isn't set yet
                interval = getattr(self, 'agreed_heartbeat_interval', 30)
                time.sleep(interval)

                # Send heartbeat with current sequence (can be None)
                heartbeat_payload = {
                    "op": 1,
                    "d": getattr(self, 'current_message_sequence', None)
                }
                try:
                    socket.send(json.dumps(heartbeat_payload))
                    if self.debug:
                        print("[qqBot.py] Ping!")
                except Exception:
                    break  # Exit thread cleanly if socket is dead

        # Continuous reconnection loop
        while True:
            ws = websocket.WebSocketApp(url)
            ws.on_message = on_message

            threading.Thread(
                target=heartbeat,
                args=(ws,),
                daemon=True
            ).start()

            if self.debug:
                print("[qqBot.py] Connecting to WebSocket...")
            ws.run_forever()

            # Short fallback delay before trying to reconnect to avoid spamming the gateway
            time.sleep(2)