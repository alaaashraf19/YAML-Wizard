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
    #github installation
    github_installations = relationship(
            "GitHubInstallation",
            back_populates="user"
        )
    #github connection
    github_id = Column(Integer, unique=True, nullable=True, index=True)
    github_login = Column(String, nullable=True, index=True)

    #gitlab connection
    gitlab_connections = relationship(
        "GitLabConnection",
        back_populates="user"
    )