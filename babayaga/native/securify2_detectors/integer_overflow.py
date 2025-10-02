"""Native integer overflow detector based on Securify2's implementation.

Based on: Securify2's arithmetic overflow/underflow patterns
Upstream: https://github.com/eth-sri/securify2
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)


class IntegerOverflowDetector(BaseDetector):
    """Detects potential integer overflow/underflow vulnerabilities.
    
    This detector identifies arithmetic operations that may result in
    overflow or underflow without proper checks (pre-Solidity 0.8.0).
    """
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-securify2-integer-overflow",
            name="Integer Overflow/Underflow",
            description="Detects unchecked arithmetic operations that may overflow or underflow",
            source_tool="securify2",
            source_version="0.1.0",
            source_detector_id="IntegerOverflow",
            severity=Severity.HIGH,
            confidence=0.8,
            category=DetectorCategory.ARITHMETIC,
            references=[
                "https://github.com/eth-sri/securify2",
                "https://swcregistry.io/docs/SWC-101"
            ],
            swc_id="SWC-101",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for integer overflow/underflow vulnerabilities."""
        findings = []
        lines = contract_source.split('\n')
        
        # Check Solidity version (0.8.0+ has built-in overflow checks)
        solidity_version = self._extract_solidity_version(contract_source)
        if solidity_version and self._is_safe_version(solidity_version):
            return findings  # Safe version with automatic checks
        
        current_function = None
        in_unchecked_block = False
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Track function boundaries
            func_match = re.search(r'function\s+(\w+)', line_stripped)
            if func_match:
                current_function = func_match.group(1)
            
            # Track unchecked blocks (Solidity 0.8.0+)
            if 'unchecked' in line_stripped and '{' in line_stripped:
                in_unchecked_block = True
            if in_unchecked_block and '}' in line_stripped:
                in_unchecked_block = False
            
            # Look for arithmetic operations
            if self._has_arithmetic_operation(line_stripped):
                # Skip if in unchecked block (intentional)
                if in_unchecked_block:
                    continue
                
                # Skip if using SafeMath
                if 'SafeMath' in line_stripped or '.add(' in line_stripped or '.sub(' in line_stripped or '.mul(' in line_stripped:
                    continue
                
                finding = DetectorFinding(
                    detector_id=self.detector_id,
                    title=f"Potential integer overflow/underflow in {current_function or 'contract'}",
                    description=f"Arithmetic operation at line {line_num} may overflow or underflow. "
                               f"Consider using SafeMath library (pre-0.8.0) or explicit overflow checks.",
                    severity=self.metadata.severity,
                    confidence=self.metadata.confidence,
                    file_path=file_path,
                    line_number=line_num,
                    function_name=current_function,
                    code_snippet=self._extract_code_snippet(contract_source, line_num),
                    remediation="Use SafeMath library for arithmetic operations (Solidity <0.8.0) "
                               "or upgrade to Solidity 0.8.0+ which has built-in overflow checks. "
                               "For intentional overflow, use 'unchecked' blocks.",
                    references=self.metadata.references,
                    swc_id=self.metadata.swc_id,
                    category=self.metadata.category
                )
                findings.append(finding)
        
        return findings
    
    def _extract_solidity_version(self, source: str) -> Optional[str]:
        """Extract Solidity version from pragma statement."""
        version_match = re.search(r'pragma\s+solidity\s+[\^>=<]*(\d+\.\d+\.\d+)', source)
        if version_match:
            return version_match.group(1)
        return None
    
    def _is_safe_version(self, version: str) -> bool:
        """Check if Solidity version has built-in overflow checks (0.8.0+)."""
        try:
            parts = version.split('.')
            major, minor = int(parts[0]), int(parts[1])
            return major > 0 or (major == 0 and minor >= 8)
        except (ValueError, IndexError):
            return False
    
    def _has_arithmetic_operation(self, line: str) -> bool:
        """Check if line contains arithmetic operations."""
        # Look for arithmetic operators (excluding comparisons)
        # Skip lines that are just declarations or comparisons
        if any(op in line for op in ['++', '--', '+=', '-=', '*=', '/=']):
            return True
        
        # Check for arithmetic in assignments or expressions
        # But avoid simple comparisons
        if '=' in line and not any(comp in line for comp in ['==', '!=', '>=', '<=']):
            # Check if there's arithmetic after the assignment
            after_equals = line.split('=', 1)[1] if '=' in line else ''
            if any(op in after_equals for op in ['+', '-', '*', '/', '%']) and not any(comp in after_equals for comp in ['==', '!=']):
                # Exclude pure additions/subtractions in string operations
                if not re.search(r'["\'].*[\+\-\*/].*["\']', after_equals):
                    return True
        
        return False
