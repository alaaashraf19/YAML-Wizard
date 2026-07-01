from sqlalchemy.orm import mapped_column, relationship, Mapped
from database.base import Base
from models.user_model import User
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime, timezone
from .project_model import Project


class GitHubInstallation(Base):
    __tablename__ = "github_installations"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    installation_id: Mapped[int] = mapped_column(unique=True, index=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    account_login: Mapped[str | None] = mapped_column(nullable=True) #column for org or username
    account_id: Mapped[int | None] = mapped_column(nullable=True)
    account_type: Mapped[str | None] = mapped_column(nullable=True)
    repos_selection: Mapped[str | None] = mapped_column(nullable=True)

    #nullable is true since github webhook returns installation info but not user info, so we can have installations without associated users
    #we will link the installation to the user
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)#index for fast lookup
    user: Mapped["User"] = relationship("User", back_populates="github_installations")
    repos = relationship("GitHubInstallationRepo",back_populates="installation",cascade="all, delete-orphan")#one to many 
    projects: Mapped[list["Project"]] = relationship("Project",back_populates="github_installation",cascade="all, delete-orphan")

class GitHubInstallationRepo(Base):
    __tablename__ = "github_installation_repos"

    id = Column(Integer, primary_key=True)

    installation_id = Column(Integer, ForeignKey("github_installations.installation_id", ondelete="CASCADE"),nullable=False, unique=False)#not unique since installation can have many repos
    
    repo_id = Column(Integer, nullable=False, unique=True)
    repo_full_name = Column(String)
    repo_url = Column(String)
    installation = relationship("GitHubInstallation",back_populates="repos")
    

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


class OAuthState(Base):
    __tablename__ = "oauth_states"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String, nullable=False)  # "github", "gitlab"

    state = Column(String, unique=True, index=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="oauth_states")