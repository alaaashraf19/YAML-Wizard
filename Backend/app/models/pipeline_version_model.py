from datetime import datetime
from database.base import Base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship


class PipelineVersion(Base):
    __tablename__ = 'pipeline_versions'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    path = Column(String, nullable=False)
    branch = Column(String, nullable=False)
    is_generated_by_wizard = Column(Boolean, nullable=False, default=True)
    description = Column(String, nullable=True)

    is_active = Column(Boolean, nullable=False, default=False)

    commit_hash = Column(String(40), nullable=True)
    commit_author = Column(String(255), nullable=True)
    commit_message = Column(Text, nullable=True)
    committed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)

    pipeline_id = Column(Integer, ForeignKey('pipelines.id', ondelete="CASCADE"), nullable=False, index=True)
    pipeline = relationship("Pipeline", back_populates="versions", foreign_keys=[pipeline_id])
