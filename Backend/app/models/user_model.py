from sqlalchemy.orm import relationship

from database.base import Base
from sqlalchemy import Column, Integer, String


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user") #user as default role, can be overridden to "admin" during signup if needed
    projects = relationship("Project", back_populates="user",cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user",cascade="all, delete-orphan")

    chat_messages = relationship("ChatMessage", back_populates="user",cascade="all, delete-orphan")
    github_installations = relationship("GitHubInstallation",back_populates="user",cascade="all, delete-orphan")

    #github connection
    github_connections = relationship("GitHubConnection", back_populates="user")

    #gitlab connection
    gitlab_connections = relationship("GitLabConnection",back_populates="user",cascade="all, delete-orphan")

    #repositories, 1 to many
    repositories = relationship("Repository",back_populates="user",cascade="all, delete-orphan")
