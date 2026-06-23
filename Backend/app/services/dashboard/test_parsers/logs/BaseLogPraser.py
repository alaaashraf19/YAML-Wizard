from abc import abstractmethod
from typing import List, Set
import re
from ..BaseTestParser import BaseTestParser
from schemas.dashboard import TestResult
class BaseLogParser(BaseTestParser):
    """Base class for all log-based parsers"""
    

    
    @property
    @abstractmethod
    def status_map(self) -> dict:
        """Return mapping of log status strings to standard format"""
        pass
    
    def parse(self, content: str) -> List[TestResult]:
        content = self.normalize_github_logs(content)
        return self._parse(content)

    @abstractmethod
    def _parse(self, content: str) -> List[TestResult]:
        pass
    
    def _extract_test_name(self, match: re.Match) -> str:
        """Override to customize test name extraction"""
        return match.group(1) if match.lastindex >= 1 else ""
    
    def _extract_status(self, match: re.Match) -> str:
        """Override to customize status extraction"""
        # Most logs have status in the last group
        return match.group(match.lastindex) if match.lastindex else ""
    
    def _extract_duration(self, match: re.Match) -> int | None:
        """Override to customize duration extraction"""
        return None
    
    def _extract_error(self, match: re.Match) -> str | None:
        """Override to customize error extraction"""
        return None