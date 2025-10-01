"""Native unchecked call detector based on Slither's implementation.

Based on: Slither's unchecked-send and unchecked-lowlevel detectors
Upstream: https://github.com/crytic/slither/blob/master/slither/detectors/statements/
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)


class UncheckedCallDetector(BaseDetector):
    """Detects unchecked return values from external calls.
    
    External calls (call, send, delegatecall) return a boolean indicating
    success/failure. Not checking this return value can lead to silent failures.
    
    Based on Slither's unchecked-send and unchecked-lowlevel detectors.
    """
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-unchecked-call",
            name="Unchecked External Call",
            description="Detects external calls whose return value is not checked",
            source_tool="slither",
            source_version="0.10.0",
            source_detector_id="unchecked-lowlevel",
            severity=Severity.MEDIUM,
            confidence=0.8,
            category=DetectorCategory.EXTERNAL_CALLS,
            references=[
                "https://github.com/crytic/slither/wiki/Detector-Documentation#unchecked-low-level-calls",
                "https://swcregistry.io/docs/SWC-104"
            ],
            swc_id="SWC-104",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for unchecked external calls."""
        findings = []
        lines = contract_source.split('\n')
        
        current_function = None
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Track function boundaries
            func_match = re.search(r'function\s+(\w+)', line_stripped)
            if func_match:
                current_function = func_match.group(1)
            
            # Look for unchecked calls
            if self._is_unchecked_call(line_stripped):
                finding = DetectorFinding(
                    detector_id=self.detector_id,
                    title=f"Unchecked external call in {current_function or 'contract'}",
                    description=f"External call at line {line_num} does not check the return value. "
                               f"Low-level calls (call, delegatecall, send) return false on failure "
                               f"instead of reverting. Not checking the return value can lead to "
                               f"silent failures.",
                    severity=self.metadata.severity,
                    confidence=self.metadata.confidence,
                    file_path=file_path,
                    line_number=line_num,
                    function_name=current_function,
                    code_snippet=self._extract_code_snippet(contract_source, line_num),
                    remediation="Check the return value of the call:\n"
                               "  (bool success, ) = addr.call(...);\n"
                               "  require(success, \"Call failed\");\n"
                               "Or use transfer() which automatically reverts on failure.",
                    references=self.metadata.references,
                    swc_id=self.metadata.swc_id,
                    category=self.metadata.category
                )
                findings.append(finding)
        
        return findings
    
    def _is_unchecked_call(self, line: str) -> bool:
        """Check if line contains an unchecked external call."""
        # Pattern for calls that are not checked
        # Look for .call(), .send(), .delegatecall() that are:
        # 1. Not assigned to a variable
        # 2. Not used in a require/assert
        # 3. Not used in an if statement
        
        # First check if there's an external call
        has_call = bool(re.search(r'\.call\s*\(|\.send\s*\(|\.delegatecall\s*\(', line))
        
        if not has_call:
            return False
        
        # Check if the return value is being checked
        is_checked = bool(re.search(
            r'(bool|require|assert|if)\s*.*\.(?:call|send|delegatecall)', 
            line
        ))
        
        # Also check for assignment with parentheses (tuple destructuring)
        is_assigned = bool(re.search(r'\(.*\)\s*=.*\.(?:call|send|delegatecall)', line))
        
        return not (is_checked or is_assigned)
