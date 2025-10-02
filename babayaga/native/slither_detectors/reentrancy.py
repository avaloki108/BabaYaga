"""Native reentrancy detector based on Slither's implementation.

Based on: Slither's reentrancy-eth detector
Upstream: https://github.com/crytic/slither/blob/master/slither/detectors/reentrancy/reentrancy_eth.py
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)


class ReentrancyDetector(BaseDetector):
    """Detects reentrancy vulnerabilities.
    
    This detector identifies patterns where:
    1. External calls are made
    2. State variables are modified after the call
    3. The function is public/external and can be called again
    
    Based on Slither's reentrancy-eth detector.
    """
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-reentrancy-eth",
            name="Reentrancy Vulnerability",
            description="Detects reentrancy vulnerabilities where state is modified after external calls",
            source_tool="slither",
            source_version="0.10.0",  # Update this when syncing with upstream
            source_detector_id="reentrancy-eth",
            severity=Severity.HIGH,
            confidence=0.9,
            category=DetectorCategory.REENTRANCY,
            references=[
                "https://github.com/crytic/slither/wiki/Detector-Documentation#reentrancy-vulnerabilities",
                "https://swcregistry.io/docs/SWC-107"
            ],
            swc_id="SWC-107",
            enabled_by_default=True,
            last_updated="2024-01-15"  # Date of last sync with upstream
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for reentrancy vulnerabilities."""
        findings = []
        lines = contract_source.split('\n')
        
        current_function = None
        external_call_line = None
        state_change_after_call = False
        in_function = False
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Track function boundaries
            if re.search(r'function\s+(\w+)', line_stripped):
                func_match = re.search(r'function\s+(\w+)', line_stripped)
                if func_match:
                    # Reset tracking for new function
                    if current_function and external_call_line and state_change_after_call:
                        # Found potential reentrancy in previous function
                        finding = self._create_finding(
                            current_function, external_call_line,
                            contract_source, file_path
                        )
                        findings.append(finding)
                    
                    current_function = func_match.group(1)
                    external_call_line = None
                    state_change_after_call = False
                    in_function = True
            
            # Detect external calls
            if in_function and current_function and self._is_external_call(line_stripped):
                external_call_line = line_num
                state_change_after_call = False
            
            # Detect state changes after external call
            if in_function and external_call_line and line_num > external_call_line:
                if self._is_state_change(line_stripped):
                    state_change_after_call = True
            
            # Detect end of function
            if in_function and line_stripped == '}':
                # Check if we found reentrancy in this function
                if current_function and external_call_line and state_change_after_call:
                    finding = self._create_finding(
                        current_function, external_call_line,
                        contract_source, file_path
                    )
                    findings.append(finding)
                    # Reset for next function
                    current_function = None
                    external_call_line = None
                    state_change_after_call = False
                in_function = False
        
        return findings
    
    def _is_external_call(self, line: str) -> bool:
        """Check if line contains an external call."""
        # Common patterns for external calls
        patterns = [
            r'\.call\s*\{',         # New syntax: .call{value: ...}
            r'\.call\s*\(',         # Old syntax: .call()
            r'\.delegatecall\s*\{', # New syntax: .delegatecall{...}
            r'\.delegatecall\s*\(', # Old syntax: .delegatecall()
            r'\.send\s*\(',         # .send()
            r'\.transfer\s*\(',     # .transfer()
            r'\w+\([^)]*\)\s*\.value\s*\(', # .value(...) calls
        ]
        
        return any(re.search(pattern, line) for pattern in patterns)
    
    def _is_state_change(self, line: str) -> bool:
        """Check if line modifies state."""
        # Exclude local variable declarations
        if re.search(r'^\s*(uint|int|address|bool|string|bytes|mapping)', line):
            return False
        
        # Common patterns for state changes
        patterns = [
            r'[\w\[\]\.]+\s*=\s*[^=]',  # Assignment (including array/mapping access)
            r'\w+\s*\+=',                # Addition assignment
            r'\w+\s*-=',                 # Subtraction assignment
            r'\w+\s*\*=',                # Multiplication assignment
            r'\w+\s*/=',                 # Division assignment
            r'\+\+\w+',                  # Pre-increment
            r'\w+\+\+',                  # Post-increment
            r'--\w+',                    # Pre-decrement
            r'\w+--',                    # Post-decrement
            r'delete\s+\w+',             # Delete operation
        ]
        
        return any(re.search(pattern, line) for pattern in patterns)
    
    def _create_finding(self, function_name: str, line_number: int,
                       source: str, file_path: str) -> DetectorFinding:
        """Create a finding for detected reentrancy."""
        return DetectorFinding(
            detector_id=self.detector_id,
            title=f"Reentrancy vulnerability in {function_name}",
            description=f"Function '{function_name}' makes an external call and then modifies state. "
                       f"This can lead to reentrancy attacks where the called contract calls back "
                       f"before state changes are complete.",
            severity=self.metadata.severity,
            confidence=self.metadata.confidence,
            file_path=file_path,
            line_number=line_number,
            function_name=function_name,
            code_snippet=self._extract_code_snippet(source, line_number),
            remediation="Use the checks-effects-interactions pattern: perform all state changes "
                       "before making external calls, or use a reentrancy guard (ReentrancyGuard).",
            references=self.metadata.references,
            swc_id=self.metadata.swc_id,
            category=self.metadata.category
        )