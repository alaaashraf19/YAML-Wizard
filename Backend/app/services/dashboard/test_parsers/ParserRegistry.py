from .BaseTestParser import BaseTestParser
from schemas.dashboard import TestResult

class ParserRegistry:
    """Registry for all available parsers"""

    def __init__(self):
        self._parsers = BaseTestParser.registry
        self._parsers.sort(key=lambda parser: parser().priority)

    def detect(self, content: str, filename: str = "") -> BaseTestParser | None:
        for parser_cls in self._parsers:
            parser = parser_cls()

            if parser.can_parse(content, filename):
                # print(f"[test-parse] Selected parser: {parser.parser_name}", flush=True)
                return parser

        return None

    def parse(self, content: str, filename: str = "") -> list[TestResult]:
        parser = self.detect(content, filename)
        # print(f"[test-parse] Detected parser: {parser.parser_name if parser else 'None'}", flush=True)
        if not parser:
            return []
        return parser.parse(content)