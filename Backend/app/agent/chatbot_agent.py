import os
from typing import TypedDict, List, Dict, Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]


class ChatbotAgent:
    def __init__(self, model: str = "gemini-2.5-flash", temperature: float = 0.7, max_output_tokens: int = 2500):
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        self.graph = self.build_graph()

    def build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("llm", self.call_llm)
        workflow.add_edge(START, "llm")
        workflow.add_edge("llm", END)
        return workflow.compile()

    async def call_llm(self, state: AgentState) -> Dict[str, List[BaseMessage]]:
        response = await self.llm.ainvoke(state["messages"])
        return {"messages": [response]}

    # converts {"role": "user","content": "Hi"} to langcain message format => HumanMessage(content="Hi")
    @staticmethod
    def to_lc_messages(message: str, chat_history: List[Dict[str, str]] = None) -> List[BaseMessage]:
        if chat_history is None:
            chat_history = []

        messages: List[BaseMessage] = []
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=message))
        return messages

     
    async def invoke(self, message: str, chat_history: List[Dict[str, str]] = None) -> str:
        lc_messages = self.to_lc_messages(message, chat_history)
        result = await self.graph.ainvoke({"messages": lc_messages})
        last_message = result["messages"][-1]
        return last_message.content
