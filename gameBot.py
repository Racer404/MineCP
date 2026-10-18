from typing import Callable

import time

import requests
import websocket

class Bot:
    def __init__(self, debug: bool = False):
        self.game_message_callback: Callable[[str], None] | None = None
        self.debug = debug

    def sendGameRawText(self, content:str):
        response = requests.post(
            f"http://localhost:13579/broadcast",
            data=content.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=UTF-8"},
            timeout=10,
        )
        return response

    def listenToSocket(self):
        url = "ws://localhost:13578"
        def on_open(socket):
            print("[gameBot.py] Connected to Minecraft event stream.")

        def on_message(socket, message):
            if self.game_message_callback is not None:
                self.game_message_callback(message)
            if self.debug:
                print(f"[gameBot.py] Message from socket: {message}")

        # Continuous reconnection loop
        while True:
            ws = websocket.WebSocketApp(url)
            ws.on_message = on_message
            ws.on_open = on_open

            if self.debug:
                print("[gameBot.py] Connecting to WebSocket...")

            ws.run_forever(
                ping_interval=30,
                ping_timeout=10,
            )
            # Short fallback delay before trying to reconnect to avoid spamming the gateway
            time.sleep(2)