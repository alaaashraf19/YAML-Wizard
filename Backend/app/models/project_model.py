from datetime import datetime
from database.base import Base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    project_name = Column(String,index= True,nullable=False)

    created_at = Column(DateTime,nullable=False,default=datetime.utcnow())
    updated_at = Column(DateTime,nullable=False,default=datetime.utcnow(),onupdate=datetime.utcnow())

    user_id = Column(Integer, ForeignKey('users.id'),nullable=False)
    repo_id = Column(Integer, ForeignKey('repositories.id', ondelete="CASCADE"),nullable=False, unique=True)
    active_pipeline_id = Column(Integer, ForeignKey('pipelines.id'),nullable=True)

    #link to the gitHub installation that created this project
    github_installation_id = Column(Integer,ForeignKey("github_installations.installation_id", ondelete="CASCADE"),nullable=True,index=True)

    user = relationship("User", back_populates="projects")
    chat_sessions = relationship("ChatSession", back_populates="project",cascade="all, delete-orphan")
    repository = relationship("Repository", back_populates="project", uselist=False, cascade="all, delete-orphan", single_parent=True)
    pipelines = relationship("Pipeline", back_populates="project",
                             cascade="all, delete-orphan",foreign_keys="Pipeline.project_id")
    active_pipeline = relationship("Pipeline",foreign_keys=[active_pipeline_id],post_update=True,uselist=False)
    github_installation = relationship("GitHubInstallation", back_populates="projects")