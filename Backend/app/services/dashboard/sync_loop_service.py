import asyncio
from sqlalchemy import select
from models.dashboard import Repository
from .sync_services import sync_repository
from database.db_engine import async_session
from realtime.connection_manager import ws_manager
import os
from dotenv import load_dotenv
load_dotenv()


SYNC_INTERVAL_MINUTES=os.getenv("SYNC_INTERVAL_MINUTES")

async def background_sync_loop():

    """Periodically sync all repositories in the background."""
    try:
        SYNC_INTERVAL_MINUTES = int(os.getenv("SYNC_INTERVAL_MINUTES", 5))
        interval = SYNC_INTERVAL_MINUTES * 60
        print(f"[auto-sync] Background sync started — interval: {interval}s", flush=True)
    except Exception as e:
        print(f"[auto-sync] STARTUP ERROR: {e}", flush=True)
        return

    while True:
        await asyncio.sleep(interval)
        try:
            async with async_session() as db:
                print("here")

                repos = (await db.execute(select(Repository))).scalars().all()
                for repo in repos:
                    try:
                        result = await sync_repository(repo, db)
                        if result.runs_synced > 0:
                            print(
                                f"[auto-sync] {repo.full_name}: "
                                f"{result.runs_synced} runs, {result.jobs_synced} jobs, "
                                f"{result.tests_parsed} tests", flush=True
                            )
                            await ws_manager.broadcast(repo.id, {
                                "type": "sync_complete",
                                "repo_id": repo.id,
                                "runs_synced": result.runs_synced,
                                "jobs_synced": result.jobs_synced,
                                "tests_parsed": result.tests_parsed,
                            })
                        else:
                            print(f"[auto-sync] {repo.full_name}: up to date", flush=True)
                    except Exception as e:
                        print(f"[auto-sync] ERROR {repo.full_name}: {e}", flush=True)
        except Exception as e:
            print(f"[auto-sync] LOOP ERROR: {e}", flush=True)