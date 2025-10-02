"""Native integer overflow/underflow detector based on Slither's implementation.

Based on: Slither's integer overflow/underflow detectors
Upstream: https://github.com/crytic/slither/blob/master/slither/detectors/statements/
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)


class IntegerOverflowDetector(BaseDetector):
    """Detects potential integer overflow/underflow vulnerabilities.
    
    Integer operations in Solidity < 0.8.0 can overflow/underflow silently.
    This detector identifies arithmetic operations that don't use SafeMath
    or checked arithmetic.
    
    Based on Slither's overflow/underflow detectors.
    """
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-integer-overflow",
            name="Integer Overflow/Underflow",
            description="Detects arithmetic operations that could overflow or underflow",
            source_tool="slither",
            source_version="0.10.0",
            source_detector_id="integer-overflow",
            severity=Severity.HIGH,
            confidence=0.75,
            category=DetectorCategory.ARITHMETIC,
            references=[
                "https://github.com/crytic/slither/wiki/Detector-Documentation",
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
        
        # Check Solidity version
        solidity_version = self._extract_solidity_version(contract_source)
        if solidity_version and self._is_safe_version(solidity_version):
            # Solidity 0.8.0+ has built-in overflow checks
            return findings
        
        current_function = None
        uses_safemath = self._uses_safemath(contract_source)
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Track function boundaries
            func_match = re.search(r'function\s+(\w+)', line_stripped)
            if func_match:
                current_function = func_match.group(1)
            
            # Look for unchecked arithmetic operations
            if self._is_unsafe_arithmetic(line_stripped, uses_safemath):
                finding = DetectorFinding(
                    detector_id=self.detector_id,
                    title=f"Potential integer overflow/underflow in {current_function or 'contract'}",
                    description=f"Arithmetic operation at line {line_num} may overflow or underflow. "
                               f"In Solidity versions < 0.8.0, integer operations don't revert on "
                               f"overflow/underflow. Use SafeMath library or upgrade to Solidity 0.8.0+.",
                    severity=self.metadata.severity,
                    confidence=self.metadata.confidence,
                    file_path=file_path,
                    line_number=line_num,
                    function_name=current_function,
                    code_snippet=self._extract_code_snippet(contract_source, line_num),
                    remediation="Use SafeMath library for arithmetic operations:\n"
                               "  using SafeMath for uint256;\n"
                               "  value = value.add(amount);  // instead of value + amount\n"
                               "Or upgrade to Solidity 0.8.0+ which has built-in overflow checks.",
                    references=self.metadata.references,
                    swc_id=self.metadata.swc_id,
                    category=self.metadata.category
                )
                findings.append(finding)
        
        return findings
    
    def _extract_solidity_version(self, source: str) -> Optional[str]:
        """Extract Solidity version from pragma statement."""
        match = re.search(r'pragma\s+solidity\s+([^;]+);', source)
        if match:
            return match.group(1).strip()
        return None
    
    def _is_safe_version(self, version_pragma: str) -> bool:
        """Check if Solidity version is >= 0.8.0 (has built-in checks)."""
        # Extract version number from pragma (e.g., "^0.8.0" -> "0.8.0")
        version_match = re.search(r'(\d+)\.(\d+)\.(\d+)', version_pragma)
        if version_match:
            major = int(version_match.group(1))
            minor = int(version_match.group(2))
            return major > 0 or (major == 0 and minor >= 8)
        return False
    
    def _uses_safemath(self, source: str) -> bool:
        """Check if contract uses SafeMath library."""
        return bool(re.search(r'using\s+SafeMath\s+for', source, re.IGNORECASE))
    
    def _is_unsafe_arithmetic(self, line: str, uses_safemath: bool) -> bool:
        """Check if line contains potentially unsafe arithmetic."""
        # Skip if SafeMath is being used in this line
        if uses_safemath and re.search(r'\.(add|sub|mul|div)\s*\(', line):
            return False
        
        # Skip local variable declarations
        if re.search(r'^\s*(uint|int)\d*\s+\w+\s*=', line):
            return False
        
        # Skip comparisons
        if re.search(r'(==|!=|<=|>=|<|>)', line):
            return False
        
        # Look for arithmetic operations on state variables or function parameters
        arithmetic_patterns = [
            r'\w+\s*\+=\s*\w+',      # Addition assignment
            r'\w+\s*-=\s*\w+',       # Subtraction assignment  
            r'\w+\s*\*=\s*\w+',      # Multiplication assignment
            r'\w+\s*=\s*\w+\s*\+',   # Assignment with addition
            r'\w+\s*=\s*\w+\s*-',    # Assignment with subtraction
            r'\w+\s*=\s*\w+\s*\*',   # Assignment with multiplication
            r'\+\+\w+',              # Pre-increment
            r'\w+\+\+',              # Post-increment
            r'--\w+',                # Pre-decrement
            r'\w+--',                # Post-decrement
        ]
        
        return any(re.search(pattern, line) for pattern in arithmetic_patterns)
