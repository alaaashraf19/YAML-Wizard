import os
from sqlalchemy.orm import selectinload
from typing import List, Dict, Optional, Any
from fastapi import HTTPException
from datetime import datetime

from google import genai
# from google.genai import types

from sqlalchemy.orm import Session,joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,update,delete

from models.project_model import Project
from models.chat_message_model import ChatMessage
from models.chat_session_model import ChatSession
from models.platforms_model import GitLabConnection
from models.project_model import Project
from models.repository_model import Repository
from schemas.chatbot_schema import ChatSessionResponse
from services.project_service import get_project_by_id
from agent.chatbot_agent import ChatbotAgent
from agent.utils.context_resolver import ContextResolver, build_context_summary
from schemas.project_schema import ProjectResponse

class ChatbotService:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = "models/gemini-2.5-flash"
        # self.model = "Qwen/Qwen2.5-72B-Instruct-AWQ"
        self.agent = ChatbotAgent()

    async def send_message(self, message: str, session_id: int, chat_history: List[Dict[str, str]] = None, 
                           db: Optional[AsyncSession] = None,  user_id: Optional[int] = None, project_id: Optional[int] = None) -> Dict[str, str]:

        if not message or not message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        if chat_history is None:
            chat_history = []

        try:
            contents = []

            # for msg in chat_history:
            #     role = "user" if msg["role"] == "user" else "model"
            #     contents.append(types.Content(
            #         role = role,
            #         parts = [types.Part.from_text(text=msg["content"])]
            #     ))

            # contents.append(types.Content(
            #     role = "user",
            #     parts = [types.Part.from_text(text=message)]
            # ))

            gitlab_connection = None
            gitlab_project_id = None
            if db is not None and user_id is not None and project_id is not None:
                platform, repo_gitlab_project_id = await self.resolve_gitlab_target(project_id, user_id, db)
                if platform == "gitlab":
                    gitlab_result = await db.execute(select(GitLabConnection).where(GitLabConnection.user_id == user_id))
                    gitlab_connection = gitlab_result.scalar_one_or_none()
                    gitlab_project_id = repo_gitlab_project_id

            context = None
            context_summary= None
            if project_id is not None:
                print("before project context in chat")
                context = await ContextResolver(db).get_project_context(project_id)

                if context:
                    context_summary = build_context_summary(context.repo_context)#return str

            # print("context in chat",context )
            response = await self.agent.invoke(
                message=message,
                chat_history=chat_history,
                db=db,
                gitlab_connection=gitlab_connection,
                gitlab_project_id=gitlab_project_id,
                session_id = session_id,
                user_id= user_id,
                project_id=project_id,
                context = context,
                context_summary = context_summary
            )
            return {
                "role": "assistant",
                "content":str(response)
            }

        except Exception as e:
            error_text = str(e)

            if "RESOURCE_EXHAUSTED" in error_text or "429" in error_text:
                return{
                    "status_code": 429,
                    "role": "assistant",
                    "content": "⚠️ You've reached the usage limit. Please try again later.",
                    "error": error_text
                }
            
            return{
                "status_code": 500,
                "role": "assistant",
                "content": "⚠️ Sorry, something went wrong while generating my response. Please try sending your message again.",
                "error": error_text
            }

    async def resolve_gitlab_target(self, project_id: int, user_id: int, db: AsyncSession) -> tuple[Optional[str], Optional[int]]:
        row = await db.execute(
            select(Repository.platform, Repository.gitlab_project_id)
            .join(Project, Project.repo_id == Repository.id)
            .where(Project.id == project_id, Project.user_id == user_id)
        )
        result = row.one_or_none()
        if result is None:
            return None, None
        platform, gitlab_project_id = result
        return platform, gitlab_project_id

    async def process_chat_message(
            self,
            user_id: int,
            message: str,
            session_id: Optional[int],
            project_id : Optional[int],
            pipeline_id : Optional[int],
            db: AsyncSession
    ) -> Dict[str, Any]:

        if not session_id:
            session = await self.create_new_session(
                user_id=user_id,
                first_message=message,
                project_id=project_id,
                db=db
            )
            session_id = session.id
            chat_history = []
            if project_id:
                project = await get_project_by_id(project_id, user_id, db)
                session.project_id = project.id
                session.updated_at = datetime.utcnow()
                await db.commit()
                await db.refresh(session)
        else:
            session = await self.get_session_if_owned(
                user_id=user_id,
                session_id=session_id,
                db=db
            )
            if not session:
                raise HTTPException(
                    status_code=404,
                    detail="Chat session not found or access denied"
                )

            # load existed chat history
            chat_history = await self.get_session_messages(
                user_id=user_id,
                session_id=session_id,
                db=db
            )

        session_name = session.session_name
        if pipeline_id and not session.pipeline_id:
            session.pipeline_id = pipeline_id
            session.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(session)

        result = await self.send_message(
            message=message,
            session_id= session_id,
            user_id=user_id,
            project_id = session.project_id,
            chat_history=chat_history,
            db=db,
            user_id=user_id,
            project_id=project_id
        )

        user_msg, bot_msg = await self.save_conversation_turn(
            user_id=user_id,
            session_id=session_id,
            user_message=message,
            bot_response=result["content"],
            db=db
        )

        full_history = await self.get_session_messages(
            user_id=user_id,
            session_id=session_id,
            db=db
        )

        if isinstance(result, dict) and result.get("error"):
            raise HTTPException(
                status_code=result["status_code"],
                detail={
                    "session_id" : session_id,
                    "session_name": session_name,
                    "message": {
                        "role": "assistant",
                        "content": result["content"],
                        "timestamp": bot_msg.timestamp.isoformat()
                    },
                    "error": result.get("error")
                }
            )

        return {
            "session_id": session_id,
            "session_name": session_name,
            "bot_response": result["content"],
            "bot_timestamp": bot_msg.timestamp,
            "full_history": full_history
        }

    async def create_new_session(
            self, user_id: int,first_message: str, db:AsyncSession,project_id : Optional[int] = None
    ) -> ChatSession:
        from agent.chat_session_title import generate_session_title
        title = await generate_session_title(first_message)
        session_name = title or self.default_session_name(first_message)
        new_session = ChatSession(user_id = user_id,session_name = session_name,project_id=project_id,
                                  created_at=datetime.utcnow(),updated_at=datetime.utcnow())
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        return new_session

    #fallback naming method in case the ai title model fails
    def default_session_name(self, first_message: str) -> str:
        return first_message[:50] + "..." if len(first_message) > 50 else first_message

    async def get_session_if_owned(
            self,
            user_id: int,
            session_id: int,
            db: AsyncSession
    ) -> Optional[ChatSession]:

        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id)
        )
        return result.scalars().one_or_none()

    async def save_conversation_turn(
            self,
            user_id: int,
            session_id: int,
            user_message: str,
            bot_response: str,
            db: AsyncSession
    ) -> tuple[ChatMessage, ChatMessage]:

        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.chat_session_id == session_id)
        )
        max_order = len(result.scalars().all())

        user_msg = ChatMessage(
            user_id = user_id,
            chat_session_id = session_id,
            role = "user",
            content = user_message,
            order_index= max_order
        )
        db.add(user_msg)

        bot_msg = ChatMessage(
            user_id = user_id,
            chat_session_id = session_id,
            role = "assistant",
            content = bot_response,
            order_index = max_order + 1
        )
        db.add(bot_msg)
        await db.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(updated_at=datetime.utcnow())
        )
        await db.commit()
        await db.refresh(user_msg)
        await db.refresh(bot_msg)
        return user_msg, bot_msg

    async def get_session_messages(
            self,
            user_id: int,
            session_id: int,
            db: AsyncSession
    ) -> List[Dict[str, Any]]:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.chat_session_id == session_id,ChatMessage.user_id == user_id)
            .order_by(ChatMessage.order_index)
        )
        messages = result.scalars().all()
        return [
            {
                "role":msg.role,
                "content":msg.content,
                "timestamp":msg.timestamp
            }
            for msg in messages
        ]

    async def get_user_sessions(
            self,
            user_id: int,
            db: AsyncSession
    )->List[ChatSession]:

        results = await db.execute(
            select(ChatSession)
            .options(joinedload(ChatSession.project).joinedload(Project.repository),
                     joinedload(ChatSession.pipeline))
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
        )
        return results.unique().scalars().all()

    async def get_session_by_pipId(
            self,
            user_id: int,
            pipeline_id: int,
            db: AsyncSession
    )->ChatSessionResponse:
        result = await db.execute(
            select(ChatSession)
            .options(joinedload(ChatSession.project),
                     joinedload(ChatSession.pipeline) )
            .where(ChatSession.user_id == user_id,ChatSession.pipeline_id == pipeline_id)
        )
        session =  result.unique().scalar_one_or_none()
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Chat session not found or access denied"
            )
        return ChatSessionResponse(
            id=session.id,
            session_name=session.session_name,
            created_at=session.created_at,
            updated_at=session.updated_at,
            project_id=session.project_id,
            project={
                "id": session.project_id,
                "project_name": session.project.project_name,
                "user_id": user_id,
                "repo_id": session.project.repo_id,
                "repo_url": session.project.repository.url,
                "platform": session.project.repository.platform,
                "created_at": session.project.created_at,
                "updated_at": session.project.updated_at
            } if session.project else None,
            pipeline={
                "id": session.pipeline_id,
                "name": session.pipeline.name,
                "content": session.pipeline.content,
                "path": session.pipeline.path,
                "branch": session.pipeline.branch,
                "is_generated_by_wizard": session.pipeline.is_generated_by_wizard,
                "description": session.pipeline.description,
                "created_at": session.pipeline.created_at,
                "updated_at": session.pipeline.updated_at,
                "activated_at": session.pipeline.activated_at,
            } if session.pipeline else None,
        )

    async def get_session_with_messages(
            self,
            user_id: int,
            session_id: int,
            db: AsyncSession
    ) -> Dict[str, Any]:
        # session = await self.get_session_if_owned(user_id,session_id,db)
        result = await db.execute(
            select(ChatSession)
            .options(joinedload(ChatSession.project))
            .where(ChatSession.id == session_id,ChatSession.user_id == user_id)
        )

        session = result.scalars().one_or_none()

        if not session:
            raise HTTPException(
                status_code=404,
                detail="Chat session not found or access denied"
            )

        messages = await self.get_session_messages(user_id,session_id,db)

        return {
            "session_id": session.id,
            "session_name": session.session_name,
            "project_id": session.project_id,
            "project" : {
                "id": session.project_id,
                "name": session.project.project_name
            } if session.project else None,
            "pipeline":{
                "id" : session.pipeline_id,
                "name": session.pipeline.name,
                "content": session.pipeline.content,
                "path": session.pipeline.path,
                "branch": session.pipeline.branch,
                "is_generated_by_wizard": session.pipeline.is_generated_by_wizard,
                "description": session.pipeline.description,
                "created_at": session.pipeline.created_at,
                "updated_at": session.pipeline.updated_at,
                "activated_at": session.pipeline.activated_at,
            } if session.pipeline else None,
            "messages": messages
        }

    async def delete_session(self, user_id: int, session_id: int, db: AsyncSession) -> None:
        session = await self.get_session_if_owned(user_id,session_id,db)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found or access denied")
        await db.delete(session)
        await db.commit()

    async def get_project_sessions(
            self,
            user_id: int,
            project_id: int,
            db: AsyncSession
    ) -> List[ChatSession]:
        results = await db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.project))
            .where(ChatSession.user_id == user_id,ChatSession.project_id == project_id)
            .order_by(ChatSession.updated_at.desc())
        )
        return results.scalars().all()

    async def link_session_to_project(
            self,
            user_id: int,
            session_id: int,
            project_id: int,
            db: AsyncSession
    ) -> ProjectResponse:
        session = await self.get_session_if_owned(user_id,session_id,db)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found or access denied")
        if session.project_id:
            raise HTTPException(status_code=409, detail="Session already linked to a project")#409 for conflict
        project = await get_project_by_id(project_id,user_id,db)
        session.project_id = project.id
        session.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(session)
        return project
