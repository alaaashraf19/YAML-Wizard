from datetime import datetime

from database.base import Base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime,Text,Boolean
from sqlalchemy.orm import relationship

class Pipeline(Base):
    __tablename__ = 'pipelines'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    path = Column(String, nullable=False)
    branch = Column(String, nullable=False)
    is_generated_by_wizard = Column(Boolean, nullable=False,default=True)
    description = Column(String, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow())
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow(), onupdate=datetime.utcnow())
    activated_at = Column(DateTime, nullable=True)

    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    project = relationship("Project", back_populates="pipelines",foreign_keys=[project_id])
