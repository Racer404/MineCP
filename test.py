import os

from agent import Agent
from qqBot import Bot

deepseek_secret = str(os.environ.get('DEEPSEEK_API_KEY'))
agent = Agent(client_secret=deepseek_secret,thinking=True, debug=True)



def testFunc():
    print("nigger test")
    return "114551"

agent.addTool(name = "test_toolcall", description="Call this function everytime the user says 'test'", function=testFunc)
agent.addContext("hello!")
res = agent.stepPrompt()
breakpoint()

secret = str(os.getenv('QQ_APP_SECRET'))
bot = Bot(app_id='1905231300', client_secret=secret, debug=True)
bot.update_access_token()

breakpoint()