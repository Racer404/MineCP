import json
import os

from qqBot import Bot
from agent import Agent

deepseek_secret = str(os.environ.get('DEEPSEEK_API_KEY'))
agent = Agent(client_secret=deepseek_secret,thinking=True)
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
bot = Bot(app_id='1905231300', client_secret=secret)
bot.update_access_token()

def onGroupAtMessage(message):
    groupId = json.loads(message)['d']['group_openid']
    msgId = json.loads(message)['d']['id']
    content = json.loads(message)['d']['content']
    msgUser = json.loads(message)['d']['author']['username']

    agent.addContext(message=content, username=msgUser, contextType="Query")
    response = agent.stepPrompt()
    reply_text = str(response.choices[0].message.content)
    bot.replyGroupRawText(groupId,reply_text, msgId)

def onGroupMessage(message):
    groupId = json.loads(message)['d']['group_openid']
    content = json.loads(message)['d']['content']
    msgUser = json.loads(message)['d']['author']['username']

    agent.addContext(message=content, username=msgUser, contextType="Chat")

def onAgentReply(response):
    reply_text = str(response.choices[0].message.content)
    bot.sendGroupRawText('34E46DBCC85FE9C2589348C7CABAF5A5', reply_text)

# bot.group_at_message_callback = onGroupAtMessage
bot.group_message_callback = onGroupMessage
agent.trigger_reply_callback = onAgentReply

wssTerminal = bot.getWebSocketTerminal()
bot.listenToSocket(wssTerminal)