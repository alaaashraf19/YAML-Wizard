from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.dashboard import PipelineRun, TestRun
from schemas.dashboard import Insight


async def generate_insights(repo_id: int, db: AsyncSession, run_id: int | None = None, limit: int = 10,) -> list[Insight]:
    
    """Analyze pipeline data and produce actionable insights for a specific run (or latest)."""

    insights: list[Insight] = []

    #we get latest 10 runs tpo have context for our rules
    result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.repo_id == repo_id)
        .order_by(PipelineRun.started_at.desc())
        .limit(10)
    )
    recent_runs = result.scalars().all()
    if not recent_runs:
        return insights

    # if we decide a run_id, if left none we take the very latest run from the 10 we just fetched
    if run_id:

        target_run = next((r for r in recent_runs if r.id == run_id), None)#check if we fetched it

        if not target_run:#fetch  from db
            
            r = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
            
            target_run = r.scalar_one_or_none()

            if not target_run:
                return insights
    else:
        target_run = recent_runs[0]

    #we get the previous run (the one before target_run)
    prev_run = None
    found_target = False
    for r in recent_runs:
        if found_target:
            prev_run = r
            break
        if r.id == target_run.id:
            found_target = True

    # 1. Slowdown detection for THIS run
    if target_run.compared_to_prev_pct and target_run.compared_to_prev_pct > 20:
        insights.append(Insight(
            level="warning",
            icon="⚠️",
            title=f"Pipeline {int(target_run.compared_to_prev_pct)}% slower",
            detail=(
                f"This commit took {target_run.total_duration_s}s "
                f"({int(target_run.compared_to_prev_pct)}% slower than previous run)"
            ),
            commit_hash=target_run.commit_hash,
        ))

    # 2. Failure in this run
    if target_run.conclusion == "failure":
        insights.append(Insight(
            level="error",
            icon="❌",
            title="Pipeline failed",
            detail=target_run.commit_message or "No commit message",
            commit_hash=target_run.commit_hash,
        ))

    # 3. Recovery detection — this run succeeded but previous failed
    if prev_run and target_run.conclusion == "success" and prev_run.conclusion == "failure":
        insights.append(Insight(
            level="success",
            icon="✅",
            title="Pipeline recovered",
            detail=f"Previous commit {prev_run.commit_hash[:8]} was failing. Now fixed.",
            commit_hash=target_run.commit_hash,
        ))

    # 4. Test-level issues for this run
    test_result = await db.execute(
        select(TestRun)
        .where(TestRun.run_id == target_run.id, TestRun.color.in_(["orange", "red"]))
        .order_by(TestRun.diff_from_avg_pct.desc())
    )
    slow_tests = test_result.scalars().all()
    for test in slow_tests[:3]:
        diff_str = f"+{int(test.diff_from_avg_pct)}%" if test.diff_from_avg_pct else ""
        if test.color == "red" and test.status in ("fail", "error"):
            insights.append(Insight(
                level="error",
                icon="🔴",
                title=f"Test '{test.test_name}' failing",
                detail=f"Failed in this run",
                commit_hash=target_run.commit_hash,
                test_name=test.test_name,
            ))
        elif test.color in ("orange", "red"):
            insights.append(Insight(
                level="warning",
                icon="🟠",
                title=f"Test '{test.test_name}' is {diff_str} slower",
                detail=(
                    f"Current: {test.duration_ms}ms, "
                    f"Avg: {int(test.avg_duration_ms or 0)}ms"
                ),
                commit_hash=target_run.commit_hash,
                test_name=test.test_name,
            ))

    # 5. All tests passed insight
    if target_run.conclusion == "success" and not slow_tests:
        all_tests = await db.execute(
            select(func.count()).select_from(TestRun).where(TestRun.run_id == target_run.id)
        )
        count = all_tests.scalar() or 0
        if count > 0:
            insights.append(Insight(
                level="success",
                icon="✅",
                title=f"All {count} tests passed",
                detail="No performance regressions detected.",
                commit_hash=target_run.commit_hash,
            ))

    # 6. Trend detection — consistently getting slower over last 5 runs (global context)
    if len(recent_runs) >= 5:
        slowdown_count = sum(
            1 for r in recent_runs[:5]
            if r.compared_to_prev_pct and r.compared_to_prev_pct > 5
        )
        if slowdown_count >= 3:
            insights.append(Insight(
                level="warning",
                icon="📈",
                title="Pipeline trending slower",
                detail=f"{slowdown_count} of last 5 runs were slower than their predecessor.",
            ))

    return insights[:limit]