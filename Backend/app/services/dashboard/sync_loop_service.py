import asyncio
from sqlalchemy import select
from models.repository_model import Repository
from .sync_services import sync_repository
from database.db_engine import async_session
from realtime.connection_manager import ws_manager
import os
from dotenv import load_dotenv

from .yaml_sync_service import yaml_sync_service

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

                for repo in repos:
                    try:
                        async with async_session() as db_repo:
                            sync_result = await sync_repository(repo.id, db_repo)

                        if sync_result.runs_synced > 0:
                            # print(
                            #     f"[auto-sync] {repo.full_name}: "
                            #     f"{sync_result.runs_synced} runs, "
                            #     f"{sync_result.jobs_synced} jobs, "
                            #     f"{sync_result.tests_parsed} tests",
                            #     flush=True
                            # )

                            await ws_manager.broadcast(repo.id, {
                                "type": "sync_complete",
                                "repo_id": repo.id,
                                "runs_synced": sync_result.runs_synced,
                                "jobs_synced": sync_result.jobs_synced,
                                "tests_parsed": sync_result.tests_parsed,
                            })
                        else:
                            # print(f"[auto-sync] {repo.full_name}: up to date", flush=True)
                            pass

                    except Exception as e:
                        # print(f"[auto-sync] ERROR repo_id={repo.id}: {e}", flush=True)
                        continue
        except Exception as e:
            # print(f"[auto-sync] LOOP ERROR: {e}", flush=True)
            continue

# async def yaml_sync_loop():
#     """
#     Periodically sync YAML pipeline files from repositories.
#     This runs independently of the CI/CD data sync.
#     """
#     await yaml_sync_service.start_background_sync()
