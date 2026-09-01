import json
import os
from typing import Callable

from openai import OpenAI, Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from datetime import datetime

def get_current_time() -> str:
    """
    Returns the current local time in the format:
    YYYY-MM-DD-HH-MM
    Example: 2026-07-30-17-07
    """
    return datetime.now().strftime("%Y-%m-%d-%H-%M")

class Agent:
    def __init__(
            self,
            client_secret:str,
            model:str = "deepseek-v4-flash",
            stream:bool = False,
            reasoning_effort:str = "high",
            thinking:bool = False,
            debug:bool = False
    ):
        extra_body = {"thinking": {"type": "disabled"}}
        if thinking:
            extra_body = {"thinking": {"type": "enabled"}}

        client = OpenAI(
            api_key=client_secret,
            base_url="https://api.deepseek.com")

        self.client = client
        self.model = model
        self.stream = stream
        self.reasoning_effort = reasoning_effort
        self.extra_body = extra_body
        self.debug = debug

        self.sysPrompt = None
        self.knlgPrompt = None
        self.memPrompt = None
        self.context:list = []

        self.contex_length_before_compress = 1000
        self.word_length_before_reply = 100
        self.__word_length_now = 0
        self.maxMemWords = 200


    def setSystemPrompt(self, sysPrompt:str):
        defineSystem = "#This is a persistent instruction that establishes the your role as an assistant, behavioral rules, operational constraints, and response style. Taking precedence over user prompts whenever conflicts arise. Instructions as follows: "
        prompt = dict()
        prompt["role"] = "system"
        prompt["content"] = defineSystem + sysPrompt
        self.sysPrompt = prompt

    def setKnowledgePrompt(self, knlgPrompt:str):
        defineKnowledge = "#This is a knowledge prompt, a supplemental information provided to a language model to supply domain-specific facts or reference material that the model should use when answering a user's request. Knowledge as follows: "
        prompt = dict()
        prompt["role"] = "system"
        prompt["content"] = defineKnowledge + knlgPrompt
        self.knlgPrompt = prompt

    def setMemoryPrompt(self, memPrompt:str):
        defineMemory = "#A memory prompt is contextual information supplied to a language model that represents persistent knowledge about a specific user, project, or ongoing interaction. Its purpose is to enable continuity and personalization across conversations without changing the model's fundamental behavior. Your memory as follows: "
        prompt = dict()
        prompt["role"] = "system"
        prompt["content"] = defineMemory + memPrompt
        self.memPrompt = prompt

    def addContext(
            self,
            message: str,
            username: str = "Unknown",
            contextType: str = "Unknown"
    ):
        prompt = {
            "role": "user",
            "content": (
                f"Timestamp: {get_current_time()}, "
                f"Context Type: {contextType}, "
                f"Sender: {username}, "
                f"Message: {message}"
            )
        }

        if username:
            prompt["name"] = username
        self.context.append(prompt)


    def stepPrompt(self) -> ChatCompletion | Stream[ChatCompletionChunk]:
        final_prompt = []
        if self.sysPrompt:
            final_prompt.append(self.sysPrompt)
        if self.knlgPrompt:
            final_prompt.append(self.knlgPrompt)
        if self.memPrompt:
            final_prompt.append(self.memPrompt)
        final_prompt += self.context

        if self.debug:
            print(f"[agent.py]Sending Prompt: {final_prompt}")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=final_prompt,
            stream=self.stream,
            extra_body=self.extra_body
        )

        if self.debug:
            print(f"[agent.py]Receiving Completion: {response}")

        assistantRecalls = json.loads(response.choices[0].message.model_dump_json())
        self.context.append(assistantRecalls)

        # if response.usage.prompt_cache_miss_tokens > self.contex_length_before_compress:
        #     self.compressContext()

        return response

    def compressContext(self):
        final_prompt = []
        defineSummarize = f"You are maintaining the long-term memory of an AI assistant for a Minecraft server; summarize the conversation into persistent memory, keeping only information useful for future conversations, including user preferences, player identities, important decisions, long-term goals, server-specific facts, and ongoing projects; remove temporary dialogue, casual chat, greetings, small talk, one-time questions, temporary game events, and repeated information; merge duplicates; when memory conflicts with newer information, keep the newer information; output only the concise summarized memory, no longer than {self.maxMemWords} words."
        sysPrompt = dict()
        sysPrompt["role"] = "system"
        sysPrompt["content"] = defineSummarize

        final_prompt.append(sysPrompt)

        if self.memPrompt:
            final_prompt.append(self.memPrompt)

        final_prompt += self.context

        response = self.client.chat.completions.create(
            model=self.model,
            messages=final_prompt,
            stream=self.stream,
            extra_body=self.extra_body
        )
        newMem = str(response.choices[0].message.content)
        self.setMemoryPrompt(newMem)
        self.context: list = []

        if self.debug:
            print("[agent.py]Compressing Context into memory...")
            print(f"[agent.py]New memory:{newMem}")