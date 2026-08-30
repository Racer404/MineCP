import json
import os

from openai import OpenAI

from qqBot import Bot
from agent import Agent

client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com")

agent = Agent(client,thinking=True)
agent.setSystemPrompt("你是Minecraft服务器拉杆服务器的人工智能-一个拉杆，用户会以拉杆bot来称呼你，"
                      "你会受到一系列上下文，每个上下文都包含上下文类型，有游戏内事件(Event)，"
                      "游戏内玩家对话(Chat)，但只有收到请求(Query)时你才会被调用，"
                      "同时每个上下文也包含发送者信息，例如发送者的玩家id，请根据你对发送者的记忆，"
                      "进行个性化回复，根据上下文用一两句话简洁的回答用户的问题。"
                      "模仿银河系搭车客指南中机器人马文的说话风格，但不要过度刻薄。")
agent.setKnowledgePrompt("你知道Minecraft的所有知识，你所在的拉杆服务器版本是Java 26.2，"
                         "ip地址是mc.racer.fund(上海)，当用户从境外连接时也可以使用"
                         "hkmc.racer.fund(香港)。")

secret = str(os.getenv('QQ_APP_SECRET'))
bot = Bot('1905231300', secret)
bot.update_access_token()

def onGroupMessage(message):
    groupId = json.loads(message)['d']['group_openid']
    msgId = json.loads(message)['d']['id']
    content = json.loads(message)['d']['content']
    msgUser = json.loads(message)['d']['author']['username']

    agent.addContext(context=content, username=msgUser, contextType="Query")
    response = agent.stepPrompt()
    reply_text = str(response.choices[0].message.content)
    bot.replyGroupRawText(groupId,reply_text, msgId)

bot.group_at_message_callback = onGroupMessage
wssTerminal = bot.getWebSocketTerminal()
bot.listenToSocket(wssTerminal)