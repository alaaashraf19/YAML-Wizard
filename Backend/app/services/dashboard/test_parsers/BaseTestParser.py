from abc import ABC, abstractmethod
import re
from typing import List
from schemas.dashboard import TestResult
import inspect
import json
import xml.etree.ElementTree as ET

class BaseTestParser(ABC):
    """Abstract base class for all test framework parsers"""
    registry: list["BaseTestParser"] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not inspect.isabstract(cls):
            if cls not in BaseTestParser.registry:
                BaseTestParser.registry.append(cls)

    @property
    @abstractmethod
    def supported_formats(self) -> List[str]:
        pass
    
    @property
    def priority(self) -> int:
        return 100

    @property
    def parser_name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def can_parse(self, content: str, filename: str = "") -> bool:
        """Detect if this parser can handle the content"""
        pass
    
    @abstractmethod
    def parse(self, content: str) -> List[TestResult]:
        pass
    
    @staticmethod
    def normalize_github_logs( content: str) -> str:
        
        """Shared function for GitHub Actions log normalization"""

        #remove github timestamp prefix like: 2026-05-08T17:40:00.7054852Z
        content = re.sub(
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\s+',
            '',
            content,
            flags=re.MULTILINE
        )

        # Remove ANSI color codes
        content = re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', content)

        return content
    
    def _to_ms(self, seconds: float | None) -> int | None:
        if seconds is None:
            return None
        try:
            return int(float(seconds) * 1000)
        except (ValueError, TypeError):
            return None
        
    def _safe_json_load(self, content: str) -> dict | None:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None
        
    def _safe_xml_load(self, content: str):
        try:
            return ET.fromstring(content)
        except ET.ParseError:
            return None