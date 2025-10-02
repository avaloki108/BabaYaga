"""Native integer overflow/underflow detector using symbolic execution.

Based on: Mythril's integer overflow detector
Upstream: https://github.com/ConsenSys/mythril
SWC-101: https://swcregistry.io/docs/SWC-101
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)
from .symbolic_engine import SimplifiedSymbolicEngine


class IntegerOverflowDetector(BaseDetector):
    """Detects integer overflow and underflow vulnerabilities.
    
    Uses symbolic execution to identify arithmetic operations that could
    overflow or underflow. Considers Solidity version and SafeMath usage.
    
    Based on Mythril's integer overflow detection using symbolic execution.
    """
    
    def __init__(self):
        super().__init__()
        self.engine = SimplifiedSymbolicEngine()
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-mythril-integer-overflow",
            name="Integer Overflow/Underflow (Symbolic Execution)",
            description="Detects potential integer overflow and underflow using symbolic execution analysis",
            source_tool="mythril",
            source_version="0.24.8",
            source_detector_id="integer-overflow",
            severity=Severity.HIGH,
            confidence=0.85,
            category=DetectorCategory.ARITHMETIC,
            references=[
                "https://github.com/ConsenSys/mythril/wiki/Integer-Overflow",
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
        
        # Check Solidity version - 0.8.0+ has built-in overflow protection
        if self._has_safe_version(contract_source):
            return findings
        
        # Check if SafeMath is used globally
        uses_safemath = 'SafeMath' in contract_source
        
        # Extract and analyze functions
        functions = self._extract_functions(contract_source)
        
        for func_name, func_code, func_start_line in functions:
            # Skip if this function uses SafeMath
            if uses_safemath and self._uses_safemath_in_function(func_code):
                continue
            
            # Run symbolic execution
            states = self.engine.analyze_function(func_code, func_name)
            
            # Check for overflow/underflow
            vulnerable_lines = self.engine.check_integer_overflow(states)
            
            for line_offset in vulnerable_lines:
                absolute_line = func_start_line + line_offset
                finding = self._create_finding(
                    func_name, absolute_line, contract_source, file_path
                )
                findings.append(finding)
        
        return findings
    
    def _has_safe_version(self, source: str) -> bool:
        """Check if contract uses Solidity 0.8.0 or higher."""
        version_match = re.search(r'pragma\s+solidity\s+[\^>=]*(\d+)\.(\d+)\.(\d+)', source)
        if version_match:
            major = int(version_match.group(1))
            minor = int(version_match.group(2))
            return major > 0 or (major == 0 and minor >= 8)
        return False
    
    def _uses_safemath_in_function(self, func_code: str) -> bool:
        """Check if function uses SafeMath operations."""
        safemath_methods = ['.add(', '.sub(', '.mul(', '.div(', '.mod(']
        return any(method in func_code for method in safemath_methods)
    
    def _extract_functions(self, source: str) -> List[tuple]:
        """Extract functions from contract source.
        
        Returns list of (function_name, function_code, start_line) tuples.
        """
        functions = []
        lines = source.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for function definition
            func_match = re.match(r'function\s+(\w+)\s*\([^)]*\)', line)
            if func_match:
                func_name = func_match.group(1)
                func_start_line = i + 1
                
                # Find function body
                func_lines = []
                brace_count = 0
                started = False
                
                for j in range(i, len(lines)):
                    func_line = lines[j]
                    func_lines.append(func_line)
                    
                    if '{' in func_line:
                        started = True
                        brace_count += func_line.count('{')
                    if '}' in func_line:
                        brace_count -= func_line.count('}')
                    
                    if started and brace_count == 0:
                        functions.append((func_name, '\n'.join(func_lines), func_start_line))
                        i = j
                        break
            
            i += 1
        
        return functions
    
    def _create_finding(self, function_name: str, line_number: int,
                       source: str, file_path: str) -> DetectorFinding:
        """Create a finding for detected integer overflow/underflow."""
        return DetectorFinding(
            detector_id=self.detector_id,
            title=f"Potential integer overflow/underflow in {function_name}",
            description=f"Function '{function_name}' contains arithmetic operations that could "
                       f"overflow or underflow. This can lead to unexpected behavior or security vulnerabilities. "
                       f"Detected through symbolic execution analysis.",
            severity=self.metadata.severity,
            confidence=self.metadata.confidence,
            file_path=file_path,
            line_number=line_number,
            function_name=function_name,
            code_snippet=self._extract_code_snippet(source, line_number),
            remediation="Use Solidity 0.8.0+ which has built-in overflow protection, "
                       "or use OpenZeppelin's SafeMath library for arithmetic operations.",
            references=self.metadata.references,
            swc_id=self.metadata.swc_id,
            category=self.metadata.category
        )
