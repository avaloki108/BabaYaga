"""Native tx.origin detector based on Slither's implementation.

Based on: Slither's tx-origin detector
Upstream: https://github.com/crytic/slither/blob/master/slither/detectors/statements/tx_origin.py
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)


class TxOriginDetector(BaseDetector):
    """Detects dangerous usage of tx.origin for authorization.
    
    tx.origin should not be used for authorization as it can be
    exploited through phishing attacks.
    
    Based on Slither's tx-origin detector.
    """
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-tx-origin",
            name="Dangerous tx.origin Usage",
            description="Detects usage of tx.origin for authorization checks",
            source_tool="slither",
            source_version="0.10.0",
            source_detector_id="tx-origin",
            severity=Severity.MEDIUM,
            confidence=0.85,
            category=DetectorCategory.ACCESS_CONTROL,
            references=[
                "https://github.com/crytic/slither/wiki/Detector-Documentation#dangerous-usage-of-txorigin",
                "https://swcregistry.io/docs/SWC-115"
            ],
            swc_id="SWC-115",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for tx.origin usage."""
        findings = []
        lines = contract_source.split('\n')
        
        current_function = None
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Track function boundaries
            func_match = re.search(r'function\s+(\w+)', line_stripped)
            if func_match:
                current_function = func_match.group(1)
            
            # Look for tx.origin usage in authorization contexts
            if self._is_tx_origin_auth(line_stripped):
                finding = DetectorFinding(
                    detector_id=self.detector_id,
                    title=f"Dangerous tx.origin usage in {current_function or 'contract'}",
                    description=f"Use of tx.origin for authorization at line {line_num}. "
                               f"tx.origin should not be used for authorization as it represents "
                               f"the original sender of the transaction, not the immediate caller. "
                               f"This can be exploited through phishing attacks.",
                    severity=self.metadata.severity,
                    confidence=self.metadata.confidence,
                    file_path=file_path,
                    line_number=line_num,
                    function_name=current_function,
                    code_snippet=self._extract_code_snippet(contract_source, line_num),
                    remediation="Replace tx.origin with msg.sender for authorization checks. "
                               "msg.sender represents the immediate caller and is safe for authorization.",
                    references=self.metadata.references,
                    swc_id=self.metadata.swc_id,
                    category=self.metadata.category
                )
                findings.append(finding)
        
        return findings
    
    def _is_tx_origin_auth(self, line: str) -> bool:
        """Check if line uses tx.origin for authorization."""
        # Pattern for tx.origin used in comparisons (likely authorization)
        patterns = [
            r'tx\.origin\s*==',
            r'tx\.origin\s*!=',
            r'require\s*\([^)]*tx\.origin',
            r'assert\s*\([^)]*tx\.origin',
            r'if\s*\([^)]*tx\.origin',
        ]
        
        return any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns)
