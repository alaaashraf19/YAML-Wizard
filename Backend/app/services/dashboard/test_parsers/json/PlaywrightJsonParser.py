from ..BaseTestParser import BaseTestParser
from schemas.dashboard import TestResult
from typing import List

class PlaywrightJSONParser(BaseTestParser):

    @property
    def supported_formats(self):
        return ["playwright_json"]

    @property
    def priority(self) -> int:
        return 10

    def can_parse(self, content: str, filename: str = "") -> bool:
        if not content.lstrip().startswith("{"):
            return False

        return (
            '"suites"' in content
            and '"tests"' in content
            and '"results"' in content
        )

    def parse(self, content: str) -> List[TestResult]:
        data = self._safe_json_load(content)
        if not data:
            return []

        tests: List[TestResult] = []

        for suite in data.get("suites", []):
            self._extract_suite(suite, prefix="", out=tests)

        return tests
    
    def _extract_suite(self, suite_obj: dict, prefix: str, out: list[TestResult]):
        for test in suite_obj.get("tests", []):

            test_name = prefix + test.get("title", "")

            results = test.get("results", [])

            if results:
                result = results[0]

                status_map = {
                    "passed": "pass",
                    "failed": "fail",
                    "skipped": "skip"
                }

                status = status_map.get(
                    result.get("status"),
                    result.get("status", "unknown")
                )

                duration = result.get("duration")
            else:
                status_map = {
                    "passed": "pass",
                    "failed": "fail",
                    "skipped": "skip"
                }

                status = status_map.get(test.get("status"), "unknown")
                duration = None

            out.append(TestResult(
                test_name=test_name,
                status=status,
                duration_ms=duration,
                error=None,
                source="playwright_json",
                framework="playwright"
            ))

        for child in suite_obj.get("suites", []):
            child_title = child.get("title", "")
            child_prefix = prefix + child_title + " › " if child_title else prefix
            self._extract_suite(child, child_prefix, out)