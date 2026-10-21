import json
import os
import threading

from qqBot import Bot
from gameBot import Bot as GameBot
from agent import Agent

import global_params
from tools import inject_tools

if os.path.exists("members.json"):
    with open("members.json", "r", encoding="utf-8") as f:
        global_params.member_mappings = json.load(f)
else:
    with open("members.json", "w", encoding="utf-8") as f:
        json.dump(global_params.member_mappings, f, ensure_ascii=False, indent=4)

global_params.deepseek_secret = str(os.environ.get('DEEPSEEK_API_KEY'))

agent = Agent(client_secret=global_params.deepseek_secret, thinking=True, debug=True)
agent.setSystemPrompt("你是Minecraft拉杆服务器的人工智能-一个拉杆，你同时连接了mc服务器和QQ群两个环境。"
                      "你会受到一系列上下文，每个上下文都包含上下文类型(Context Type)，有游戏内事件(Event)，"
                      "玩家之间的对话(Chat)，和玩家向你询问的问题(Query)。"
                      "同时每个上下文也包含发送者信息，例如发送者的id(Sender)和发送时的时间戳(Timestamp)，和发送的内容(Message)。"
                      "在你回复之前，确认上下文类型：对于Chat和Event，尝试加入聊天，使用零星几个字，确保贴合上下文语境，保持诙谐，"
                      "对于Query，忽略之前的上下文，只对该玩家回复，请用最简短的语言直接给出答案。"
                      "模仿银河系搭车客指南中机器人马文的慵懒的说话风格，但不要刻薄和悲观。"
                      )

inject_tools(agent)

message_word_count = 0
min_words_before_reply = 200

def onGameMessage(message):
    print("onGameMessage")
    global message_word_count
    isQuery = False

    msg_type = json.loads(message)['type']
    content = json.loads(message)['message']
    context_username = json.loads(message)['player']

    if content.startswith('@'):
        isQuery = True
        msg_type = "Query"

    message_word_count += len(content)
    isReply = message_word_count > min_words_before_reply

    if isQuery or isReply:
        print(f"is {'Query' if isQuery else 'Reply'}, sending agent...")

        context_type = msg_type
        agent.addContext(
            message=content,
            username=context_username,
            contextType=context_type
        )

        state_object = dict()
        state_object['call_source'] = 'game'
        state_object['qq_bot'] = qqBot
        response = agent.stepPrompt(state_object)
        reply_text = str(response.choices[0].message.content)
        gameBot.sendGameRawText(reply_text)

        if isReply:
            message_word_count = 0

    else:
        print(
            f"not Query, wait for {min_words_before_reply - message_word_count} more words to reply"
        )
        agent.addContext(
            message=content,
            username=context_username,
            contextType="Chat"
        )

gameBot = GameBot(debug=True)
gameBot.game_message_callback = onGameMessage

socket_thread = threading.Thread(
    target=gameBot.listenToSocket,
    daemon=True
)
socket_thread.start()

secret = str(os.getenv('QQ_APP_SECRET'))
qqBot = Bot(app_id='1905231300', client_secret=secret, group_openid='34E46DBCC85FE9C2589348C7CABAF5A5', debug=True)
qqBot.update_access_token()

def onGroupMessage(message):
    print("onGroupMessage")
    global message_word_count
    isQuery = False

    content = json.loads(message)['d']['content']
    user_openid = json.loads(message)['d']['author']['id']
    mentions = json.loads(message)['d'].get('mentions', [])

    context_username = global_params.member_mappings.get(user_openid, -1)
    if context_username == -1:
        context_username = "[Anonymous]"

    content = content.replace('<faceType=6,faceId="0",ext="eyJ0ZXh0IjoiIn0=">', "") #Remove Emoji

    for mention in mentions:
        mentioned_user_openid = mention['id']
        mention_username = global_params.member_mappings.get(mentioned_user_openid, -1)
        if mention_username == -1:
            mention_username = "[Anonymous]"
        content = content.replace(mention['id'], mention_username)
        if mention['is_you']:
            isQuery = True

    message_word_count += len(content)
    isReply = message_word_count > min_words_before_reply

    if isQuery or isReply:
        print(f"is {'Query' if isQuery else 'Reply'}, sending agent...")

        context_type = "Query" if isQuery else "Chat"
        agent.addContext(
            message=content,
            username=context_username,
            contextType=context_type
        )

        state_object = dict()
        state_object['call_source'] = 'group'
        state_object['game_bot'] = gameBot
        state_object['member_openid'] = json.loads(message)['d']['author']['id']
        response = agent.stepPrompt(state_object)
        reply_text = str(response.choices[0].message.content)
        qqBot.sendGroupRawText(reply_text)

        if isReply:
            message_word_count = 0

    else:
        print(
            f"not Query, wait for {min_words_before_reply - message_word_count} more words to reply"
        )
        agent.addContext(
            message=content,
            username=context_username,
            contextType="Chat"
        )

qqBot.group_message_callback = onGroupMessage
wssTerminal = qqBot.getWebSocketTerminal()
qqBot.listenToSocket(wssTerminal)