from database.base import Base
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from schemas.repo_schema import Platform
from sqlalchemy.sql import func


    
class RepoContext(Base):
    __tablename__ = "repo_context"
    id = Column(Integer, primary_key=True, index=True)
    # Foreign key
    #unique=True because one repo context per project
    # if project is deleted delete repos too, prevents orphaned repo contexts
    # project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), unique=True,, index=True)


    # might remove url and platform and specify the branch
    url = Column(String, nullable=False)
    platform = Column(Enum(Platform), nullable=False)

    default_branch = Column(String, default="main")
    languages = Column(JSONB, default=list)
    frameworks = Column(JSONB, default=list)
    build_tools = Column(JSONB, default=list)
    test_runners = Column(JSONB, default=list)

    has_docker = Column(Boolean, default=False)
    has_existing_ci = Column(Boolean, default=False)

    existing_ci_content = Column(Text, nullable=True) #text is safer than string since yaml files can be large and multiline, text can handle that better than string which is often limited in size
    directory_tree = Column(Text, default="")

    key_files = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    #connect it to repositoy
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), unique=True)