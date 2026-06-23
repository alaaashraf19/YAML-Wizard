from ..BaseTestParser import BaseTestParser
from schemas.dashboard import TestResult

from typing import List


class BaseJUnitXMLParser(BaseTestParser):

    framework_name = "unknown"

    def parse(self, content: str) -> List[TestResult]:

        root = self._safe_xml_load(content)

        if root is None:
            return []

        tests: List[TestResult] = []

        testsuites = root.findall(".//testsuite")

        if not testsuites:
            testsuites = (
                [root]
                if root.tag == "testsuite"
                else []
            )

        for testsuite in testsuites:

            for testcase in testsuite.findall("testcase"):

                classname = testcase.get("classname", "")
                name = testcase.get("name", "")

                test_name = (
                    f"{classname}::{name}"
                    if classname else name
                )

                duration_ms = self._to_ms(
                    testcase.get("time")
                )

                status = "pass"
                error_msg = None

                failure = testcase.find("failure")
                error = testcase.find("error")
                skipped = testcase.find("skipped")

                if failure is not None:
                    status = "fail"
                    error_msg = failure.get("message", "")

                elif error is not None:
                    status = "error"
                    error_msg = error.get("message", "")

                elif skipped is not None:
                    status = "skip"

                tests.append(TestResult(
                    test_name=test_name,
                    status=status,
                    duration_ms=duration_ms,
                    error=error_msg,
                    source=self.supported_formats[0],
                    framework=self.framework_name
                ))

        return tests