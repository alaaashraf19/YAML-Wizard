from datetime import datetime

from database.base import Base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    project_name = Column(String,index= True,nullable=False)
    repo_url = Column(String,nullable=False)
    target_platform = Column(String,nullable=False)
    created_at = Column(DateTime,nullable=False,default=datetime.utcnow())
    updated_at = Column(DateTime,nullable=False,default=datetime.utcnow(),onupdate=datetime.utcnow())

    user_id = Column(Integer, ForeignKey('users.id'),nullable=False)
    active_pipeline_id = Column(Integer, ForeignKey('pipelines.id'),nullable=True)

    user = relationship("User", back_populates="projects")
    chat_sessions = relationship("ChatSession", back_populates="project",cascade="all, delete-orphan")
    pipelines = relationship("Pipeline", back_populates="project",
                             cascade="all, delete-orphan",foreign_keys="Pipeline.project_id")
    active_pipeline = relationship("Pipeline",foreign_keys=[active_pipeline_id],post_update=True,uselist=False)