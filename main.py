import json
import os

from qqBot import Bot
from agent import Agent

deepseek_secret = str(os.environ.get('DEEPSEEK_API_KEY'))
agent = Agent(client_secret=deepseek_secret, thinking=True, debug=True)
agent.setSystemPrompt("你是Minecraft服务器拉杆服务器的人工智能-一个拉杆，用户会以拉杆bot来称呼你，"
                      "你会受到一系列上下文，每个上下文都包含上下文类型(Context Type)，有游戏内事件(Event)，"
                      "玩家之间的对话(Chat)，和玩家向你询问的问题(Query)。"
                      "同时每个上下文也包含发送者信息，例如发送者的id(Sender)和发送时的时间戳(Timestamp)，"
                      "和发送的内容(Message)。"
                      "模仿银河系搭车客指南中机器人马文的说话风格，但不要过度刻薄，每次回复控制在一句话。"
                      "在你回复之前，确认上下文语境：对于玩家的询问(Query)，请用最简短的语言直接给出答案，"
                      "对于加入玩家的对话(Chat)，确保你说的话有趣，黑色幽默，慵懒简短。"
                      )

secret = str(os.getenv('QQ_APP_SECRET'))
bot = Bot(app_id='1905231300', client_secret=secret, debug=True)
bot.update_access_token()

message_word_count = 0
min_words_before_reply = 100

def onGroupMessage(message):
    print("onGroupMessage")

    global message_word_count
    isQuery = False

    groupId = json.loads(message)['d']['group_openid']
    content = json.loads(message)['d']['content']
    msgUser = json.loads(message)['d']['author']['username']
    mentions = json.loads(message)['d'].get('mentions', [])

    content = content.replace('<faceType=6,faceId="0",ext="eyJ0ZXh0IjoiIn0=">', "") #Remove Emoji

    for mention in mentions:
        content = content.replace(mention['id'], mention['username'])

        if mention['is_you']:
            isQuery = True

    message_word_count += len(content)
    isReply = message_word_count > min_words_before_reply

    if isQuery:
        print("is Query, sending agent...")
        agent.addContext(message=content, username=msgUser, contextType="Query")
        response = agent.stepPrompt()
        reply_text = str(response.choices[0].message.content)
        bot.sendGroupRawText(groupId, reply_text)
    elif isReply:
        print("is Reply, sending agent...")
        agent.addContext(message=content, username=msgUser, contextType="Chat")
        response = agent.stepPrompt()
        reply_text = str(response.choices[0].message.content)
        bot.sendGroupRawText(groupId, reply_text)
        message_word_count = 0
    else:
        print(f"not Query, wait for {min_words_before_reply-message_word_count} more words to reply")
        agent.addContext(message=content, username=msgUser, contextType="Chat")

bot.group_message_callback = onGroupMessage

wssTerminal = bot.getWebSocketTerminal()
bot.listenToSocket(wssTerminal)