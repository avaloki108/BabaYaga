"""Native timestamp dependence detector based on Securify2's implementation.

Based on: Securify2's timestamp dependence patterns
Upstream: https://github.com/eth-sri/securify2
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)


class TimestampDependenceDetector(BaseDetector):
    """Detects reliance on block.timestamp for critical logic.
    
    This detector identifies usage of block.timestamp or 'now' in
    conditionals or critical operations that could be manipulated by miners.
    """
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-securify2-timestamp-dependence",
            name="Timestamp Dependence",
            description="Detects reliance on block.timestamp which can be manipulated by miners",
            source_tool="securify2",
            source_version="0.1.0",
            source_detector_id="TimestampDependence",
            severity=Severity.MEDIUM,
            confidence=0.8,
            category=DetectorCategory.TIMESTAMP,
            references=[
                "https://github.com/eth-sri/securify2",
                "https://swcregistry.io/docs/SWC-116"
            ],
            swc_id="SWC-116",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for timestamp dependence vulnerabilities."""
        findings = []
        lines = contract_source.split('\n')
        
        current_function = None
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Track function boundaries
            func_match = re.search(r'function\s+(\w+)', line_stripped)
            if func_match:
                current_function = func_match.group(1)
            
            # Look for timestamp usage in conditionals or critical operations
            if self._uses_timestamp(line_stripped):
                # Determine severity based on context
                severity = self.metadata.severity
                confidence = self.metadata.confidence
                
                # Higher severity if used in require/if/while statements
                if any(keyword in line_stripped for keyword in ['require', 'if', 'while', 'for']):
                    severity = Severity.HIGH
                    confidence = 0.9
                
                finding = DetectorFinding(
                    detector_id=self.detector_id,
                    title=f"Timestamp dependence in {current_function or 'contract'}",
                    description=f"Block timestamp usage detected at line {line_num}. "
                               f"Miners can manipulate timestamps within a ~15 second window, "
                               f"which could affect contract logic.",
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=line_num,
                    function_name=current_function,
                    code_snippet=self._extract_code_snippet(contract_source, line_num),
                    remediation="Avoid relying on block.timestamp for critical logic. "
                               "If you need time-based logic, consider using block numbers instead, "
                               "or ensure that ~15 second timestamp manipulation doesn't affect security.",
                    references=self.metadata.references,
                    swc_id=self.metadata.swc_id,
                    category=self.metadata.category
                )
                findings.append(finding)
        
        return findings
    
    def _uses_timestamp(self, line: str) -> bool:
        """Check if line uses block.timestamp or now."""
        # Look for block.timestamp or 'now' keyword
        timestamp_patterns = [
            r'block\.timestamp',
            r'\bnow\b',  # 'now' is deprecated but still in use
        ]
        
        for pattern in timestamp_patterns:
            if re.search(pattern, line):
                return True
        
        return False
