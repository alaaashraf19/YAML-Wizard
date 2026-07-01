from __future__ import annotations
from datetime import datetime
from sqlalchemy import BigInteger, DateTime,Float,ForeignKey,Integer,String,Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.project_model import Project
from database.base import Base
from models.user_model import User
from models.repo_context_model import RepoContext

class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="repositories")

    full_name: Mapped[str] = mapped_column(String(255), unique=False, nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False, default="github")
    #we can add an id for both gitlab and github but for now we will add only for gitlab because github repo can be identified by full_name 
    # which is unique but in gitlab we have to use id because there can be multiple projects with same name but different namespace so we will 
    # use id to identify the project
    gitlab_project_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    github_repo_id: Mapped[int | None] = mapped_column(BigInteger,nullable=True,index=True,)
    installation_id: Mapped[int | None] = mapped_column(ForeignKey("github_installations.installation_id", ondelete="CASCADE"),nullable=True,)
    default_branch: Mapped[str] = mapped_column(String(100), nullable=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False,)

    # 1 to many with PipelineRun
    runs: Mapped[list[PipelineRun]] = relationship(back_populates="repository", cascade="all, delete-orphan")
    project: Mapped[Project | None] = relationship("Project",back_populates="repository", uselist=False)#uselist is false to tell that it is one to one relation
    context: Mapped[RepoContext | None] = relationship("RepoContext",back_populates="repository", uselist=False, cascade="all, delete-orphan")#if a repo is deleted its context is deleted
    __table_args__ = (UniqueConstraint("user_id", "url", name="uq_user_repo_url"),
        #A user cannot add the same GitHub ID twice
        UniqueConstraint("user_id", "github_repo_id", name="uq_user_github_id"),)

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    repo_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    
    # id from the platform that is why we call it external_id, external_id = GitHub run id / GitLab pipeline id
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

    #job_id nullable is true because we can parse tests from artifacts and in github artifacts are related to runs not jobs so it can be empty
    job_id: Mapped[int] = mapped_column( ForeignKey("job_timings.id", ondelete="CASCADE"), nullable=True)
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
    job: Mapped[JobTiming| None] = relationship(back_populates="tests")

    # will be added laterr
    # source_job_name: str | None
    # artifact_name: str | None
    # Unique constraint: same test can't be recorded twice in same job 
    __table_args__ = ( UniqueConstraint('run_id', 'framework', 'test_name', name='uq_run_framework_test_name'), )