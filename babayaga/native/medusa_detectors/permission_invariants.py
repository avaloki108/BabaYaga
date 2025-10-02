"""Permission invariant detector for smart contracts.

Detects violations of access control and permission invariants such as:
- Missing access control on privileged functions
- Improper owner/admin checks
- Unauthorized state modifications

Based on: Medusa's permission invariant checking
Upstream: https://github.com/crytic/medusa
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)
from .symbolic_engine import SymbolicExecutionEngine
from .invariant_checker import InvariantChecker, InvariantType


class PermissionInvariantsDetector(BaseDetector):
    """Detects violations of permission and access control invariants.
    
    This detector uses symbolic execution to verify that:
    - Critical functions have proper access control
    - Owner/admin privileges are properly checked
    - State modifications are authorized
    """
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-medusa-permissions",
            name="Permission Invariants",
            description="Detects missing or improper access control using symbolic analysis",
            source_tool="medusa",
            source_version="0.3.0",
            source_detector_id="permission-invariants",
            severity=Severity.HIGH,
            confidence=0.8,
            category=DetectorCategory.ACCESS_CONTROL,
            references=[
                "https://github.com/crytic/medusa",
                "https://swcregistry.io/docs/SWC-105"
            ],
            swc_id="SWC-105",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for permission invariant violations."""
        findings = []
        
        # Use invariant checker
        checker = InvariantChecker()
        violations = checker.check_invariants(contract_source, InvariantType.PERMISSION)
        
        # Convert violations to findings
        for violation in violations:
            finding = DetectorFinding(
                detector_id=self.detector_id,
                title=f"Permission Invariant Violation: {violation.description}",
                description=violation.description,
                severity=self.metadata.severity,
                confidence=self.metadata.confidence,
                file_path=file_path,
                line_number=violation.line_number,
                function_name=violation.function_name,
                remediation=violation.remediation or self._get_remediation(),
                references=self.metadata.references,
                swc_id=self.metadata.swc_id,
                category=self.metadata.category
            )
            findings.append(finding)
        
        # Additional pattern-based checks
        pattern_findings = await self._check_patterns(contract_source, file_path)
        findings.extend(pattern_findings)
        
        return findings
    
    async def _check_patterns(self, source: str, file_path: str) -> List[DetectorFinding]:
        """Check for common permission violation patterns."""
        findings = []
        lines = source.split('\n')
        
        # Critical keywords that suggest privileged operations
        critical_keywords = ['owner', 'admin', 'authorized', 'privileged', 'withdraw',
                            'selfdestruct', 'delegatecall', 'destroy', 'pause']
        
        current_function = None
        current_function_line = None
        has_access_control = False
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Track function boundaries
            func_match = re.search(r'function\s+(\w+)', line_stripped)
            if func_match:
                # Check if previous function had issues
                if current_function and not has_access_control:
                    if any(keyword in current_function.lower() for keyword in critical_keywords):
                        finding = DetectorFinding(
                            detector_id=self.detector_id,
                            title=f"Missing Access Control in Privileged Function",
                            description=f"Function '{current_function}' appears to be privileged but lacks access control",
                            severity=Severity.HIGH,
                            confidence=0.7,
                            file_path=file_path,
                            line_number=current_function_line,
                            function_name=current_function,
                            code_snippet=self._extract_code_snippet(source, current_function_line),
                            remediation=self._get_remediation(),
                            references=self.metadata.references,
                            swc_id=self.metadata.swc_id,
                            category=self.metadata.category
                        )
                        findings.append(finding)
                
                # Reset for new function
                current_function = func_match.group(1)
                current_function_line = line_num
                has_access_control = False
                
                # Check if function is public/external
                is_public = 'public' in line_stripped or 'external' in line_stripped
                
                if is_public:
                    # Check for view/pure (these don't modify state)
                    if 'view' in line_stripped or 'pure' in line_stripped:
                        has_access_control = True  # Safe, doesn't modify state
            
            # Check for access control patterns
            if current_function:
                # Look for require with msg.sender or owner checks
                if 'require' in line_stripped:
                    if 'msg.sender' in line_stripped or 'owner' in line_stripped:
                        has_access_control = True
                
                # Look for modifier usage
                if re.search(r'(onlyOwner|onlyAdmin|authorized|requireAuth)', line_stripped):
                    has_access_control = True
                
                # Check for critical operations without access control
                if any(keyword in line_stripped.lower() for keyword in ['selfdestruct', 'delegatecall']):
                    if not has_access_control:
                        finding = DetectorFinding(
                            detector_id=self.detector_id,
                            title="Critical Operation Without Access Control",
                            description=f"Critical operation in '{current_function}' lacks access control",
                            severity=Severity.CRITICAL,
                            confidence=0.9,
                            file_path=file_path,
                            line_number=line_num,
                            function_name=current_function,
                            code_snippet=self._extract_code_snippet(source, line_num),
                            remediation="Add access control checks before critical operations",
                            references=self.metadata.references,
                            swc_id=self.metadata.swc_id,
                            category=self.metadata.category
                        )
                        findings.append(finding)
        
        return findings
    
    def _get_remediation(self) -> str:
        """Get remediation advice."""
        return ("Add proper access control to privileged functions. Use modifiers like 'onlyOwner', "
                "'onlyAdmin', or 'require(msg.sender == owner)' to restrict access. "
                "Consider using OpenZeppelin's Ownable or AccessControl contracts for robust "
                "access control management.")
