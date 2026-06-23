from ..BaseTestParser import BaseTestParser
from schemas.dashboard import TestResult
from typing import List


class BaseNUnitXMLParser(BaseTestParser):

    framework_name = "nunit"

    STATUS_MAP = {
        "Success": "pass",
        "Failure": "fail",
        "Error": "error",
        "Skipped": "skip",
        "Inconclusive": "skip",
    }

    def parse(self, content: str) -> List[TestResult]:

        root = self._safe_xml_load(content)

        if root is None:
            return []

        tests: List[TestResult] = []

        def extract_tests(element, prefix=""):

            for testcase in element.findall("test-case"):

                name = testcase.get("name", "")
                result = testcase.get("result", "unknown")

                duration_ms = self._to_ms(
                    testcase.get("duration")
                )

                error_msg = None

                failure = testcase.find("failure")

                if failure is not None:
                    message = failure.find("message")

                    if message is not None:
                        error_msg = message.text

                tests.append(TestResult(
                    test_name=prefix + name,
                    status=self.STATUS_MAP.get(
                        result,
                        "unknown"
                    ),
                    duration_ms=duration_ms,
                    error=error_msg,
                    source=self.supported_formats[0],
                    framework=self.framework_name
                ))

            for suite in element.findall("test-suite"):

                extract_tests(
                    suite,
                    prefix + element.get("name", "") + " › "
                )

        extract_tests(root)

        return tests