"""Native unprotected selfdestruct detector based on Securify2's implementation.

Based on: Securify2's selfdestruct patterns
Upstream: https://github.com/eth-sri/securify2
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)


class UnprotectedSelfdestructDetector(BaseDetector):
    """Detects unprotected selfdestruct calls.
    
    This detector identifies selfdestruct calls that lack proper
    access control, which could allow anyone to destroy the contract.
    """
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-securify2-unprotected-selfdestruct",
            name="Unprotected Selfdestruct",
            description="Detects selfdestruct calls without proper access control",
            source_tool="securify2",
            source_version="0.1.0",
            source_detector_id="UnprotectedSelfdestruct",
            severity=Severity.CRITICAL,
            confidence=0.9,
            category=DetectorCategory.SELFDESTRUCT,
            references=[
                "https://github.com/eth-sri/securify2",
                "https://swcregistry.io/docs/SWC-106"
            ],
            swc_id="SWC-106",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for unprotected selfdestruct vulnerabilities."""
        findings = []
        lines = contract_source.split('\n')
        
        current_function = None
        function_body = []
        function_start_line = 0
        function_visibility = None
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Track function declarations
            func_match = re.search(r'function\s+(\w+)\s*\([^)]*\)\s*(public|external|internal|private)?', line_stripped)
            if func_match:
                current_function = func_match.group(1)
                function_start_line = line_num
                function_visibility = func_match.group(2) or 'public'
                function_body = []
            
            if current_function:
                function_body.append(line_stripped)
            
            # Look for selfdestruct usage
            if self._has_selfdestruct(line_stripped):
                # Check if function has access control
                has_protection = self._has_access_control(function_body)
                
                # Only report if public/external without protection
                if function_visibility in ['public', 'external'] and not has_protection:
                    finding = DetectorFinding(
                        detector_id=self.detector_id,
                        title=f"Unprotected selfdestruct in {current_function or 'contract'}",
                        description=f"Selfdestruct call at line {line_num} is not protected by access control. "
                                   f"Anyone can call this function and destroy the contract, "
                                   f"causing loss of funds and functionality.",
                        severity=self.metadata.severity,
                        confidence=self.metadata.confidence,
                        file_path=file_path,
                        line_number=line_num,
                        function_name=current_function,
                        code_snippet=self._extract_code_snippet(contract_source, line_num),
                        remediation="Restrict selfdestruct to authorized addresses only. "
                                   "Use modifiers like 'onlyOwner' or require statements: "
                                   "'require(msg.sender == owner, \"Not authorized\");'",
                        references=self.metadata.references,
                        swc_id=self.metadata.swc_id,
                        category=self.metadata.category
                    )
                    findings.append(finding)
        
        return findings
    
    def _has_selfdestruct(self, line: str) -> bool:
        """Check if line contains selfdestruct call."""
        return bool(re.search(r'\bselfdestruct\s*\(', line))
    
    def _has_access_control(self, function_body: List[str]) -> bool:
        """Check if function has access control checks."""
        body_text = ' '.join(function_body)
        
        # Check for common access control patterns
        access_control_patterns = [
            r'onlyOwner',
            r'onlyAdmin',
            r'require\s*\(\s*msg\.sender\s*==',
            r'if\s*\(\s*msg\.sender\s*!=',
            r'require\s*\(\s*hasRole\(',
            r'require\s*\(\s*owner\s*==',
            r'_checkOwner\(',
        ]
        
        for pattern in access_control_patterns:
            if re.search(pattern, body_text):
                return True
        
        return False
