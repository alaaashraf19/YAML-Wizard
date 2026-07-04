from ..BaseTestParser import BaseTestParser
from schemas.dashboard import TestResult
from typing import List

class RSpecJSONParser(BaseTestParser):

    @property
    def supported_formats(self):
        return ["rspec_json"]

    @property
    def priority(self) -> int:
        return 10
    
    def can_parse(self, content: str, filename: str = "") -> bool:
        return (
            filename.endswith(".json")
            and '"examples"' in content
            and '"full_description"' in content
        )

    def parse(self, content: str) -> List[TestResult]:
        data = self._safe_json_load(content)
        if not data:
            return []

        tests: List[TestResult] = []

        for example in data.get("examples", []):

            status_map = {
                "passed": "pass",
                "failed": "fail",
                "pending": "skip"
            }

            raw_status = example.get("status", "unknown")
            status = status_map.get(raw_status, raw_status)

            exception = example.get("exception") or {}

            tests.append(TestResult(
                test_name=example.get("full_description", ""),
                status=status,
                duration_ms=self._to_ms(example.get("run_time")),
                error=exception.get("message"),
                source="rspec_json",
                framework="rspec"
            ))

        return tests