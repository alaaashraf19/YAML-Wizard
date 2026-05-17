from ..BaseTestParser import BaseTestParser
from schemas.dashboard import TestResult
from typing import List
import xml.etree.ElementTree as ET


class BaseTrxXMLParser(BaseTestParser):
    """Base class for TRX (Visual Studio Test Results) XML format"""
    framework_name = "unknown"
    
    @property
    def trx_namespace(self) -> dict:
        """TRX XML namespace"""
        return {'trx': 'http://microsoft.com/schemas/VisualStudio/TeamTest/2010'}
    
    @property
    def status_map(self) -> dict:
        """Map TRX outcome values to standard status"""
        return {
            'Passed': 'pass',
            'Failed': 'fail',
            'NotExecuted': 'skip',
            'Inconclusive': 'skip',
        }
    
    def _parse_trx_duration(self, duration_str: str) -> int | None:
        """Parse TRX duration format: 00:00:01.234 (HH:MM:SS.ms)
        Falls back to plain seconds if no colons found"""
        
        if not duration_str:
            return None
        
        try:
            if ':' in duration_str:
                # Format: HH:MM:SS.ms - extract seconds part
                parts = duration_str.split(':')
                seconds = float(parts[-1])  # Get last part (SS.ms)
                return self._to_ms(seconds)
            else:
                # Fallback: treat as plain seconds
                return self._to_ms(float(duration_str))
        except (ValueError, TypeError, IndexError):
            return None
    
    def _extract_error_message(self, result_element: ET.Element) -> str | None:
        """Extract error message from TRX result element"""
        ns = self.trx_namespace
        
        output = result_element.find('.//trx:Output', ns) or result_element.find('.//Output')
        if output is None:
            return None
        
        #try with namespace first, then without, because some TRX files omit namespaces
        stderr = output.find('trx:ErrorInfo/trx:Message', ns) or output.find('ErrorInfo/Message')
        
        return stderr.text if stderr is not None else None
    
    def parse(self, content: str) -> List[TestResult]:
        """Parse TRX XML content"""
        content = self._normalize_github_logs(content)
        root = self._safe_xml_load(content)
        
        if root is None:
            return []
        
        tests: List[TestResult] = []
        
        for result in root.findall('.//trx:UnitTestResult', self.trx_namespace) or root.findall('.//UnitTestResult'):
            test_name = result.get('testName', '')
            outcome = result.get('outcome', 'Unknown')
            duration_str = result.get('duration', '0')
            
            duration_ms = self._parse_trx_duration(duration_str)
            
            error_msg = self._extract_error_message(result)
            
            tests.append(TestResult(
                test_name=test_name,
                status=self.status_map.get(outcome, 'unknown'),
                duration_ms=duration_ms,
                error=error_msg,
                source=self.supported_formats[0],
                framework=self.framework_name
            ))
        
        return tests