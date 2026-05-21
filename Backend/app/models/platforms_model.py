from sqlalchemy.orm import mapped_column, relationship, Mapped
from database.base import Base
from models.user_model import User
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime, timezone

class GitHubInstallation(Base):
    __tablename__ = "github_installations"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    installation_id: Mapped[int] = mapped_column(unique=True, index=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    account_login: Mapped[str | None] = mapped_column(nullable=True)
    account_id: Mapped[int | None] = mapped_column(nullable=True)
    
    #nullable is true since github webhook returns installation info but not user info, so we can have installations without associated users
    #we will link the installation to the user
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user: Mapped["User"] = relationship("User", back_populates="github_installations")




class GitLabConnection(Base):
    __tablename__ = "gitlab_connections"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), unique=True)    
    user = relationship("User", back_populates="gitlab_connections")

    gitlab_user_id = Column(Integer, index=True)
    gitlab_username = Column(String, index=True)

    access_token = Column(String)  # encrypt this
    refresh_token = Column(String, nullable=True)

    expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True),  default=lambda: datetime.now(timezone.utc))


class GitHubConnection(Base):
    __tablename__ = "github_connections"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    user = relationship("User", back_populates="github_connections")

    github_user_id = Column(Integer, index=True)
    github_username = Column(String, index=True)

    access_token = Column(String)  # encrypt this
    refresh_token = Column(String, nullable=True)  # GitHub may not always provide this

    expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))