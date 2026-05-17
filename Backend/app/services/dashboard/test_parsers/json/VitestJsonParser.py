from ..BaseTestParser import BaseTestParser
from schemas.dashboard import TestResult
from typing import List


class VitestJSONParser(BaseTestParser):

    @property
    def supported_formats(self):
        return ["vitest_json"]

    @property
    def priority(self) -> int:
        return 9   #higher priority than generic json

    def can_parse(self, content: str, filename: str = "") -> bool:
        if not filename.endswith(".json"):
            return False

        # Vitest blob reports usually contain these
        indicators = [
            '"testResults"',
            '"assertionResults"',
            '".vitest/"',
            '"vitest"',
        ]

        return any(indicator in content for indicator in indicators)

    def parse(self, content: str) -> List[TestResult]:
        data = self._safe_json_load(content)

        if not data:
            return []

        tests = []

        status_map = {
            "passed": "pass",
            "failed": "fail",
            "skipped": "skip",
            "pending": "skip",
            "todo": "skip",
        }

        for file_result in data.get("testResults", []):

            for assertion in file_result.get("assertionResults", []):

                status = status_map.get(
                    assertion.get("status"),
                    assertion.get("status")
                )

                tests.append(TestResult(
                    test_name=assertion.get("fullName", "Unknown Test"),
                    status=status,
                    duration_ms=assertion.get("duration"),
                    error=(
                        assertion["failureMessages"][0]
                        if assertion.get("failureMessages")
                        else None
                    ),
                    source="vitest_json",
                    framework="vitest"
                ))

        return tests