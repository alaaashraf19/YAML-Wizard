from __future__ import annotations
from datetime import datetime
from sqlalchemy import BigInteger, DateTime,Float,ForeignKey,Integer,String,Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base
from models.user_model import User

class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="repositories")

    full_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False, default="github")
    default_branch: Mapped[str] = mapped_column(String(100), nullable=False, default="main")
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # 1 to many with PipelineRun
    runs: Mapped[list[PipelineRun]] = relationship(back_populates="repository", cascade="all, delete-orphan")

    
class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    repo_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    
    # id from the platform that is why we call it external_id
    external_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    
    commit_hash: Mapped[str] = mapped_column(String(40), nullable=False)
    commit_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    branch: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    
    conclusion: Mapped[str | None] = mapped_column(String(30), nullable=True)
    
    total_duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    compared_to_prev_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    repository: Mapped[Repository] = relationship(back_populates="runs")
    jobs: Mapped[list[JobTiming]] = relationship(back_populates="run", cascade="all, delete-orphan")
    tests: Mapped[list[TestRun]] = relationship(back_populates="run", cascade="all, delete-orphan")


class JobTiming(Base):
    __tablename__ = "job_timings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    run_id: Mapped[int] = mapped_column(ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False)
    
    external_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    
    job_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    
    duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    compared_to_prev_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    run: Mapped[PipelineRun] = relationship(back_populates="jobs")
    #to be updatedd!!
    tests: Mapped[list[TestRun]] = relationship(back_populates="job", cascade="all, delete-orphan")

class TestRun(Base):
    __tablename__ = "test_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    run_id: Mapped[int] = mapped_column(ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[int] = mapped_column( ForeignKey("job_timings.id", ondelete="CASCADE"), nullable=False)

    test_name: Mapped[str] = mapped_column(String(500), nullable=False)
    
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    diff_from_avg_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    color: Mapped[str] = mapped_column(String(10), nullable=False, default="green")
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    framework: Mapped[str] = mapped_column(String(50), nullable=False)
    source_format: Mapped[str] = mapped_column(String(50), nullable=False)  # logs or reports


    run: Mapped[PipelineRun] = relationship(back_populates="tests")
    job: Mapped[JobTiming] = relationship(back_populates="tests")
    # Unique constraint: same test can't be recorded twice in same job 
    __table_args__ = ( UniqueConstraint('job_id', 'framework', 'test_name', name='uq_job_framework_test_name'), )