from ..BaseTestParser import BaseTestParser
from schemas.dashboard import TestResult

from typing import List


class GenericJSONParser(BaseTestParser):

    @property
    def supported_formats(self):
        return ["custom_json"]

    @property
    def priority(self) -> int:
        return 1000

    def can_parse(self, content: str, filename: str = "") -> bool:

        #we only attempt generic detection if it looks like json
        if not (
            filename.endswith(".json")
            or content.lstrip().startswith("{")
        ):
            return False

        data = self._safe_json_load(content)

        if not data:
            return False

        tests = data.get("tests")

        return (
            isinstance(tests, list)
            and any(isinstance(t, dict) for t in tests)
        )

    def parse(self, content: str) -> List[TestResult]:

        data = self._safe_json_load(content)

        if not data:
            return []

        tests: List[TestResult] = []

        for test in data.get("tests", []):

            raw_status = test.get("status", "unknown")

            status_map = {
                "passed": "pass",
                "failed": "fail",
                "skipped": "skip",
                "pending": "skip"
            }

            status = status_map.get(raw_status, raw_status)

            duration=(test.get("duration") or test.get("time"))

            tests.append(TestResult(
                test_name=(
                    test.get("name")
                    or test.get("title")
                    or "unknown_test"
                ),
                status=status,
                duration_ms=self._safe_int(duration)
                ,
                error=(
                    test.get("error")
                    or test.get("message")
                ),
                source="custom_json",
                framework="unknown"
            ))

        return tests