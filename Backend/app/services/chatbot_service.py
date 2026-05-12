import os
from typing import List, Dict, Optional, Any
from fastapi import HTTPException
from datetime import datetime

from google import genai
from google.genai import types

from sqlalchemy.orm import Session
from models.chat_message_model import ChatMessage
from models.chat_session_model import ChatSession


class ChatbotService:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = "models/gemini-2.5-flash"

    async def send_message(self, message: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, str]:

        if not message or not message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        if chat_history is None:
            chat_history = []

        try:
            contents = []

            for msg in chat_history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(types.Content(
                    role = role,
                    parts = [types.Part.from_text(text=msg["content"])]
                ))

            contents.append(types.Content(
                role = "user",
                parts = [types.Part.from_text(text=message)]
            ))

            response = self.client.models.generate_content(
                model = self.model,
                contents = contents,
                config = types.GenerateContentConfig(
                    temperature = 0.7,
                    max_output_tokens = 2500,
                )
            )


            return {
                "role": "assistant",
                "content": response.text.strip(),
            }

        except Exception as e:
            error_text = str(e)

            if "RESOURCE_EXHAUSTED" in error_text or "429" in error_text:
                return{
                    "status_code": 429,
                    "role": "assistant",
                    "content": "The chatbot has reached its limit. Please try again later.",
                    "error": error_text
                }
            
            return{
                "status_code": 500,
                "role": "assistant",
                "content": "Something went wrong while generating the response.",
                "error": error_text
            }

    async def process_chat_message(
            self,
            user_id: int,
            message: str,
            session_id: Optional[int],
            db: Session
    ) -> Dict[str, Any]:

        if not session_id:
            session = await self.create_new_session(
                user_id=user_id,
                first_message=message,
                db=db
            )
            session_id = session.id
            chat_history = []
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

        result = await self.send_message(
            message=message,
            chat_history=chat_history
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

        return {
            "session_id": session_id,
            "session_name": session_name,
            "bot_response": result["content"],
            "bot_timestamp": bot_msg.timestamp,
            "full_history": full_history
        }

    async def create_new_session(self, user_id: int,first_message: str, db:Session) -> ChatSession:
        session_name = first_message[:50] + "..." if len(first_message) > 50 else first_message
        new_session = ChatSession(user_id = user_id,session_name = session_name)
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return new_session

    async def get_session_if_owned(
            self,
            user_id: int,
            session_id: int,
            db: Session
    ) -> Optional[ChatSession]:

        return db.query(ChatSession).filter(
        ChatSession.id == session_id,
                ChatSession.user_id == user_id
        ).first()

    async def save_conversation_turn(
            self,
            user_id: int,
            session_id: int,
            user_message: str,
            bot_response: str,
            db: Session
    ) -> tuple[ChatMessage, ChatMessage]:

        max_order = db.query(ChatMessage).filter(ChatMessage.chat_session_id == session_id).count()

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
        db.query(ChatSession).filter(ChatSession.id == session_id).update({
            "updated_at": datetime.utcnow()
        })
        db.commit()
        db.refresh(user_msg)
        db.refresh(bot_msg)
        return user_msg, bot_msg

    async def get_session_messages(
            self,
            user_id: int,
            session_id: int,
            db: Session
    ) -> List[Dict[str, Any]]:
        messages = db.query(ChatMessage).filter(
            ChatMessage.chat_session_id == session_id,
            ChatMessage.user_id == user_id
        ).order_by(
            ChatMessage.order_index
        ).all()
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
            db: Session
    )->List[ChatSession]:

        return db.query(ChatSession).filter(
            ChatSession.user_id == user_id
        ).order_by(ChatSession.updated_at.desc()).all()

    async def get_session_with_messages(
            self,
            user_id: int,
            session_id: int,
            db: Session
    ) -> Dict[str, Any]:
        session = await self.get_session_if_owned(user_id,session_id,db)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Chat session not found or access denied"
            )
        messages = await self.get_session_messages(user_id,session_id,db)
        return {
            "session_id": session.id,
            "session_name": session.session_name,
            "messages": messages
        }

    async def delete_session(self, user_id: int, session_id: int, db: Session) -> None:
        session = await self.get_session_if_owned(user_id,session_id,db)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found or access denied")
        db.delete(session)
        db.commit()

