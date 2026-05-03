from database.base import Base
from sqlalchemy import Column, Integer, String, ForeignKey,DateTime
from sqlalchemy.orm import relationship
from datetime import datetime


class ChatSession(Base):
    __tablename__ = 'chat_sessions'

    id = Column(Integer, primary_key=True)
    session_name = Column(String,nullable=False,default="New Chat Session")
    created_at = Column(DateTime,nullable=False,default=datetime.utcnow())
    updated_at = Column(DateTime,nullable=False,default=datetime.utcnow(),onupdate=datetime.utcnow())

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    chat_messages = relationship(
        "ChatMessage",
        back_populates="chat_session",
        order_by="ChatMessage.order_index",
        cascade="all, delete-orphan"
    )
    user = relationship("User", back_populates="chat_sessions")
