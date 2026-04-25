from database.base import Base
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    project_name = Column(String,index= True)
    repo_url = Column(String)
    target_platform = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'),nullable=False)
    user = relationship("User", back_populates="projects")

