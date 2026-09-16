import os
import json
import requests

from agent import Agent

def get_player_stats(member_name:str, base_url: str = "http://localhost:13579", **kwargs) -> str:
    response = requests.get(
        f"{base_url}/playerstats",
        params={"name": member_name},
        timeout=5
    )

    response.raise_for_status()
    return json.dumps(response.json())

breakpoint()