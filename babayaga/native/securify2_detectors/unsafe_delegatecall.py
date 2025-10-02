"""Native unsafe delegatecall detector based on Securify2's implementation.

Based on: Securify2's delegatecall patterns
Upstream: https://github.com/eth-sri/securify2
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)


class UnsafeDelegatecallDetector(BaseDetector):
    """Detects potentially unsafe delegatecall usage.
    
    This detector identifies delegatecall usage that may be vulnerable
    to attacks, especially when the target address is not properly validated.
    """
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-securify2-unsafe-delegatecall",
            name="Unsafe Delegatecall",
            description="Detects delegatecall to untrusted addresses which can lead to malicious code execution",
            source_tool="securify2",
            source_version="0.1.0",
            source_detector_id="UnsafeDelegatecall",
            severity=Severity.HIGH,
            confidence=0.8,
            category=DetectorCategory.DELEGATECALL,
            references=[
                "https://github.com/eth-sri/securify2",
                "https://swcregistry.io/docs/SWC-112"
            ],
            swc_id="SWC-112",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for unsafe delegatecall vulnerabilities."""
        findings = []
        lines = contract_source.split('\n')
        
        current_function = None
        function_body = []
        function_start_line = 0
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Track function boundaries
            func_match = re.search(r'function\s+(\w+)', line_stripped)
            if func_match:
                current_function = func_match.group(1)
                function_start_line = line_num
                function_body = []
            
            if current_function:
                function_body.append(line_stripped)
            
            # Look for delegatecall usage
            if 'delegatecall' in line_stripped:
                # Check if target is validated
                is_safe = self._has_address_validation(function_body, line_stripped)
                
                severity = Severity.MEDIUM if is_safe else Severity.HIGH
                confidence = 0.6 if is_safe else 0.9
                
                finding = DetectorFinding(
                    detector_id=self.detector_id,
                    title=f"Unsafe delegatecall in {current_function or 'contract'}",
                    description=f"Delegatecall detected at line {line_num}. "
                               f"Delegatecall executes code in the context of the calling contract, "
                               f"allowing the called contract to modify the caller's storage. "
                               f"{'The target address may not be properly validated.' if not is_safe else 'Ensure the target address is trusted.'}",
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=line_num,
                    function_name=current_function,
                    code_snippet=self._extract_code_snippet(contract_source, line_num),
                    remediation="Validate the target address before making delegatecall. "
                               "Use a whitelist of trusted addresses or restrict delegatecall "
                               "to known, audited contracts only. Consider using library calls instead.",
                    references=self.metadata.references,
                    swc_id=self.metadata.swc_id,
                    category=self.metadata.category
                )
                findings.append(finding)
        
        return findings
    
    def _has_address_validation(self, function_body: List[str], delegatecall_line: str) -> bool:
        """Check if the target address is validated before delegatecall."""
        body_text = ' '.join(function_body)
        
        # Extract the target address from delegatecall
        # Pattern: address.delegatecall(...)
        addr_match = re.search(r'(\w+)\.delegatecall', delegatecall_line)
        if not addr_match:
            return False
        
        target_var = addr_match.group(1)
        
        # Check for validation patterns before the delegatecall
        validation_patterns = [
            rf'require\s*\([^)]*{target_var}[^)]*\)',  # require with target
            rf'if\s*\([^)]*{target_var}[^)]*\)',  # if check with target
            rf'{target_var}\s*==\s*\w+',  # equality check
            rf'isWhitelisted\s*\(\s*{target_var}\s*\)',  # whitelist check
            rf'trusted\s*\[\s*{target_var}\s*\]',  # trusted mapping
        ]
        
        for pattern in validation_patterns:
            if re.search(pattern, body_text):
                return True
        
        return False
