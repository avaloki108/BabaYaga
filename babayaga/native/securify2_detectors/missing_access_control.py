"""Native missing access control detector based on Securify2's implementation.

Based on: Securify2's access control patterns
Upstream: https://github.com/eth-sri/securify2
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)


class MissingAccessControlDetector(BaseDetector):
    """Detects missing access control on sensitive functions.
    
    This detector identifies state-changing functions that lack proper
    access control mechanisms.
    """
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-securify2-missing-access-control",
            name="Missing Access Control",
            description="Detects state-changing functions without proper access control",
            source_tool="securify2",
            source_version="0.1.0",
            source_detector_id="MissingAccessControl",
            severity=Severity.CRITICAL,
            confidence=0.7,
            category=DetectorCategory.ACCESS_CONTROL,
            references=[
                "https://github.com/eth-sri/securify2",
                "https://swcregistry.io/docs/SWC-105"
            ],
            swc_id="SWC-105",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for missing access control."""
        findings = []
        lines = contract_source.split('\n')
        
        current_function = None
        function_start_line = 0
        function_visibility = None
        function_body = []
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Track function declarations
            func_match = re.search(r'function\s+(\w+)\s*\([^)]*\)\s*(public|external|internal|private)?', line_stripped)
            if func_match:
                # Check previous function if exists
                if current_function and function_visibility in ['public', 'external']:
                    if self._is_state_changing(function_body) and not self._has_access_control(function_body):
                        finding = DetectorFinding(
                            detector_id=self.detector_id,
                            title=f"Missing access control in {current_function}",
                            description=f"Function '{current_function}' at line {function_start_line} is state-changing "
                                       f"but lacks access control checks (e.g., onlyOwner, require(msg.sender == ...)).",
                            severity=self.metadata.severity,
                            confidence=self.metadata.confidence,
                            file_path=file_path,
                            line_number=function_start_line,
                            function_name=current_function,
                            code_snippet=self._extract_code_snippet(contract_source, function_start_line),
                            remediation="Add access control checks to restrict who can call this function. "
                                       "Use modifiers like 'onlyOwner' or require statements like "
                                       "'require(msg.sender == owner, \"Not authorized\");'",
                            references=self.metadata.references,
                            swc_id=self.metadata.swc_id,
                            category=self.metadata.category
                        )
                        findings.append(finding)
                
                # Start tracking new function
                current_function = func_match.group(1)
                function_start_line = line_num
                function_visibility = func_match.group(2) or 'public'  # Default to public
                function_body = []
            
            # Collect function body
            if current_function:
                function_body.append(line_stripped)
                
                # End of function (simple heuristic)
                if line_stripped == '}' and len(function_body) > 1:
                    # Check this function
                    if function_visibility in ['public', 'external']:
                        if self._is_state_changing(function_body) and not self._has_access_control(function_body):
                            finding = DetectorFinding(
                                detector_id=self.detector_id,
                                title=f"Missing access control in {current_function}",
                                description=f"Function '{current_function}' at line {function_start_line} is state-changing "
                                           f"but lacks access control checks.",
                                severity=self.metadata.severity,
                                confidence=self.metadata.confidence,
                                file_path=file_path,
                                line_number=function_start_line,
                                function_name=current_function,
                                code_snippet=self._extract_code_snippet(contract_source, function_start_line),
                                remediation="Add access control checks to restrict who can call this function.",
                                references=self.metadata.references,
                                swc_id=self.metadata.swc_id,
                                category=self.metadata.category
                            )
                            findings.append(finding)
                    
                    current_function = None
                    function_body = []
        
        return findings
    
    def _is_state_changing(self, function_body: List[str]) -> bool:
        """Check if function modifies state."""
        body_text = ' '.join(function_body)
        
        # Check for view/pure modifiers
        if 'view' in body_text or 'pure' in body_text:
            return False
        
        # Check for state modifications
        state_changing_patterns = [
            r'\w+\s*=\s*',  # Assignment
            r'\w+\+\+',  # Increment
            r'\w+--',  # Decrement
            r'\.push\(',  # Array push
            r'\.pop\(',  # Array pop
            r'delete\s+',  # Delete
            r'selfdestruct\s*\(',  # Selfdestruct
            r'\.transfer\(',  # Transfer
            r'\.send\(',  # Send
            r'\.call',  # Call
        ]
        
        for pattern in state_changing_patterns:
            if re.search(pattern, body_text):
                return True
        
        return False
    
    def _has_access_control(self, function_body: List[str]) -> bool:
        """Check if function has access control checks."""
        body_text = ' '.join(function_body)
        
        # Check for common access control patterns
        access_control_patterns = [
            r'onlyOwner',  # Modifier
            r'onlyAdmin',  # Modifier
            r'require\s*\(\s*msg\.sender\s*==',  # Require sender check
            r'if\s*\(\s*msg\.sender\s*!=',  # If sender check
            r'require\s*\(\s*hasRole\(',  # Role-based check
            r'require\s*\(\s*owner\s*==',  # Owner check
            r'_checkOwner\(',  # OpenZeppelin pattern
        ]
        
        for pattern in access_control_patterns:
            if re.search(pattern, body_text):
                return True
        
        return False
