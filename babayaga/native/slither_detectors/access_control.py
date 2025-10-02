"""Native access control detector based on Slither's implementation.

Based on: Slither's access control detectors
Upstream: https://github.com/crytic/slither/blob/master/slither/detectors/functions/
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)


class AccessControlDetector(BaseDetector):
    """Detects missing or weak access control in critical functions.
    
    Critical functions (that modify state, transfer funds, or change ownership)
    should have proper access control modifiers.
    
    Based on Slither's unprotected functions detectors.
    """
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-access-control",
            name="Missing Access Control",
            description="Detects functions with missing or weak access control",
            source_tool="slither",
            source_version="0.10.0",
            source_detector_id="unprotected-upgrade",
            severity=Severity.HIGH,
            confidence=0.7,
            category=DetectorCategory.ACCESS_CONTROL,
            references=[
                "https://github.com/crytic/slither/wiki/Detector-Documentation#unprotected-upgradeable-contract",
                "https://swcregistry.io/docs/SWC-106"
            ],
            swc_id="SWC-106",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for access control issues."""
        findings = []
        lines = contract_source.split('\n')
        
        current_function = None
        current_function_line = None
        function_visibility = None
        function_modifiers = []
        function_body_started = False
        has_critical_operation = False
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Track function boundaries
            func_match = re.search(r'function\s+(\w+)\s*\([^)]*\)\s*(public|external|private|internal)?([^{]*)', line_stripped)
            if func_match:
                # Save previous function if it was critical and unprotected
                if (current_function and has_critical_operation and 
                    function_visibility in ['public', 'external'] and
                    not self._has_access_control(function_modifiers)):
                    
                    finding = self._create_finding(
                        current_function, current_function_line,
                        contract_source, file_path
                    )
                    findings.append(finding)
                
                # Start tracking new function
                current_function = func_match.group(1)
                current_function_line = line_num
                function_visibility = func_match.group(2) or 'public'  # Default is public
                function_modifiers = self._extract_modifiers(func_match.group(3))
                function_body_started = '{' in line
                has_critical_operation = False
            
            elif current_function:
                if not function_body_started:
                    function_body_started = '{' in line
                    # Continue tracking modifiers
                    if not function_body_started:
                        function_modifiers.extend(self._extract_modifiers(line_stripped))
                
                # Check for critical operations in function body
                if function_body_started and self._is_critical_operation(line_stripped):
                    has_critical_operation = True
            
            # Check for end of function
            if '}' in line and current_function:
                # Check if this function needs to be reported
                if (has_critical_operation and 
                    function_visibility in ['public', 'external'] and
                    not self._has_access_control(function_modifiers)):
                    
                    finding = self._create_finding(
                        current_function, current_function_line,
                        contract_source, file_path
                    )
                    findings.append(finding)
                
                # Reset for next function
                current_function = None
                has_critical_operation = False
        
        return findings
    
    def _extract_modifiers(self, text: str) -> List[str]:
        """Extract modifiers from function declaration."""
        modifiers = []
        # Common modifier patterns
        modifier_pattern = r'\b(onlyOwner|onlyRole|onlyAdmin|auth|authorized|restricted)\w*\b'
        matches = re.findall(modifier_pattern, text, re.IGNORECASE)
        modifiers.extend(matches)
        return modifiers
    
    def _has_access_control(self, modifiers: List[str]) -> bool:
        """Check if function has access control modifiers."""
        if not modifiers:
            return False
        
        # Common access control patterns
        access_patterns = [
            'only', 'auth', 'restrict', 'require', 'check', 'guard'
        ]
        
        return any(
            any(pattern in modifier.lower() for pattern in access_patterns)
            for modifier in modifiers
        )
    
    def _is_critical_operation(self, line: str) -> bool:
        """Check if line contains critical operations that need protection."""
        critical_patterns = [
            r'selfdestruct\s*\(',           # Contract destruction
            r'delegatecall\s*\(',           # Delegatecall
            r'\.call\s*\{.*value',          # Ether transfer via call
            r'\.transfer\s*\(',             # Ether transfer
            r'\.send\s*\(',                 # Ether send
            r'owner\s*=',                   # Owner change
            r'admin\s*=',                   # Admin change
            r'_setupRole\s*\(',             # Role setup
            r'grantRole\s*\(',              # Grant role
            r'transferOwnership\s*\(',      # Transfer ownership
            r'renounceOwnership\s*\(',      # Renounce ownership
            r'upgradeTo\s*\(',              # Contract upgrade
            r'pause\s*\(',                  # Pause contract
            r'unpause\s*\(',                # Unpause contract
        ]
        
        return any(re.search(pattern, line, re.IGNORECASE) for pattern in critical_patterns)
    
    def _create_finding(self, function_name: str, line_number: int,
                       source: str, file_path: str) -> DetectorFinding:
        """Create a finding for unprotected critical function."""
        return DetectorFinding(
            detector_id=self.detector_id,
            title=f"Missing access control in {function_name}",
            description=f"Function '{function_name}' at line {line_number} performs critical "
                       f"operations but lacks proper access control. Public or external functions "
                       f"that modify state, transfer funds, or change contract ownership should "
                       f"have access control modifiers (e.g., onlyOwner, onlyRole).",
            severity=self.metadata.severity,
            confidence=self.metadata.confidence,
            file_path=file_path,
            line_number=line_number,
            function_name=function_name,
            code_snippet=self._extract_code_snippet(source, line_number),
            remediation="Add appropriate access control:\n"
                       "  - Use modifiers like 'onlyOwner' or 'onlyRole'\n"
                       "  - Add 'require' statements to check msg.sender\n"
                       "  - Consider using OpenZeppelin's Ownable or AccessControl\n"
                       "Example: function criticalOp() public onlyOwner { ... }",
            references=self.metadata.references,
            swc_id=self.metadata.swc_id,
            category=self.metadata.category
        )
