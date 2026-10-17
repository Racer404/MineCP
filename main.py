import json
import os
from qqBot import Bot
from agent import Agent

import global_params
from tools import inject_tools

if os.path.exists("members.json"):
    with open("members.json", "r", encoding="utf-8") as f:
        global_params.member_mappings = json.load(f)
else:
    with open("members.json", "w", encoding="utf-8") as f:
        json.dump(global_params.member_mappings, f, ensure_ascii=False, indent=4)

def build_state_object(message):
    stateObject = dict()
    stateObject['member_openid'] = json.loads(message)['d']['author']['id']

    return stateObject


deepseek_secret = str(os.environ.get('DEEPSEEK_API_KEY'))
agent = Agent(client_secret=deepseek_secret, thinking=True, debug=True)
agent.setSystemPrompt("你是Minecraft服务器拉杆服务器的人工智能-一个拉杆，用户会以拉杆bot来称呼你，"
                      "你会受到一系列上下文，每个上下文都包含上下文类型(Context Type)，有游戏内事件(Event)，"
                      "玩家之间的对话(Chat)，和玩家向你询问的问题(Query)。"
                      "同时每个上下文也包含发送者信息，例如发送者的id(Sender)和发送时的时间戳(Timestamp)，和发送的内容(Message)。"
                      "在你回复之前，确认上下文类型：对于Chat和Event，尝试加入聊天，使用零星几个字，确保贴合上下文语境，保持诙谐，"
                      "对于Query，只需要对该玩家回复，请用最简短的语言直接给出答案。"
                      "模仿银河系搭车客指南中机器人马文的慵懒的说话风格，但不要刻薄和悲观。"
                      )

inject_tools(agent)

secret = str(os.getenv('QQ_APP_SECRET'))
bot = Bot(app_id='1905231300', client_secret=secret, debug=True)
bot.update_access_token()

message_word_count = 0
min_words_before_reply = 200

def onGroupMessage(message):
    print("onGroupMessage")

    global message_word_count
    isQuery = False

    groupId = json.loads(message)['d']['group_openid']
    content = json.loads(message)['d']['content']
    msg_username = json.loads(message)['d']['author']['username']
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

    if isQuery:
        print("is Query, sending agent...")
        agent.addContext(message=content, username=context_username, contextType="Query")
        response = agent.stepPrompt(build_state_object(message))
        reply_text = str(response.choices[0].message.content)
        bot.sendGroupRawText(groupId, reply_text)
    elif isReply:
        print("is Reply, sending agent...")
        agent.addContext(message=content, username=context_username, contextType="Chat")
        response = agent.stepPrompt(build_state_object(message))
        reply_text = str(response.choices[0].message.content)
        bot.sendGroupRawText(groupId, reply_text)
        message_word_count = 0
    else:
        print(f"not Query, wait for {min_words_before_reply-message_word_count} more words to reply")
        agent.addContext(message=content, username=context_username, contextType="Chat")

bot.group_message_callback = onGroupMessage

wssTerminal = bot.getWebSocketTerminal()
bot.listenToSocket(wssTerminal)