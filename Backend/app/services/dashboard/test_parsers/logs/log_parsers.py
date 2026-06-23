import re
from .BaseLogPraser import BaseLogParser
from schemas.dashboard import TestResult
from typing import List, Set


class JestLogsParser(BaseLogParser):
    """Parse Jest console output"""
    framework_name = "jest"
    
    @property
    def supported_formats(self):
        return ["jest_logs"]
    
    @property
    def priority(self):
        return 50
    
    @property
    def status_map(self) -> dict:
        return {}############################################### to be updated
    
    def can_parse(self, content: str, filename: str = "") -> bool:

        # remove ANSI escape codes first 
        clean = re.sub(r"\x1b\[[0-9;]*m", "", content)

        strong_signals = [
            "Test Suites:",
            "Tests:",
            "Snapshots:",
            "Ran all test suites",
        ]

        score = 0

        for sig in strong_signals:
            if sig in clean:
                score += 2

        #Jest file result pattern
        if re.search(r"\b(PASS|FAIL)\s+.*\.test\.(js|ts|jsx|tsx)", clean):
            score += 2

        #filename hint
        if ".test." in filename or ".spec." in filename:
            score += 1

        return score >= 3
    
    def _extract_test_name(self, match: re.Match) -> str:
        return match.group(1).strip()
    
    def _extract_status(self, match: re.Match) -> str:
        return 'pass' if '✓' in match.group(0) else 'fail'
    
    def _parse(self, content: str) -> List[TestResult]:

        # remove ANSI escape codes  
        clean = re.sub(r"\x1b\[[0-9;]*m", "", content)

        tests: List[TestResult] = []
        seen_files: Set[str] = set()

        #if filenames exist in logs we can extract per-file results with status and duration.
        #example : PASS e2e/__tests__/browserBasic.test.ts(16.098 s)

        file_pattern = re.compile(
            r"\b(?P<status>PASS|FAIL)\s+"
            r"(?P<file>.+?\.(?:test|spec)\.(?:js|ts|jsx|tsx))"
            r"(?:\s+\((?P<duration>[\d.]+)\s*s\))?"
        )

        for match in file_pattern.finditer(clean):

            file_name = match.group("file").strip()
            status_raw = match.group("status").lower()
            duration_str = match.group("duration")

            if file_name in seen_files:
                continue
            seen_files.add(file_name)

            duration_ms = None

            if duration_str:
                try:
                    duration_ms = int(float(duration_str) * 1000)
                except ValueError:
                    duration_ms = None

            tests.append(TestResult(
                test_name=file_name,
                status="pass" if status_raw == "pass" else "fail",
                duration_ms=duration_ms,
                error=None,
                source=self.supported_formats[0],
                framework=self.framework_name,
                file=file_name,
                is_aggregated=True
            ))

        # we search for the overall summary line which contains total test counts and pass/fail numbers. 
        # which is a strong signal of Jest output and gives us the ground truth for the overall test run result.

        # Test Suites: 2 passed, 2 total
        # Tests:       16 passed, 16 total

        summary_match = re.search(
            r"Test Suites:\s+"
            r"(?:(\d+)\s+passed)?"
            r"(?:,\s*(\d+)\s+failed)?"
            r".*?(\d+)\s+total.*?"
            r"Tests:\s+"
            r"(?:(\d+)\s+passed)?"
            r"(?:,\s*(\d+)\s+failed)?"
            r".*?(\d+)\s+total",
            clean,
            re.DOTALL
        )

        if summary_match:

            suites_passed = int(summary_match.group(1) or 0)
            suites_failed = int(summary_match.group(2) or 0)
            suites_total = int(summary_match.group(3) or 0)

            tests_passed = int(summary_match.group(4) or 0)
            tests_failed = int(summary_match.group(5) or 0)
            tests_total = int(summary_match.group(6) or 0)

            tests.append(TestResult(
                test_name="__jest_summary__",

                status="fail" if tests_failed > 0 else "pass",

                passed_count=tests_passed,
                failed_count=tests_failed,
                skipped_count=max(
                    0,
                    tests_total - tests_passed - tests_failed
                ),

                suite_passed_count=suites_passed,
                suite_failed_count=suites_failed,
                suite_total_count=suites_total,

                source=self.supported_formats[0],
                framework=self.framework_name,
                is_aggregated=True
            ))

        # if we see the "Ran all test suites" line, we can add a final aggregated result 
        # indicating the run completed successfully

        if "Ran all test suites" in clean:

            tests.append(TestResult(
                test_name="__jest_run_complete__",
                status="pass",
                source=self.supported_formats[0],
                framework=self.framework_name,
                is_aggregated=True
            ))

        return tests


class PytestLogsParser(BaseLogParser):
    """Parse pytest console output"""
    framework_name = "pytest"
    
    @property
    def supported_formats(self):
        return ["pytest_logs"]
    
    @property
    def priority(self):
        return 50
    
    
    @property
    def status_map(self) -> dict:
        return {
            'PASSED': 'pass',
            'FAILED': 'fail',
            'ERROR': 'error',
            'SKIPPED': 'skip'
        }
    
    def can_parse(self, content: str, filename: str = "") -> bool:
        score = 0

        indicators = [
            "test session starts",
            "collected",
            "warnings summary",
            "::",
            "pytest-",
            "plugins:",
            "passed",
        ]

        for indicator in indicators:
            if indicator in content:
                score += 2

        # in pytest logs there are often lines called pytest node IDS that look like this:
        # test_module.py::TestClass::test_method PASSED [ 50%]
        if re.search(r"\w+\.py::", content):
            score += 3

        # parametrized tests
        if re.search(r"::.*\[.*\]", content):
            score += 2

        return score >= 5


    def _parse(self, content: str) -> List[TestResult]:

        tests: List[TestResult] = []

        seen_lines: Set[str] = set()
        seen_tests: Set[str] = set()
  
        # =====================================================================
        # STRATEGY 1: test-level results with node IDs and optional durations
        # (e.g., "test_auth.py::test_login PASSED").
        # =====================================================================

        node_pattern = re.compile(
            r"(?P<node>[\w\\/\\-\\.]+::[\w\\[\\]\\-\\.]+)\s+"
            r"(?P<status>PASSED|FAILED|ERROR|SKIPPED|XPASS|XFAIL)"
        )

        for m in node_pattern.finditer(content):
            line = m.group(0)

            if line in seen_lines:
                continue
            seen_lines.add(line)

            test_name = m.group("node")
            status_raw = m.group("status")

            if test_name in seen_tests:
                continue
            seen_tests.add(test_name)

            tests.append(TestResult(
                test_name=test_name,
                status=self.status_map.get(status_raw, status_raw.lower()),
                duration_ms=None, #Standard stdout lacks duration
                error=None,
                source=self.supported_formats[0],
                framework=self.framework_name,
                is_aggregated=False #False because we successfully found a specific individual test
            ))

        # =====================================================================
        # strategy 2: file-level results
        # if Pytest runs in default mode (no `-v`), It only prints the file name and progressno test names
        # characters (e.g., "tests/test_api.py ..F.s").
        # Since we cannot extract the exact test name, we group the results by file
        # =====================================================================

        file_stats = {}

        progress_pattern = re.compile(
            r"^(tests?[\\/][^\s]+)\s+([\.FsExX]+)",
            re.MULTILINE
        )

        for m in progress_pattern.finditer(content):
            file_name = m.group(1)
            progress = m.group(2)

            if file_name not in file_stats:
                file_stats[file_name] = {
                    "pass": 0,
                    "fail": 0,
                    "skip": 0,
                    "error": 0,
                    "xfail": 0,
                    "xpass": 0,
                }

            for ch in progress:
                status = {
                    ".": "pass",
                    "F": "fail",
                    "s": "skip",
                    "E": "error",
                    "x": "xfail",
                    "X": "xpass",
                }.get(ch)

                if status:
                    file_stats[file_name][status] += 1

        # convert file stats into results
        for file_name, stats in file_stats.items():

            tests.append(TestResult(
                test_name=file_name,
                status="fail" if stats["fail"] > 0 else "pass",
                duration_ms=None,
                error=None,
                source=self.supported_formats[0],
                framework=self.framework_name,
                file=file_name,
                passed_count=stats["pass"],
                failed_count=stats["fail"],
                skipped_count=stats["skip"],
                is_aggregated=True #True because this represents a whole file, not a single test
            ))

        # =====================================================================
        # strategy 3: summary line
        # (e.g., "=== 12 passed, 2 failed in 0.43s ===") 
        # by parsing a final `__summary__` testresult, we ensure that the total counts are 100% accurate, 
        # even if we missed a few progress dots earlier in the log.
        # =====================================================================

        summary = re.search(
            r"=+\s*(\d+)\s+passed.*?(\d+)\s+failed.*?(\d+)\s+skipped",
            content
        )

        if summary:
            tests.append(TestResult(
                test_name="__summary__",
                status="fail" if int(summary.group(2)) > 0 else "pass",
                source=self.supported_formats[0],
                framework=self.framework_name,
                passed_count=int(summary.group(1)),
                failed_count=int(summary.group(2)),
                skipped_count=int(summary.group(3)),
                is_aggregated=True
            ))

        return tests



class GoLogsParser(BaseLogParser):
    """Parse Go test output"""
    
    framework_name = "go"
    
    @property
    def supported_formats(self):
        return ["go_logs"]
    
    @property
    def priority(self):
        return 50
    

    @property
    def status_map(self) -> dict:
        return {
            "PASS": "pass",
            "FAIL": "fail",
            "SKIP": "skip",
            "ok": "pass",
        }
    def can_parse(self, content: str, filename: str = "") -> bool:
        strong_indicators = [
            "=== RUN",
            "--- PASS",
            "--- FAIL",
            "=== PAUSE",
            "ok\t",
            "FAIL\t",
        ]

        score = 0

        for indicator in strong_indicators:
            if indicator in content:
                score += 2

        # very Go-specific structure: test function names
        if "=== RUN" in content and "/" not in content:
            score += 1

        # subtests (very Go-specific)
        if "=== RUN" in content and "/" in content:
            score += 2

        # result markers
        if "--- PASS" in content or "--- FAIL" in content:
            score += 2

        return score >= 3
    
    def _extract_test_name(self, match: re.Match) -> str:
        return match.group(2)
    

    def _parse(self, content: str) -> List[TestResult]:

        tests: List[TestResult] = []

        seen_names: Set[str] = set()

        # =====================================================================
        # strategy 1: individual go test results (verbose mode / failures)
        # why we do this: if a developer runs `go test -v` (or if a test fails 
        # in normal mode), go explicitly prints `--- pass/fail/skip`.
        # unlike pytest or minitest, go's stdout natively includes the exact test duration
        # --- pass: testx (0.12s)
        # --- fail: testy/sub (1.45s)
        # --- skip: testz (0.00s)
        # =====================================================================

        test_pattern = re.compile(
            r"---\s+(PASS|FAIL|SKIP):\s+(.+?)\s+\(([\d.]+)s\)"
        )

        for match in test_pattern.finditer(content):

            status_raw = match.group(1)
            test_name = match.group(2).strip()
            duration_sec = float(match.group(3))

            if test_name in seen_names:
                continue

            seen_names.add(test_name)

            parent_test = None
            is_subtest = False

            # --------------------------------------------------------
            # detect go subtests (table-driven tests)
            # go heavily relies on "table-driven tests"
            # using `t.run("subcase")`. the output formats this as `testparent/subcase`.
            # we can allow users to click `testparent` to expand all its subcases.
            # --------------------------------------------------------

            if "/" in test_name:
                parent_test = test_name.split("/")[0]
                is_subtest = True

            tests.append(TestResult(
                test_name=test_name,
                status=self.status_map.get(status_raw, "unknown"),
                duration_ms=int(duration_sec * 1000),
                error=None,
                source=self.supported_formats[0],
                framework=self.framework_name,

                # hierarchy metadata
                parent_test=parent_test,
                is_subtest=is_subtest,

                # optional
                is_aggregated=False
            ))
        # =====================================================================
        # strategy 2: package summary lines (non-verbose mode)
        # if a user runs `go test ./...` (without `-v`), go 
        # will not print individual tests for packages that pass. it will only print a single line per package
        # this acts as our fallback. if we didn't find individual tests, we 
        # at least record that the entire package passed and how long it took.
        # Examples:
        # ok   github.com/x/y   0.123s
        # FAIL github.com/x/y   0.456s
        # =====================================================================

        summary_pattern = re.compile(
            r"^(ok|FAIL)\s+([^\s]+)\s+([\d.]+)s",
            re.MULTILINE
        )

        for match in summary_pattern.finditer(content):

            status_raw = match.group(1)
            package_name = match.group(2)
            duration_sec = float(match.group(3))

            tests.append(TestResult(
                test_name="__go_summary__",
                status=self.status_map.get(status_raw, "unknown"),
                duration_ms=int(duration_sec * 1000),
                error=None,
                source=self.supported_formats[0],
                framework=self.framework_name,

                is_aggregated=True,
                file=package_name
            ))

        return tests



class RspecLogsParser(BaseLogParser):
    """Parse RSpec output"""
    
    framework_name = "rspec"
    
    @property
    def supported_formats(self):
        return ["rspec_logs"]
    
    @property
    def priority(self):
        return 50
    
    
    @property
    def status_map(self) -> dict:
        return {}
    
    def can_parse(self, content: str, filename: str = "") -> bool:
        strong_indicators = [
            "Finished in",
            "examples,",
            "Failures:",
            "example,",#sometimes singular/plural appears
            "rspec",
        ]

        score = 0

        for indicator in strong_indicators:
            if indicator in content:
                score += 2

        # dot progress output (VERY RSpec-specific)
        if any(c in content for c in [".", "F", "S", "*"]):
            score += 1

        # failure formatting (strong signal)
        if "Failure/Error" in content or "expected:" in content and "got:" in content:
            score += 2

        return score >= 3 and ("examples," in content or "Failures:" in content)
    
    def _extract_test_name(self, match: re.Match) -> str:
        return match.group(1).strip()
    
    def _extract_status(self, match: re.Match) -> str:
        return 'pass' if '✓' in match.group(0) else 'fail'
    
    def _parse(self, content: str) -> List[TestResult]:

        tests: List[TestResult] = []
        seen_files = set()

        # =====================================================================
        # STRATEGY 1: the log outputs a mini-summary for each file it runs
        # This regex links the exact file (e.g., "user_spec.rb") to its duration and failure count
        # =====================================================================

        running_file_pattern = re.compile(
            r"Running\s+(?P<file>.+?_spec\.rb).*?"
            r"Finished in\s+(?P<duration>[\d.]+)\s+seconds.*?"
            r"(?P<examples>\d+)\s+examples?,\s+(?P<failures>\d+)\s+failures?",
            re.DOTALL
        )

        for match in running_file_pattern.finditer(content):
            file_name = match.group("file").split("/")[-1]
            # Prevent duplicate entries for the same spec file
            if file_name in seen_files:
                continue
            seen_files.add(file_name)
            duration_ms = int(float(match.group("duration")) * 1000)
            examples = int(match.group("examples"))
            failures = int(match.group("failures"))

            tests.append(TestResult(
                test_name=file_name,
                status="fail" if failures > 0 else "pass",
                passed_count=examples-failures,
                failed_count=failures,
                duration_ms=duration_ms,
                error=None,
                source=self.supported_formats[0],
                framework=self.framework_name,
                is_aggregated=True,
                file=file_name
            ))
        # =====================================================================
        # STRATEGY 2: OVERALL SUITE SUMMARY: "96 examples, 0 failures"
        # =====================================================================

        summary_pattern = re.search(
            r"(\d+)\s+examples?,\s+(\d+)\s+failures?",content)

        if summary_pattern:
            examples = int(summary_pattern.group(1))
            failures = int(summary_pattern.group(2))

            tests.append(TestResult(
                test_name="__rspec_summary__",
                status="fail" if failures > 0 else "pass",
                passed_count=examples - failures,
                failed_count=failures,
                source=self.supported_formats[0],
                framework=self.framework_name,
                is_aggregated=True
            ))

        # =====================================================================
        #STRATEGY 3: TOTAL RUN DURATION
        # =====================================================================
        time_match = re.search(
            r"Finished in ([\d.]+) seconds",
            content
        )

        if time_match:
            duration_ms = int(float(time_match.group(1)) * 1000)

            tests.append(TestResult(
                test_name="__rspec_run_complete__",
                status="pass",
                duration_ms=duration_ms,
                source=self.supported_formats[0],
                framework=self.framework_name
            ))

        return tests



class MinitestLogsParser(BaseLogParser):
    """Parse Minitest output"""
    
    framework_name = "minitest"
    
    @property
    def supported_formats(self):
        return ["minitest_logs"]
    
    @property
    def priority(self):
        return 50
    

    @property
    def status_map(self) -> dict:
        return {'.': 'pass', 'F': 'fail', 'E': 'error', 'S': 'skip'}
    
    def can_parse(self, content: str, filename: str = "") -> bool:
        strong_indicators = [
            "runs,",
            "assertions,",
            "# Running:",
            "errors,",
            "skips",
        ]

        score = 0

        for indicator in strong_indicators:
            if indicator in content:
                score += 2

        if "runs," in content and "assertions," in content:
            score += 3

        # dot progress output
        if any(c in content for c in [".", "F", "E", "S"]):
            score += 1

        return score >= 3 and ("runs," in content or "# Running:" in content)


    def _parse(self, content: str) -> List[TestResult]:

        tests: List[TestResult] = []

        # =====================================================================
        #PROGRESS DOTS EXTRACTION
        #Minitest prints a single character for every test so we can't get the test *names* from this, counting these dots 
        #gives us a backup metric in case the build crashes right before printing the final summary. 
        #we parse them into stats_from_dots but rely on the summary below to actually append the TestResult
        #because the summary line is much more mathematically reliable).
        # =====================================================================
        progress_section = re.search(r"# Running:(.*?)(?=Finished in)", content, re.DOTALL)
        
        stats_from_dots = {"pass": 0, "fail": 0, "skip": 0, "error": 0}
        if progress_section:
            # In GHA, dots often appear on individual lines or in a block
            # We look for single characters ., F, E, S surrounded by whitespace/newlines
            potential_dots = progress_section.group(1).split()
            for char in potential_dots:
                if char in self.status_map:
                    status = self.status_map[char]
                    stats_from_dots[status] += 1

        # =====================================================================
        # 3. Parse detailed summary line : 7 runs, 11 assertions, 0 failures, 0 errors, 0 skips
        # =====================================================================
        summary_counts = re.search(
            r"(\d+)\s+runs,\s+(\d+)\s+assertions,\s+(\d+)\s+failures,\s+(\d+)\s+errors,\s+(\d+)\s+skips",content)
        
        # =====================================================================
        # 4. Parse duration : Finished in 0.257549s
        # =====================================================================

        duration_match = re.search(r"Finished in ([\d.]+)s", content)
        duration_ms = int(float(duration_match.group(1)) * 1000) if duration_match else None

        if summary_counts:
            runs = int(summary_counts.group(1))
            assertions = int(summary_counts.group(2))
            failures = int(summary_counts.group(3))
            errors = int(summary_counts.group(4))
            skips = int(summary_counts.group(5))
            
            #we mark status as failed if there are failures OR errors
            is_failed = (failures + errors) > 0

            # Add the aggregated summary result
            tests.append(TestResult(
                test_name="__summary__",
                status="fail" if is_failed else "pass",
                duration_ms=duration_ms,
                is_aggregated=True,
                total_count=runs,
                passed_count=runs - failures - errors - skips,
                failed_count=failures + errors,
                skipped_count=skips,
                source=self.supported_formats[0],
                framework=self.framework_name
            ))

        # not yet implemented but will be added to Parse Failure Details
        # if there are failures, minitest prints them between "Finished in" and the summary line
        # will extract failure names and stack traces 
        # to create individual TestResult objects with status="fail".

        return tests




class UnittestLogsParser(BaseLogParser):
    """Parse Python unittest -v console output"""
    
    framework_name = "unittest"
    
    @property
    def supported_formats(self):
        return ["unittest_logs"]
    
    @property
    def priority(self):
        return 50
    

    @property
    def status_map(self) -> dict:
        return {
            "OK": "pass",
            "PASSED": "pass",
            "FAIL": "fail",
            "FAILED": "fail",
            "ERROR": "error",
            "SKIPPED": "skip",
        }
    
    def can_parse(self, content: str, filename: str = "") -> bool:
        strong_indicators = [
            "Ran",                    
            "FAILED",             
            "ERROR",                
            "skipped",               
            "======================================================================",
            "test.",                 
        ]

        score = 0

        for indicator in strong_indicators:
            if indicator in content:
                score += 2

        #unittest test case signature
        if re.search(r"\w+\.\w+\.\w+\(.*\)\s+\.\.\.\s+(ok|FAIL|ERROR|skipped)", content):
            score += 3

        #summary line
        if re.search(r"Ran \d+ tests?", content):
            score += 3

        #status keywords
        if " ok" in content or "FAIL:" in content:
            score += 2

        # dot progress but it is weak signal, shared with other parsers
        if any(c in content for c in [".", "F", "E", "S"]):
            score += 1

        return score >= 4
    
    def _extract_test_name(self, match: re.Match) -> str:
        # Prefer full qualified name (group 2)
        full_qual = match.group(2).strip()
        return full_qual if full_qual else match.group(1).strip()
    
    def _extract_status(self, match: re.Match) -> str:
        # Status is group 3
        return match.group(3).lower()
    
    def _parse(self, content: str) -> List[TestResult]:

        tests: List[TestResult] = []
        seen = set()
        # ------------------------------------------------------------
        #if parallel : [  2/505] test_property passed
        # ------------------------------------------------------------
        parallel_pattern = re.compile(
            r"\[\s*\d+/\d+\]\s+([^\s]+)\s+(passed|skipped|failed|error)",re.IGNORECASE)

        for match in parallel_pattern.finditer(content):
            test_name = match.group(1).strip()
            status_raw = match.group(2).lower()

            if test_name in seen:
                continue
            seen.add(test_name)

            tests.append(TestResult(
                test_name=test_name,
                status=self.status_map.get(status_raw.upper(), status_raw),
                duration_ms=None,
                error=None,
                source=self.supported_formats[0],
                framework=self.framework_name,
                is_aggregated=False
            ))

        # ------------------------------------------------------------
        #unitest classic style: test_xxx (...) ... ok
        # ------------------------------------------------------------
        verbose_pattern = re.compile(
            r"^(.+?)\s+\.\.\.\s+(ok|FAIL|ERROR|skipped)",
            re.MULTILINE
        )

        for match in verbose_pattern.finditer(content):
            test_name = match.group(1).strip()
            status_raw = match.group(2).lower()

            if test_name in seen:
                continue
            seen.add(test_name)

            tests.append(TestResult(
                test_name=test_name,
                status=self.status_map.get(status_raw.upper(), status_raw),
                duration_ms=None,
                error=None,
                source=self.supported_formats[0],
                framework=self.framework_name,
                is_aggregated=False
            ))

        # ------------------------------------------------------------
        #summary : Ran 505 tests in 123.45s
        # ------------------------------------------------------------
        summary = re.search(
            r"Ran\s+(\d+)\s+tests?\s+in\s+([\d.]+)s",content)

        if summary:
            total = int(summary.group(1))
            duration_sec = float(summary.group(2))
            failed = 0
            skipped = 0
            errors = 0

            fail_match = re.search(r"FAILED\s+\(failures=(\d+)", content)
            if fail_match:
                failed = int(fail_match.group(1))

            skip_match = re.search(r"skipped=(\d+)", content)
            if skip_match:
                skipped = int(skip_match.group(1))

            error_match = re.search(r"errors=(\d+)", content)
            if error_match:
                errors = int(error_match.group(1))

            tests.append(TestResult(
                test_name="__summary__",
                status="fail" if failed > 0 or errors > 0 else "pass",
                duration_ms=int(duration_sec * 1000),
                error=None,
                source=self.supported_formats[0],
                framework=self.framework_name,
                passed_count=total - failed - errors - skipped,
                failed_count=failed,
                skipped_count=skipped,
                is_aggregated=True
            ))

        return tests