# YAML-Wizard Sync Status Tracking Analysis

## Executive Summary

The YAML-Wizard project uses a **simple but functional** sync tracking mechanism based on a single `last_synced_at` timestamp. While it works, there are several areas for improvement, including a **critical method signature mismatch** between GitHub and GitLab collectors.

---

## 1. How Sync Status is Tracked

### Data Model

**Repository Model** ([`models/repository_model.py:29`](models/repository_model.py))
```python
last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

**SyncStatus Schema** ([`schemas/dashboard.py:91-96`](schemas/dashboard.py))
```python
class SyncStatus(BaseModel):
    repo_id: int
    runs_synced: int
    jobs_synced: int
    tests_parsed: int
    message: str
```

### Tracking Details

- **Single timestamp field**: `last_synced_at` on Repository model
- **Nullable**: Allows distinguishing "never synced" from "synced"
- **UTC timezone-aware**: `datetime.now(timezone.utc)`
- **No history tracking**: Only current last sync time is stored

---

## 2. When `last_synced_at` is Set and Retrieved

### SET - During Sync Operations

**GitHub Collector** ([`github_collector_services.py:206`](Backend/app/services/dashboard/platform_collectors/github_collector_services.py#L206))
```python
ctx.repo.last_synced_at = datetime.now(timezone.utc)
await db.commit()
```
- Set **inside the for loop** after each run is processed
- Committed multiple times per sync (inefficient!)
- Location: End of each successful run processing

**GitLab Collector** ([`gitlab_collector_services.py:222`](Backend/app/services/dashboard/platform_collectors/gitlab_collector_services.py#L222))
- Identical pattern to GitHub

### RETRIEVED - Displayed and Logged

1. **Frontend Display** ([`RepoSidebar.tsx:99-101`](Frontend/src/components/Dashboard/RepoSidebar.tsx))
   ```typescript
   {repo.last_synced_at && formatDate(repo.last_synced_at)}
   ```
   Shows "Last synced: [timestamp]" in UI

2. **YAML Sync Service** ([`yaml_sync_service.py:50`](Backend/app/services/dashboard/yaml_sync_service.py#L50))
   ```python
   last_synced_at=repo.last_synced_at,  # Passed to RepositorySchema
   ```

3. **Repository List Endpoint** ([`repos_router.py:26`](Backend/app/routers/dashboard/repos_router.py#L26))
   - Returns RepoOut schema which includes `last_synced_at`

---

## 3. Sync Logic in Collectors

### GitHub Collector Flow

```
fetch_runs(per_page=MAX_RUNS_PER_SYNC)
    ↓
for each run:
    → Skip if already synced (external_id check)
    → Skip if status != "completed"
    → Create PipelineRun record
    → fetch_jobs(run_id)
    ↓
    for each job:
        → Create JobTiming record
        → get_artifacts_for_run()  [look for test reports]
        → if no artifacts: sync_job_tests()  [parse logs]
        → sync: update last_synced_at, commit()
```

**Key Filter on Line 141-142:**
```python
if raw_run.get("status") != "completed":
    continue
```
Only completed runs are synced!

### GitLab Collector Flow

```
get_runs(per_page=MAX_RUNS_PER_SYNC)
    ↓
for each pipeline:
    → Skip if already synced (external_id check)
    → Skip if status NOT in {"success", "failed"}
    → Create PipelineRun record
    → fetch_jobs(pipeline_id)
    ↓
    for each job:
        → Create JobTiming record
        → Check for artifacts_file
        → if has_artifacts: get_artifacts_for_job()
        → if no artifacts: sync_job_tests()
        → sync: update last_synced_at, commit()
```

**Key Filter on Line 195-196:**
```python
if pipeline.get("status") not in {"success", "failed"}:
    continue
```
Only completed pipelines are synced!

---

## 4. Sync History & Logging Mechanism

### What EXISTS:

1. **Console Logging** ([`sync_loop_service.py:30-35`](Backend/app/services/dashboard/sync_loop_service.py))
   ```python
   print(f"[auto-sync] {repo.full_name}: {sync_result.runs_synced} runs, ...")
   ```

2. **WebSocket Broadcasts** ([`sync_loop_service.py:42-50`](Backend/app/services/dashboard/sync_loop_service.py))
   ```python
   await ws_manager.broadcast(repo.id, {
       "type": "sync_complete",
       "repo_id": repo.id,
       "runs_synced": sync_result.runs_synced,
       "jobs_synced": sync_result.jobs_synced,
       "tests_parsed": sync_result.tests_parsed,
   })
   ```
   Real-time notification to connected clients

3. **SyncStatus API Response** ([`repos_router.py:46-55`](Backend/app/routers/dashboard/repos_router.py#L46))
   ```python
   @router.post("/repos/sync/{repo_id}")
   async def sync_repo(...) -> SyncStatus:
   ```
   Returns counts of synced items

### What DOES NOT EXIST:

❌ **No persistent sync history table**
- Only current timestamp is stored
- No record of past sync attempts
- Cannot see "sync happened 5 times today"

❌ **No sync logs/audit trail**
- Logs only go to stdout (console)
- Not persisted to database
- Disappear on server restart

❌ **No per-sync error tracking**
- Errors are returned in SyncStatus.message
- Not stored for later review

❌ **No failed sync recovery**
- If a sync fails, no automatic retry
- No queue of pending syncs
- Manual retry required

❌ **No sync status indicators** (in DB)
- Can't query "is sync in progress?"
- No locking mechanism
- Concurrent syncs could corrupt data

---

## 5. Sync Status Checks & Filters

### Authentication & Authorization

**[sync_services.py:16-18]**
```python
token, _ = await _resolve_token(user_id, repo.platform, repo.url, db)
if token is None:
    raise HTTPException(status_code=401, detail="No auth token")
```
**Impact**: No token = sync fails immediately

### Repository Ownership

**[repos_router.py:50-55]**
```python
result = await db.execute(
    select(Repository).where(
        Repository.id == repo_id and 
        Repository.user_id == current_user.id
    )
)
```
**Impact**: User can only sync their own repos

### Duplicate Run Prevention

**[github_collector_services.py:143-145]**
```python
existing = await db.execute(
    select(PipelineRun).where(
        PipelineRun.external_id == external_id,
        PipelineRun.repo_id == ctx.repo.id
    )
)
if existing.scalar_one_or_none():
    continue  # Skip already synced
```
**Impact**: Prevents duplicate data entry

### Completion Status Filters

**GitHub**: `status == "completed"` only
**GitLab**: `status in {"success", "failed"}` only
**Impact**: In-progress/queued runs are skipped

### MAX_RUNS_PER_SYNC Limit

**[github_collector_services.py:127-129]**
```python
max_runs = os.getenv("MAX_RUNS_PER_SYNC")
if max_runs is None:
    raise ValueError("MAX_RUNS_PER_SYNC not found...")
raw_runs = await self.get_runs(ctx, per_page=int(max_runs))
```
**Impact**: Env var controls how many runs fetched per sync

### Project Requirement

**[yaml_sync_service.py:76-85]**
```python
proj_result = await db.execute(
    select(Project).where(Project.repo_id == repo_id)
)
project = proj_result.scalar_one_or_none()
if not project:
    return YamlSyncResult(..., message="No project linked")
```
**Impact**: YAML sync fails if no project exists

---

## 🔴 CRITICAL ISSUE: Method Signature Mismatch

### Problem Description

The `sync_job_tests` method has **different signatures** in GitHub vs GitLab collectors:

**GitHub** ([`github_collector_services.py:295`](Backend/app/services/dashboard/platform_collectors/github_collector_services.py#L295))
```python
async def sync_job_tests(self, ctx: CollectorsRepositoryDetail, job: JobTiming, db: AsyncSession):
```

**GitLab** ([`gitlab_collector_services.py:303`](Backend/app/services/dashboard/platform_collectors/gitlab_collector_services.py#L303))
```python
async def sync_job_tests(self, run: PipelineRun, ctx: CollectorsRepositoryDetail, job: JobTiming, db: AsyncSession):
                                 ↑↑↑↑↑↑↑↑↑↑ EXTRA PARAMETER
```

### How They're Called

**GitHub** ([`github_collector_services.py:195`](Backend/app/services/dashboard/platform_collectors/github_collector_services.py#L195))
```python
job_tests = await self.sync_job_tests(ctx, job, db)
```

**GitLab** ([`gitlab_collector_services.py:211`](Backend/app/services/dashboard/platform_collectors/gitlab_collector_services.py#L211))
```python
job_tests = await self.sync_job_tests(run, ctx, job, db,)
```

### Why This Matters

1. **Code Maintainability**: Different signatures for same functionality is confusing
2. **Duplicate Logic**: Nearly identical code with different parameters
3. **Bug Risk**: If one is updated, other might not be
4. **Inconsistency**: Violates DRY principle

### Recommendation

Standardize the signature. Since both methods do the same thing (parse logs for tests), they should have identical signatures. Options:

**Option A: Remove `run` from GitLab** (since `job` has `run_id`)
```python
# Both would use:
async def sync_job_tests(self, ctx, job, db):
```

**Option B: Normalize to CICollector base**
Create abstract method in base class to enforce consistency

---

## Summary of Potential Issues Preventing Syncs

| Issue | Impact | Severity |
|-------|--------|----------|
| No auth token | Sync fails immediately | 🔴 Critical |
| User doesn't own repo | 404 error | 🔴 Critical |
| No project linked | YAML sync fails silently | 🟡 High |
| All runs already synced | "0 synced" response (normal) | 🟢 Low |
| Run status incomplete | Skipped (by design) | 🟢 Low |
| MAX_RUNS_PER_SYNC too low | Old runs never fetched | 🟡 High |
| Network timeout (30s) | Sync fails with exception | 🟡 High |
| DB unique constraint | Duplicate external_id fails | 🔴 Critical |
| Method signature mismatch | Maintenance risk | 🟡 High |

---

## Additional Observations

### Performance Considerations

1. **`last_synced_at` update inside loop** (Line 206/222)
   - Updated and committed for each run
   - Could be moved outside loop for single commit
   - Current approach: N commits per sync (N = runs synced)
   - Optimized approach: 1 commit at end

2. **No sync locking**
   - Two concurrent sync requests could race
   - Could cause duplicate data or inconsistency

3. **No pagination continuation**
   - Always fetches first N runs
   - If you have 100 runs but MAX=50, only latest 50 synced
   - Older runs never synced

### Frontend Integration

- Real-time updates via WebSocket
- Last sync timestamp displayed in sidebar
- No sync history view available
- No error details shown to user

---

## Recommendations

### High Priority

1. **Fix method signature mismatch** - Standardize both collectors
2. **Add sync locking** - Prevent concurrent sync races
3. **Move `last_synced_at` update** - Single commit per sync, not per run
4. **Add error persistence** - Store failed sync details

### Medium Priority

1. **Add sync history table** - Track all sync attempts
2. **Add retry mechanism** - Automatic retry on failure
3. **Add pagination** - Sync older runs beyond MAX_RUNS_PER_SYNC
4. **Add sync status endpoint** - Query "is sync in progress?"

### Low Priority

1. **Add sync logs UI** - View past sync history/details
2. **Add sync stats** - Total runs/jobs/tests synced over time
3. **Implement cleanup** - Archive old sync history

