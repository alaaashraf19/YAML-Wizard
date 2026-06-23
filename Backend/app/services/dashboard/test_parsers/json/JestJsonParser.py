from ..BaseTestParser import BaseTestParser
from schemas.dashboard import TestResult
from typing import List


class JestJSONParser(BaseTestParser):

    @property
    def supported_formats(self):
        return ["jest_json"]

    @property
    def priority(self) -> int:
        return 10

    def can_parse(self, content: str, filename: str = "") -> bool:
        return (
            filename.endswith(".json") and
            '"assertionResults"' in content
        )

    def parse(self, content: str) -> List[TestResult]:
        data = self._safe_json_load(content)
        if not data:
            return []

        tests = []

        for file_result in data.get("testResults", []):
            for assertion in file_result.get("assertionResults", []):

                status_map = {
                    "passed": "pass",
                    "failed": "fail",
                    "skipped": "skip",
                    "pending": "skip",
                    "todo": "skip",
                }

                status = status_map.get(assertion["status"], assertion["status"])

                tests.append(TestResult(
                    test_name=assertion["fullName"],
                    status=status,
                    duration_ms=assertion.get("duration"),
                    error=(
                        assertion["failureMessages"][0]
                        if assertion.get("failureMessages")
                        else None
                    ),
                    source="jest_json",
                    framework="jest"
                ))

        return tests