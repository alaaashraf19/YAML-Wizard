"""
YAML Pipeline Sync Service
Periodically fetches YAML pipeline files from repositories and saves them as Pipeline records.
"""

import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository_model import Repository
from models.pipeline_model import Pipeline
from models.project_model import Project
from database.db_engine import async_session
from .platform_collectors.github_collector_services import GitHubCollector
from .platform_collectors.gitlab_collector_services import GitLabCollector
from schemas.dashboard import CollectorsRepositoryDetail, RepositorySchema
from schemas.yaml_sync_schema import YamlSyncResult, PipelineSyncResult
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()


class YAMLSyncService:
    def __init__(self):
        self.sync_interval_minutes = int(os.getenv("YAML_SYNC_INTERVAL_MINUTES", 30))
        self._running = False
        self._task: asyncio.Task | None = None

    def _create_context_from_repo(self, repo: Repository) -> CollectorsRepositoryDetail:
        """Create collector context from a Repository model instance."""
        repo_schema = RepositorySchema(
            id=repo.id,
            user_id=repo.user_id,
            full_name=repo.full_name,
            platform=repo.platform,
            gitlab_project_id=repo.gitlab_project_id,
            default_branch=repo.default_branch,
            url=repo.url,
            last_synced_at=repo.last_synced_at,
            created_at=repo.created_at,
        )
        parts = repo.full_name.split("/")
        return CollectorsRepositoryDetail(
            repo=repo_schema,
            gitlab_project_id=repo.gitlab_project_id,
            github_owner=parts[0] if len(parts) == 2 else None,
            github_repo=parts[1] if len(parts) == 2 else None,
        )

    # ---- Sync all YAML files for a repository ----
    async def sync_repository_yaml_files(
        self,
        repo_id: int,
        db: AsyncSession
    ) -> YamlSyncResult:
        """Sync all YAML files for a repository and store as Pipelines."""
        # fetch repo
        result = await db.execute(select(Repository).where(Repository.id == repo_id))
        repo = result.scalar_one_or_none()
        if not repo:
            return YamlSyncResult(
                repo_id=repo_id,
                repo_name="Unknown",
                platform="unknown",
                success=False,
                message="Repository not found"
            )

        # find project
        proj_result = await db.execute(select(Project).where(Project.repo_id == repo_id))
        project = proj_result.scalar_one_or_none()
        if not project:
            return YamlSyncResult(
                repo_id=repo_id,
                repo_name=repo.full_name,
                platform=repo.platform,
                success=False,
                message="No project linked to this repository"
            )

        ctx = self._create_context_from_repo(repo)

        # choose collector
        if repo.platform == "github":
            collector = GitHubCollector()
        elif repo.platform == "gitlab":
            collector = GitLabCollector()
        else:
            return YamlSyncResult(
                repo_id=repo_id,
                repo_name=repo.full_name,
                platform=repo.platform,
                success=False,
                message=f"Unsupported platform: {repo.platform}"
            )

        try:
            saved, updated = await collector.save_yaml_files(ctx, db)
            # Update last_synced_at
            repo.last_synced_at = datetime.now(timezone.utc)
            await db.commit()
            return YamlSyncResult(
                repo_id=repo_id,
                repo_name=repo.full_name,
                platform=repo.platform,
                files_synced=saved,
                files_updated=updated,
                files_found=saved + updated,
                success=True,
                message=f"Synced {saved} new, updated {updated} existing files"
            )
        except Exception as e:
            await db.rollback()
            return YamlSyncResult(
                repo_id=repo_id,
                repo_name=repo.full_name,
                platform=repo.platform,
                success=False,
                errors=[str(e)],
                message=f"Sync failed: {str(e)}"
            )
        finally:
            await collector.close()


    async def sync_single_pipeline(
        self,
        pipeline_id: int,
        user_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:


        result = await db.execute(
            select(Pipeline)
            .join(Project, Pipeline.project_id == Project.id)
            .where(Pipeline.id == pipeline_id, Project.user_id == user_id)
        )
        pipeline = result.scalar_one_or_none()
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")

        project = await db.get(Project, pipeline.project_id)
        if not project or not project.repo_id:
            raise HTTPException(status_code=400, detail="Project has no connected repository")

        repo = await db.get(Repository, project.repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        ctx = self._create_context_from_repo(repo)


        if repo.platform == "github":
            collector = GitHubCollector()
        elif repo.platform == "gitlab":
            collector = GitLabCollector()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported platform: {repo.platform}")

        try:
            # Fetch file with commit info
            if repo.platform == "github":
                file_data = await collector.get_file_with_commit_info(
                    ctx, pipeline.path, branch=pipeline.branch or repo.default_branch or "main"
                )
            else:
                file_data = await collector.get_file_with_commit_info(
                    ctx, pipeline.path, ref=pipeline.branch or repo.default_branch or "main"
                )

            if not file_data or not file_data.get("content"):
                raise HTTPException(status_code=404, detail=f"File {pipeline.path} not found in repository")

            # Update pipeline
            pipeline.content = file_data["content"]
            pipeline.updated_at = datetime.utcnow()
            pipeline.is_active = True
            if file_data.get("commit_hash"):
                pipeline.commit_hash = file_data["commit_hash"]
            if file_data.get("commit_author"):
                pipeline.commit_author = file_data["commit_author"]
            if file_data.get("commit_message"):
                pipeline.commit_message = file_data["commit_message"]
            if file_data.get("committed_at"):
                committed_at = file_data["committed_at"]
                if isinstance(committed_at, str):
                    pipeline.committed_at = datetime.fromisoformat(
                        committed_at.replace("Z", "+00:00")
                    )
                else:
                    pipeline.committed_at = committed_at
            if not pipeline.activated_at:
                pipeline.activated_at = datetime.utcnow()

            await db.commit()
            await db.refresh(pipeline)

            from schemas.pipeline_schema import PipelineResponse
            return PipelineResponse.model_validate(pipeline).model_dump()

        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
        finally:
            await collector.close()


    async def sync_all_repositories_yaml(self) -> list[YamlSyncResult]:
        """Sync YAML files for all repositories. Returns list of results."""
        results = []
        async with async_session() as db:
            repos = (await db.execute(select(Repository))).scalars().all()
            for repo in repos:
                try:
                    # Use a fresh session per repo to avoid conflicts
                    async with async_session() as repo_db:
                        result = await self.sync_repository_yaml_files(repo.id, repo_db)
                        results.append(result)
                except Exception as e:
                    results.append(YamlSyncResult(
                        repo_id=repo.id,
                        repo_name=repo.full_name,
                        platform=repo.platform,
                        success=False,
                        errors=[str(e)],
                        message=f"Unexpected error: {str(e)}"
                    ))
        return results


    async def start_background_sync(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._sync_loop())
        print(f"[YAML-Sync] Started (interval: {self.sync_interval_minutes} min)")

    async def stop_background_sync(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        print("[YAML-Sync] Stopped")

    async def _sync_loop(self):
        while self._running:
            try:
                await asyncio.sleep(self.sync_interval_minutes * 60)
                if not self._running:
                    break
                print(f"[YAML-Sync] Running scheduled sync at {datetime.now()}")
                results = await self.sync_all_repositories_yaml()
                total = len(results)
                success = sum(1 for r in results if r.success)
                files = sum(r.files_synced + r.files_updated for r in results)
                print(f"[YAML-Sync] Done: {success}/{total} repos, {files} files synced/updated")
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[YAML-Sync] Loop error: {e}")


# Global instance
yaml_sync_service = YAMLSyncService()