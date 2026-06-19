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

    # ── detections ────────────────────────────────────────────────────────
    languages   = Column(JSONB, default=list)
    frameworks  = Column(JSONB, default=list)
    build_tools = Column(JSONB, default=list)

    # ── test runners ──────────────────────────────────────────────────────
    test_runners        = Column(JSONB, default=list)
    test_runner_details = Column(JSONB, default=list)

    # ── test reports ──────────────────────────────────────────────────────
    has_test_reports = Column(Boolean, default=False)
    report_formats   = Column(JSONB, default=list)
    test_reports     = Column(JSONB, default=list)

    # ── CI / Docker ───────────────────────────────────────────────────────
    has_docker      = Column(Boolean, default=False)
    has_existing_ci = Column(Boolean, default=False)
    existing_ci_content = Column(Text, nullable=True)

    # ── NEW: commands + env + services ───────────────────────────────────
    test_commands  = Column(JSONB, default=list)
    build_commands = Column(JSONB, default=list)
    env_vars       = Column(JSONB, default=list)
    services       = Column(JSONB, default=list)

    # ── repo structure ────────────────────────────────────────────────────
    directory_tree = Column(Text, default="")
    key_files      = Column(JSONB, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())