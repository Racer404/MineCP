import requests
import json
from agent import Agent

import global_params

def get_player_whitelisted_status(member_name:str, base_url: str = "http://localhost:13579") -> str:
    response = requests.get(
        f"{base_url}/ifwhitelist",
        params={"name": member_name},
        timeout=5
    )
    response.raise_for_status()
    if_whitelist = response.json()["whitelisted"]
    return if_whitelist

def set_member_name(
    member_name: str,
    member_openid: str,
    json_file: str = "members.json",
    **kwargs):

    if not get_player_whitelisted_status(member_name):
        return f"Player {member_name} not whitelisted"

    global_params.member_mappings[member_openid] = member_name
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(global_params.member_mappings, f, ensure_ascii=False, indent=4)

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

def inject_tools(agent: Agent):
    agent.addTool(
        name="set_member_name",
        description="Record or change the name(equivalent to the player name in the game), user should supply a name",
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