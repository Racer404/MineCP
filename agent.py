import os

from openai import OpenAI
from openai.types.chat import ChatCompletion

from datetime import datetime

def get_current_time() -> str:
    """
    Returns the current local time in the format:
    YYYY-MM-DD-HH-MM
    Example: 2026-07-30-17-07
    """
    return datetime.now().strftime("%Y-%m-%d-%H-%M")

class Agent:
    def __init__(self, client:OpenAI = None, model:str = "deepseek-v4-flash", stream:bool=False, reasoning_effort:str = "high",
                 extra_body=None):
        if extra_body is None:
            extra_body = {"thinking": {"type": "disabled"}}

        self.client = client
        self.model = model
        self.stream = stream
        self.reasoning_effort = reasoning_effort
        self.extra_body = extra_body

        self.sysPrompt = None
        self.knlgPrompt = None
        self.memPrompt = None
        self.context:list = []

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

    def addContext(self, context:str, role:str = "user", username:str = "Unknown", contextType:str = "Unknown", timestamp:str = "Unknown"):
        defineType = "Context Type: "
        defineUser = "Sender: "
        defineTime = "Timestamp: "
        prompt = dict()
        prompt["role"] = role
        if username:
            prompt["name"] = username
        prompt["content"] = (defineType + contextType + ", " +
                             defineUser + username +", " +
                             defineTime + timestamp + ", " +
                             context)
        self.context.append(prompt)

    def recordResponse(self, response:ChatCompletion, timestamp:str = "Unknown"):
        defineTime = "Timestamp: "
        prompt = dict()
        prompt["role"] = "assistant"
        prompt["content"] = defineTime + timestamp + ", " + response.choices[0].message.content
        self.context.append(prompt)

    def updateMem(self, maxWords:int=500):
        finalMessage = []
        defineSummarize = f"You are maintaining the long-term memory of an AI assistant for a Minecraft server; summarize the conversation into persistent memory, keeping only information useful for future conversations, including user preferences, player identities, important decisions, long-term goals, server-specific facts, and ongoing projects; remove temporary dialogue, casual chat, greetings, small talk, one-time questions, temporary game events, and repeated information; merge duplicates; when memory conflicts with newer information, keep the newer information; output only the concise summarized memory, no longer than {maxWords} words."
        sysPrompt = dict()
        sysPrompt["role"] = "system"
        sysPrompt["content"] = defineSummarize

        finalMessage.append(sysPrompt)

        if self.memPrompt:
            finalMessage.append(self.memPrompt)

        finalMessage += self.context

        response = self.client.chat.completions.create(
            model=self.model,
            messages=finalMessage,
            stream=self.stream,
            extra_body=self.extra_body
        )
        newMem = str(response.choices[0].message.content)
        self.setMemoryPrompt(newMem)
        breakpoint()

    def chatSend(self) -> ChatCompletion:
        finalMessage = []
        if self.sysPrompt:
            finalMessage.append(self.sysPrompt)
        if self.knlgPrompt:
            finalMessage.append(self.knlgPrompt)
        if self.memPrompt:
            finalMessage.append(self.memPrompt)
        finalMessage += self.context

        response = self.client.chat.completions.create(
            model=self.model,
            messages=finalMessage,
            stream=self.stream,
            extra_body=self.extra_body
        )

        self.recordResponse(response)
        return response


client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com")

agent = Agent(client)
agent.setSystemPrompt("你是Minecraft服务器拉杆服务器的人工智能-一个拉杆，用户会以拉杆来称呼你，"
                      "你会受到一系列上下文，每个上下文都包含上下文类型，有游戏内事件(Event)，"
                      "游戏内玩家对话(Chat)，但只有收到请求(Query)时你才会被调用，"
                      "同时每个上下文也包含发送者信息，例如发送者的玩家id，请根据你对发送者的记忆，"
                      "进行个性化回复，根据上下文用一两句话简洁的回答用户的问题，保持友善的风格。")
agent.setKnowledgePrompt("你知道Minecraft的所有知识，你所在的拉杆服务器版本是Java 26.2，"
                         "ip地址是mc.racer.fund(上海)，当用户从境外连接时也可以使用"
                         "hkmc.racer.fund(香港)。")

agent.addContext("你是谁")
agent.addContext("Steve was drown", username="Steve", contextType="Event")
agent.chatSend()

agent.updateMem(100)

breakpoint()