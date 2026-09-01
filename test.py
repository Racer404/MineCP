import os

from agent import Agent

deepseek_secret = str(os.environ.get('DEEPSEEK_API_KEY'))
agent = Agent(client_secret=deepseek_secret,thinking=True, debug=True)

agent.addContext("Hello")
breakpoint()