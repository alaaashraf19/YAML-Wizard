import os
from typing import TypedDict, List, Dict, Annotated, Optional, Any
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from agent.tools import TOOLS
from agent.prompts import SYSTEM_PROMPT



class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]


class ChatbotAgent:
    def __init__(self, model: str = "gemini-2.5-flash", temperature: float = 0.3,
        max_output_tokens: int = 2500, tools: Optional[list] = None,
        system_prompt: Optional[str] = SYSTEM_PROMPT,):
        
        self.tools = TOOLS
        self.system_prompt = system_prompt

        base_llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        
        self.llm = base_llm.bind_tools(self.tools) if self.tools else base_llm
        self.graph = self.build_graph()

    def build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("llm", self.call_llm)
        workflow.add_node("tools", ToolNode(self.tools))

        workflow.add_edge(START, "llm")
        workflow.add_conditional_edges("llm", tools_condition,{
            "tools": "tools", END: END
            },
        )
        workflow.add_edge("tools", "llm")
        return workflow.compile()

    async def call_llm(self, state: AgentState) -> Dict[str, List[BaseMessage]]:
        messages = state["messages"]
        if self.system_prompt:
            messages = [SystemMessage(content=self.system_prompt)] + list(messages)
        response = await self.llm.ainvoke(messages)
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

     
    async def invoke(self, message: str, chat_history: List[Dict[str, str]] = None, db: Optional[Any] = None, gitlab_connection: Optional[Any] = None) -> str:
        lc_messages = self.to_lc_messages(message, chat_history)
        
        #langchain uses the db (the active session) and gitlab_connection in the validation tool
        #since it sends the yaml and determines the platform, it can't determine the connection token and the llm can't produce them
        #so we send these parameters into a runnable config that propagates along the graph and is not part of the prompt (hidden from the llm and ready to use not waiting to be filled)
        #so we are delivering request‑scoped runtime data to a tool without involving the model.
        config = {"configurable": {"db": db, "gitlab_connection": gitlab_connection}}
        
        result = await self.graph.ainvoke({"messages": lc_messages}, config=config)
        last_message = result["messages"][-1]
        return last_message.content
