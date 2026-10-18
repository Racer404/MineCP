import requests
import json
from agent import Agent

import global_params
from qqBot import Bot as QQBot
from gameBot import Bot as GameBot

def get_player_whitelisted_status(member_name:str, base_url: str = "http://localhost:13579") -> str:
    response = requests.get(
        f"{base_url}/ifwhitelist",
        params={"name": member_name},
        timeout=5
    )
    response.raise_for_status()
    if_whitelist = response.json()["whitelisted"]
    return if_whitelist

def group_message_game(call_source: str, message: str, game_bot: GameBot|None = None, **kwargs) -> str:
    if call_source == "game":
        return "[error] calling a QQ group only function while in game"

    game_bot.sendGameRawText(message)
    return f"message forwarded"

def game_message_group(call_source: str, message: str, qq_bot: QQBot|None = None, **kwargs) -> str:
    if call_source == "group":
        return "[error] calling a game only function while in QQ group"

    qq_bot.sendGroupRawText(message)
    return f"message forwarded"

def bind_member_name(
    member_name: str,
    call_source: str,
    member_openid: str|None = None,
    json_file: str = "members.json",
    **kwargs):

    if call_source == "game":
        return "[error] calling a QQ group only function while in game"

    if not get_player_whitelisted_status(member_name):
        return f"Player {member_name} not whitelisted"

    global_params.member_mappings[member_openid] = member_name
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(global_params.member_mappings, f, ensure_ascii=False, indent=4)

    return f"added {member_name}"

def get_online_players(call_source: str, base_url: str = "http://localhost:13579", **kwargs) -> str:

    if call_source == "game":
        return "[error] calling a QQ group only function while in game"

    response = requests.get(
        f"{base_url}/onlineplayers",
        timeout=5
    )

    response.raise_for_status()
    return json.dumps(response.json())

def get_player_stats(call_source: str, member_name:str, base_url: str = "http://localhost:13579", **kwargs) -> str:
    response = requests.get(
        f"{base_url}/playerstats",
        params={"name": member_name},
        timeout=5
    )
    response.raise_for_status()
    return json.dumps(response.json())

def pat_player(call_source: str, member_name:str, base_url: str = "http://localhost:13579", **kwargs) -> str:
    response = requests.get(
        f"{base_url}/patplayer",
        params={"name": member_name},
        timeout=5
    )
    response.raise_for_status()
    return json.dumps(response.json())

def inject_tools(agent: Agent):
    agent.addTool(
        name="bind_member_name",
        description="Record or change the bind name(equivalent to the player name in the game), user should supply a name",
        function=bind_member_name,
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
        description="Query the stats of a player in game, user should supply a name",
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

    agent.addTool(
        name="group_message_game",
        description="help to forward information from QQ group to game, user should give the information needs to be forward",
        function=group_message_game,
        parameters={
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The forwarding message or information"
                }
            },
            "required": ["message"]}
    )

    agent.addTool(
        name="game_message_group",
        description="help to forward message from game to QQ group, user should give the information needs to be forward",
        function=game_message_group,
        parameters={
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The forwarding message or information"
                }
            },
            "required": ["message"]}
    )