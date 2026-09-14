import os

from qqBot import Bot

secret = str(os.getenv('QQ_APP_SECRET'))
bot = Bot(app_id='1905231300', client_secret=secret, debug=True)
bot.update_access_token()

bot.listenToSocket(bot.getWebSocketTerminal())
breakpoint()