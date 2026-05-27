from database.base import Base
from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from schemas.repo_schema import Platform
from sqlalchemy.sql import func


class RepoContext(Base):
    __tablename__ = "repo_context"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)
    platform = Column(Enum(Platform), nullable=False)
    default_branch = Column(String, default="main")

    languages   = Column(JSONB, default=list)
    frameworks  = Column(JSONB, default=list)
    build_tools = Column(JSONB, default=list)

    test_runners        = Column(JSONB, default=list)
    test_runner_details = Column(JSONB, default=list)

    # names match ContextPackage + API response schema
    has_test_reports = Column(Boolean, default=False)
    report_formats   = Column(JSONB, default=list)
    test_reports     = Column(JSONB, default=list)

    has_docker      = Column(Boolean, default=False)
    has_existing_ci = Column(Boolean, default=False)

    existing_ci_content = Column(Text, nullable=True)
    directory_tree      = Column(Text, default="")
    key_files           = Column(JSONB, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())