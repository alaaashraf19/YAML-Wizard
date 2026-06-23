from ..BaseTestParser import BaseTestParser
from schemas.dashboard import TestResult
from typing import List


class MochaJSONParser(BaseTestParser):

    @property
    def supported_formats(self):
        return ["mocha_json"]
    
    @property
    def priority(self) -> int:
        return 10

    def can_parse(self, content: str, filename: str = "") -> bool:
        return (
            (
                filename.endswith(".json")
                or content.lstrip().startswith("{")
            )
            and '"suites"' in content
            and '"passes"' in content
        )

    def parse(self, content: str) -> List[TestResult]:

        data = self._safe_json_load(content)

        if not data:
            return []

        tests: List[TestResult] = []

        root_title = data.get("title", "")
        prefix = f"{root_title} › " if root_title else ""

        self._extract_tests(data, prefix, tests)

        return tests

    def _extract_tests(
        self,
        test_obj: dict,
        prefix: str,
        out: List[TestResult]
    ) -> None:

        # recurse through suites
        for suite in test_obj.get("suites", []):

            suite_title = suite.get("title", "")
            suite_prefix = (
                prefix + suite_title + " › "
                if suite_title else prefix
            )

            self._extract_tests(suite, suite_prefix, out)

        # extract tests
        for test in test_obj.get("tests", []):

            if test.get("pass"):
                status = "pass"
            elif test.get("pending"):
                status = "skip"
            else:
                status = "fail"

            error = (test.get("err") or {}).get("message")

            out.append(TestResult(
                test_name=prefix + test.get("title", ""),
                status=status,
                duration_ms=test.get("duration"),
                error=error,
                source="mocha_json",
                framework="mocha"
            ))