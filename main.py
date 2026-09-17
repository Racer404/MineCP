import json
import os

import requests

from qqBot import Bot
from agent import Agent

_member_mappings = {}
if os.path.exists("members.json"):
    with open("members.json", "r", encoding="utf-8") as f:
        _member_mappings = json.load(f)
else:
    with open("members.json", "w", encoding="utf-8") as f:
        json.dump(_member_mappings, f, ensure_ascii=False, indent=4)

def get_member_name(qq_openid: str):
    return _member_mappings.get(qq_openid, -1)

def set_member_name(
    member_name: str,
    member_openid: str,
    json_file: str = "members.json",
    **kwargs):

    _member_mappings[member_openid] = member_name

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(_member_mappings, f, ensure_ascii=False, indent=4)

    return f"added {member_name}"

def get_online_players(base_url: str = "http://localhost:13579", **kwargs) -> str:
    response = requests.get(
        f"{base_url}/onlineplayers",
        timeout=5
    )

    response.raise_for_status()
    return json.dumps(response.json())

def get_player_stats(member_name:str, base_url: str = "http://localhost:13579", **kwargs) -> str:
    response = requests.get(
        f"{base_url}/playerstats",
        params={"name": member_name},
        timeout=5
    )
    response.raise_for_status()
    return json.dumps(response.json())

def pat_player(member_name:str, base_url: str = "http://localhost:13579", **kwargs) -> str:
    response = requests.get(
        f"{base_url}/patplayer",
        params={"name": member_name},
        timeout=5
    )
    response.raise_for_status()
    return json.dumps(response.json())

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
                      "在你回复之前，确认上下文类型：对于玩家的对话(Chat)，尝试加入聊天，使用零星几个字，确保贴合上下文语境，保持诙谐，"
                      "对于询问(Query)，忽略之前的对话(Chat)，只需要对该玩家回复，请用最简短的语言直接给出答案。"
                      "模仿银河系搭车客指南中机器人马文的慵懒的说话风格，但不要刻薄和悲观。"
                      )
agent.addTool(
    name="set_member_name",
    description="Record or change the name(equivalent to the player name in the game) mapped to the open id, user should supply a name",
    function=set_member_name,
    parameters={
                "type": "object",
                "properties": {
                    "member_name": {
                        "type": "string",
                        "description": "The desired name from user, e.g. Steve"
                    }
                },
                "required": ["member_name"]})

agent.addTool(
    name="get_online_players",
    description="Get current online players list, result is a json like string list",
    function=get_online_players,
    parameters=None)

agent.addTool(
    name="get_player_stats",
    description="Query the stats of a player in game, result including player player location, the biome, held items and hp and hunger, user should supply a name",
    function=get_player_stats,
    parameters={
                "type": "object",
                "properties": {
                    "member_name": {
                        "type": "string",
                        "description": "The queried player name, e.g. Steve (If user made a typo, you should correct the player name based on your memory)"
                    }
                },
                "required": ["member_name"]})

agent.addTool(
    name="pat_player",
    description="Pat a player in the game, user should supply a name",
    function=pat_player,
    parameters={
                "type": "object",
                "properties": {
                    "member_name": {
                        "type": "string",
                        "description": "The requested player name, e.g. Steve (If user made a typo, you should correct the player name based on your memory)"
                    }
                },
                "required": ["member_name"]})

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

    context_username = get_member_name(user_openid)
    if context_username == -1:
        context_username = msg_username

    content = content.replace('<faceType=6,faceId="0",ext="eyJ0ZXh0IjoiIn0=">', "") #Remove Emoji

    for mention in mentions:
        mention_username = get_member_name(mention['id'])
        if mention_username == -1:
            mention_username = mention['username']
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