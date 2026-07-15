import asyncio
from sqlalchemy import select
from models.repository_model import Repository
from .sync_services import sync_repository
from database.db_engine import async_session
from realtime.connection_manager import ws_manager
import os
from dotenv import load_dotenv

import traceback

load_dotenv()


SYNC_INTERVAL_MINUTES=os.getenv("SYNC_INTERVAL_MINUTES")

async def background_sync_loop():

    """Periodically sync all repositories in the background."""
    try:
        SYNC_INTERVAL_MINUTES = int(os.getenv("SYNC_INTERVAL_MINUTES", 5))
        interval = SYNC_INTERVAL_MINUTES * 60
        # print(f"[auto-sync] Background sync started — interval: {interval}s", flush=True)
    except Exception as e:
        # print(f"[auto-sync] STARTUP ERROR: {e}", flush=True)
        return

    while True:
        await asyncio.sleep(interval)

        try:
            async with async_session() as db:

                repos = (await db.execute(select(Repository))).scalars().all()
                repo_ids = [repo.id for repo in repos]

            # Sync each repo in its own session to avoid detached object issues
            for repo_id in repo_ids:
                try:
                    async with async_session() as db_repo:
                        # Fetch repo fresh in this session
                        repo_result = await db_repo.execute(select(Repository).where(Repository.id == repo_id))
                        repo = repo_result.scalar_one_or_none()
                        
                        if not repo:
                            continue
                        
                        sync_result = await sync_repository(repo.user_id, repo, db_repo)

                        # if sync_result.runs_synced > 0:
                        #     print(
                        #         f"[auto-sync] {repo.full_name}: "
                        #         f"{sync_result.runs_synced} runs, "
                        #         f"{sync_result.jobs_synced} jobs, "
                        #         f"{sync_result.tests_parsed} tests",
                        #         flush=True
                        #     )
                        # else:
                        #     print(f"[auto-sync] {repo.full_name}: up to date", flush=True)
                        
                        # Always broadcast sync complete (last_synced_at is always updated)
                        await ws_manager.broadcast(repo.id, {
                            "type": "sync_complete",
                            "repo_id": repo.id,
                            "runs_synced": sync_result.runs_synced,
                            "jobs_synced": sync_result.jobs_synced,
                            "tests_parsed": sync_result.tests_parsed,
                        })

                except Exception as e:
                    # print(f"Error syncing repo {repo.id}: {e}")
                    traceback.print_exc()
        except Exception as e:
            traceback.print_exc()

