from database.base import Base
from sqlalchemy import Column, Integer, String, ForeignKey,DateTime,Index
from sqlalchemy.orm import relationship
from datetime import datetime

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id = Column(Integer, primary_key=True)
    role = Column(String,nullable=False)
    content = Column(String,nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow(), nullable=False)
    order_index =  Column(Integer,nullable=False)

    user_id = Column(Integer, ForeignKey('users.id'),nullable=False)
    chat_session_id = Column(Integer, ForeignKey('chat_sessions.id'),nullable=False)

    chat_session = relationship("ChatSession", back_populates="chat_messages")
    user = relationship("User", back_populates="chat_messages")

    __table_args__ = (
        Index("idx_session_order", "chat_session_id", "order_index"),
    )