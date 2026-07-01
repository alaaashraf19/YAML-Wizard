import os
from typing import TypedDict, List, Dict, Annotated, Optional, Any
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_openai import ChatOpenAI 
# from langchain_groq import ChatGroq

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage, ToolMessage
from agent.tools import TOOLS
from agent.prompts import SYSTEM_PROMPT
from agent.utils.context_resolver import ContextResolverResponse
from schemas.context_package import ContextPackage
from models.pipeline_model import Pipeline
from sqlalchemy import select
import logging
import json
import re
# logging.basicConfig(level=logging.DEBUG)

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    context: Optional[Any] # full ContextResolverResponse
    context_summary: Optional[str]
    active_pipeline_msg: Optional[str]
    rag_examples: Optional[str]


class ChatbotAgent:
    def __init__(self, 
                #  model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
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
        # base_llm = ChatGroq(
        #     model=model,
        #     api_key=os.getenv("GROQ_API_KEY"),
        #     temperature=temperature,
        #     max_tokens=max_output_tokens,
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

        history = list(state["messages"])
        
        # Inject context once as a system message (only on first turn)
        current_summary = state.get("context_summary")
        if history and isinstance(history[-1], ToolMessage):
            if "REPO_CONTEXT_SUMMARY:" in history[-1].content:
                # Extract the fresh summary from the tool output
                current_summary = history[-1].content.split("REPO_CONTEXT_SUMMARY:\n")[-1]

        
        messages_to_send = [SystemMessage(content=self.system_prompt)]
        
        if current_summary:
            messages_to_send.append(SystemMessage(content=f"PROJECT_CONTEXT:\n{current_summary}"))

        if state.get("active_pipeline_msg"):
            messages_to_send.append(SystemMessage(content=state["active_pipeline_msg"]))

        if state.get("rag_examples"):
            rag_msg = f"### REFERENCE EXAMPLES (Use these for inspiration):\n{state['rag_examples']}"
            messages_to_send.append(SystemMessage(content=rag_msg))
            
        clean_history = [m for m in history if not isinstance(m, SystemMessage)]
        if len(clean_history) > 10:
            clean_history = clean_history[-10:]
        messages_to_send.extend(clean_history)
        
        
        print("\n================ MESSAGES SENT TO MODEL ================")
        for m in messages_to_send:
            print(f"Role: {type(m).__name__}")
            print(f"Content: {m.content}")
            print("-" * 30)
        

        response = await self.llm.ainvoke(messages_to_send)

        print("\n================ MODEL RESPONSE ================")
        print(f"Content: {response.content}")
        print(f"Tool Calls: {response.tool_calls}")
        print("================================================\n")

        return {
            "messages": [response],
            "context_summary": state.get("context_summary"),
            "active_pipeline_msg": state.get("active_pipeline_msg"),
            "rag_examples": None,  # Reset RAG examples after each LLM call
        }

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
    

    def parse_full_response(self, content: str):
        # Regex to find all markdown code blocks
        # Group 1: language (e.g. yaml), Group 2: the code
        pattern = r"```(\w+)?\n(.*?)\n```"
        
        segments = []
        last_end = 0
        
        for match in re.finditer(pattern, content, re.DOTALL):
            # 1. Capture the text BEFORE the code block
            text_before = content[last_end:match.start()].strip()
            if text_before:
                segments.append({"type": "text", "content": text_before})
                
            # 2. Capture the CODE block itself
            language = match.group(1) or "text"
            code_content = match.group(2).strip()
            segments.append({
                "type": "code", 
                "language": language, 
                "content": code_content
            })
            
            last_end = match.end()
            
        # 3. Capture any text AFTER the last code block
        text_after = content[last_end:].strip()
        if text_after:
            segments.append({"type": "text", "content": text_after})
            
        return segments

    async def invoke(self, message: str, session_id: int, context: ContextResolverResponse | None, 
                     context_summary :str | None, chat_history: List[Dict[str, str]] = None, db: Optional[Any] = None, 
                     gitlab_connection: Optional[Any] = None, user_id: Optional[int] = None, project_id: Optional[int] = None,
                     pipeline_id : Optional[int] = None ,gitlab_project_id: Optional[Any] = None) -> str:
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
        active_pipeline_msg = ""
        if pipeline_id and db:
            result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
            p = result.scalar_one_or_none()
            if p:
                active_pipeline_msg = (
                    f"\n### USER IS CURRENTLY VIEWING THIS PIPELINE (PRIORITY):\n"
                    f"Name: {p.name}\n"
                    f"Content:\n```yaml\n{p.content}\n```\n"
                    f"This is the code the user is looking at on their screen. "
                    f"Ignore other YAML files in the repo if they conflict with this one."
                )
                print("################################### pipeline content:", p.content)
                # lc_messages = [SystemMessage(content=active_pipeline_msg)] + lc_messages

        print(lc_messages)
        initial_state = {
        "messages": lc_messages,
        "context": context,
        "context_summary": context_summary,
        "active_pipeline_msg" : active_pipeline_msg
        }
        result = await self.graph.ainvoke(initial_state, config=config)
        last_message = result["messages"][-1]

        # parsed_data = self.extract_pipeline_data(last_message.content)
        # return json.dumps(parsed_data) 
        segments = self.parse_full_response(last_message.content)
        return segments #returns a list of dicts