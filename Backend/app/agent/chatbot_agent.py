import os
from typing import TypedDict, List, Dict, Annotated, Optional, Any
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_openai import ChatOpenAI 

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from agent.tools import TOOLS
from agent.prompts import SYSTEM_PROMPT
from agent.utils.context_resolver import ContextResolverResponse
from schemas.context_package import ContextPackage
import logging

# logging.basicConfig(level=logging.DEBUG)

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    context: Optional[Any] # full ContextResolverResponse
    context_summary: Optional[str]  # str


class ChatbotAgent:
    def __init__(self, 
                 model :str = "models/gemini-2.5-flash",
                #  model: str = "Qwen/Qwen2.5-72B-Instruct-AWQ", 
                 temperature: float = 0.3,
        max_output_tokens: int = 2500, tools: Optional[list] = None,
        system_prompt: Optional[str] = SYSTEM_PROMPT, ):
        
        self.tools = TOOLS
        self.system_prompt = system_prompt
        base_llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        # base_llm = ChatOpenAI(####################check if we will add max output tokens############################
        #     model=model,
        #     openai_api_key="token-not-needed", # vLLM doesn't require a key usually
        #     openai_api_base="http://localhost:8001/v1",
        #     temperature=temperature,
        #     max_retries=2,
        #     # Matches your 300s timeout from the test script
        #     timeout=300, 
        # )
        self.llm = base_llm.bind_tools(self.tools) if self.tools else base_llm
        #print("\n========== LLM CREATED ==========")
        #print(self.llm)
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
        messages = list(state["messages"])          # work on a copy
        
        # Inject context once as a system message (only on first turn)
        if state.get("context_summary"):
                already_injected = any(
                    "PROJECT_CONTEXT" in getattr(m, "content", "")
                    for m in messages if isinstance(m, SystemMessage)
                )
                if not already_injected:
                    context_msg = SystemMessage(
                        content=f"PROJECT_CONTEXT:\n{state['context_summary']}"
                    )
                    messages = [context_msg] + messages


    # Ensure system prompt exists
        if self.system_prompt and not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=self.system_prompt)] + messages
            
        print("\n================ MESSAGES SENT TO MODEL ================")
        for m in messages:
            print(f"Role: {type(m).__name__}")
            print(f"Content: {m.content}")
            print("-" * 30)
        
        # 2. CALL THE LLM WITH THE FULL MESSAGE LIST (NOT HARDCODED)
        response = await self.llm.ainvoke(messages)

        print("\n================ MODEL RESPONSE ================")
        print(f"Content: {response.content}")
        print(f"Tool Calls: {response.tool_calls}")
        print("================================================\n")

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

     
    async def invoke(self, message: str, session_id: int, context: ContextResolverResponse | None, 
                     context_summary :str | None, chat_history: List[Dict[str, str]] = None, db: Optional[Any] = None, 
                     gitlab_connection: Optional[Any] = None, user_id: Optional[int] = None, project_id: Optional[int] = None,
                     gitlab_project_id: Optional[Any] = None) -> str:
        lc_messages = self.to_lc_messages(message, chat_history)
        
        #langchain uses the db (the active session), gitlab_connection and gitlab_project_id in the validation tool
        #since it sends the yaml and determines the platform, it can't determine the connection token and the llm can't produce them
        #so we send these parameters into a runnable config that propagates along the graph and is not part of the prompt (hidden from the llm and ready to use not waiting to be filled)
        #so we are delivering request‑scoped runtime data to a tool without involving the model.
        config = {"configurable": 
                  {
                    "db": db, 
                    "gitlab_connection": gitlab_connection,
                    "gitlab_project_id": gitlab_project_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "project_id": project_id,
                    "context": context, #full object only for tools
                    "context_summary" : context_summary # str for LLM + tools
                   }
                }
        
        initial_state = {
        "messages": lc_messages,
        "context": context,
        "context_summary": context_summary,
        }
        result = await self.graph.ainvoke(initial_state, config=config)
        last_message = result["messages"][-1]
        return last_message.text