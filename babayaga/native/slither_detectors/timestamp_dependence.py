"""Native timestamp dependence detector based on Slither's implementation.

Based on: Slither's timestamp detector
Upstream: https://github.com/crytic/slither/blob/master/slither/detectors/statements/timestamp.py
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)


class TimestampDependenceDetector(BaseDetector):
    """Detects dangerous dependence on block.timestamp or now.
    
    block.timestamp and now can be manipulated by miners within certain bounds
    and should not be used for critical logic or random number generation.
    
    Based on Slither's timestamp detector.
    """
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-timestamp-dependence",
            name="Timestamp Dependence",
            description="Detects dangerous dependence on block.timestamp or now",
            source_tool="slither",
            source_version="0.10.0",
            source_detector_id="timestamp",
            severity=Severity.LOW,
            confidence=0.75,
            category=DetectorCategory.TIMESTAMP,
            references=[
                "https://github.com/crytic/slither/wiki/Detector-Documentation#block-timestamp",
                "https://swcregistry.io/docs/SWC-116"
            ],
            swc_id="SWC-116",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for timestamp dependence."""
        findings = []
        lines = contract_source.split('\n')
        
        current_function = None
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Track function boundaries
            func_match = re.search(r'function\s+(\w+)', line_stripped)
            if func_match:
                current_function = func_match.group(1)
            
            # Look for timestamp usage in dangerous contexts
            if self._is_dangerous_timestamp_usage(line_stripped):
                # Determine severity based on context
                severity = self._assess_severity(line_stripped)
                
                finding = DetectorFinding(
                    detector_id=self.detector_id,
                    title=f"Timestamp dependence in {current_function or 'contract'}",
                    description=f"Dangerous use of block.timestamp at line {line_num}. "
                               f"block.timestamp (or 'now') can be manipulated by miners within "
                               f"certain bounds (~15 seconds). It should not be used for critical "
                               f"logic, access control, or random number generation.",
                    severity=severity,
                    confidence=self.metadata.confidence,
                    file_path=file_path,
                    line_number=line_num,
                    function_name=current_function,
                    code_snippet=self._extract_code_snippet(contract_source, line_num),
                    remediation="Avoid using block.timestamp for:\n"
                               "  - Access control decisions\n"
                               "  - Random number generation\n"
                               "  - Critical state changes\n"
                               "Consider using block.number for relative time measurements "
                               "or oracle solutions for precise timing.",
                    references=self.metadata.references,
                    swc_id=self.metadata.swc_id,
                    category=self.metadata.category
                )
                findings.append(finding)
        
        return findings
    
    def _is_dangerous_timestamp_usage(self, line: str) -> bool:
        """Check if line contains dangerous timestamp usage."""
        # Patterns for timestamp usage
        timestamp_patterns = [
            r'block\.timestamp',
            r'\bnow\b',
        ]
        
        # Check if timestamp is used in potentially dangerous ways
        has_timestamp = any(re.search(pattern, line) for pattern in timestamp_patterns)
        
        if not has_timestamp:
            return False
        
        # Dangerous contexts
        dangerous_contexts = [
            r'(==|!=|<=|>=|<|>)',          # Comparisons
            r'require\s*\(',                # Require statements
            r'assert\s*\(',                 # Assert statements
            r'if\s*\(',                     # If conditions
            r'%',                           # Modulo (often for randomness)
            r'\*',                          # Multiplication (often for randomness)
            r'\+',                          # Addition
            r'-',                           # Subtraction
        ]
        
        return any(re.search(pattern, line) for pattern in dangerous_contexts)
    
    def _assess_severity(self, line: str) -> Severity:
        """Assess severity based on usage context."""
        # High severity if used in access control or state changes
        if re.search(r'require\s*\(.*block\.timestamp|require\s*\(.*\bnow\b', line):
            return Severity.MEDIUM
        
        # High severity if used for randomness
        if re.search(r'(block\.timestamp|now).*%', line):
            return Severity.MEDIUM
        
        # Medium severity for other comparisons
        if re.search(r'(==|!=|<=|>=)', line):
            return Severity.LOW
        
        # Low severity for simple usage
        return Severity.LOW
