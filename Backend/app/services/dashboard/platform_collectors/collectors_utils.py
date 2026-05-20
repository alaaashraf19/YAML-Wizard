import os
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from ..recommendations_services.processor_services import compute_test_avg_and_color
from models.dashboard import JobTiming, TestRun
from schemas.dashboard import TestResult

from typing import Tuple
from io import BytesIO
import zipfile

async def process_test_batch(parsed_tests: list[TestResult], run_id:int, repo_id:int, db: AsyncSession, job : JobTiming | None,):

    tests_found = 0
    for test in parsed_tests:

        avg, diff, color = await compute_test_avg_and_color(test.test_name,  test.duration_ms, test.status, repo_id,db,)
        db.add(TestRun(
            run_id=run_id,
            job_id=job.id if job else None,
            test_name=test.test_name,
            status=test.status,
            duration_ms=test.duration_ms,
            avg_duration_ms=avg,
            diff_from_avg_pct=diff,
            color=color,
            error_message=test.error,
            framework=test.framework,
            source_format=test.source,
        ))
        tests_found += 1

    return tests_found


def parse_duration(started_at: str | None, completed_at: str | None) -> int | None:
        
    """Calculate duration in seconds from ISO timestamps"""
    #github timings are like: "2026-05-10T12:00:00Z"
    # we convert to "2026-05-10T12:00:00+00:00"
    if not started_at or not completed_at:
        return None
    try:
        #this creates an object like: datetime(2026, 5, 10, 12, 0, tzinfo=UTC)
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        return max(0, int((end - start).total_seconds()))
    except (ValueError, TypeError):
        return None
    

def _parse_ts(time: str | None) -> datetime | None:
    if not time:
        return None
    try:
        return datetime.fromisoformat(time.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    


def extract_test_reports_from_zip(zip_data: bytes) -> list[Tuple[str, str, str]]:
    
    """
    Extract structured test report files from CI artifact ZIPs.

    Returns:
        [(filename, content, extension), ...]
    """

    reports = []

    VALID_EXTENSIONS = {".xml", ".json"}

    COMMON_REPORT_PATTERNS = [
        "test",
        "tests",
        "report",
        "reports",
        "result",
        "results",
        "junit",
        "surefire",
        "failsafe",
        "pytest",
        "nunit",
        "trx",
        "jest",
        "playwright",
        "mocha",
        "rspec",
    ]

    try:
        with zipfile.ZipFile(BytesIO(zip_data)) as z:

            for file_info in z.filelist:
                fname = file_info.filename
                lower_name = fname.lower()

                # skip directories
                if file_info.is_dir():
                    continue
                ext = os.path.splitext(lower_name)[1]
                # skip unsupported file types
                if ext not in VALID_EXTENSIONS:
                    continue
                # heuristic filter
                if not any(p in lower_name for p in COMMON_REPORT_PATTERNS):
                    continue
                try:
                    content = z.read(fname).decode("utf-8",errors="ignore")
                    reports.append((fname, content, ext.lstrip(".")))
                except Exception as e:
                    print(f"Failed reading report file {fname}: {e}", flush=True)

    except Exception as e:
        print(f"Failed to extract artifact zip: {e}", flush=True)

    return reports