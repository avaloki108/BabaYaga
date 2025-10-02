"""Native reentrancy detector using symbolic execution.

Based on: Mythril's reentrancy detector
Upstream: https://github.com/ConsenSys/mythril
SWC-107: https://swcregistry.io/docs/SWC-107
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)
from .symbolic_engine import SimplifiedSymbolicEngine


class ReentrancySymbolicDetector(BaseDetector):
    """Detects reentrancy vulnerabilities using symbolic execution.
    
    This detector uses symbolic execution to identify reentrancy patterns
    where external calls are made before state is updated.
    
    Based on Mythril's reentrancy detection approach.
    """
    
    def __init__(self):
        super().__init__()
        self.engine = SimplifiedSymbolicEngine()
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-mythril-reentrancy",
            name="Reentrancy Vulnerability (Symbolic Execution)",
            description="Detects reentrancy vulnerabilities using symbolic execution analysis",
            source_tool="mythril",
            source_version="0.24.8",
            source_detector_id="reentrancy",
            severity=Severity.HIGH,
            confidence=0.9,
            category=DetectorCategory.REENTRANCY,
            references=[
                "https://github.com/ConsenSys/mythril/wiki/Reentrancy",
                "https://swcregistry.io/docs/SWC-107"
            ],
            swc_id="SWC-107",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for reentrancy vulnerabilities."""
        findings = []
        
        # Extract and analyze functions
        functions = self._extract_functions(contract_source)
        
        for func_name, func_code, func_start_line in functions:
            # Skip view/pure functions
            if self._is_safe_function(func_code):
                continue
            
            # Check for reentrancy guard
            if self._has_reentrancy_guard(func_code):
                continue
            
            # Run symbolic execution
            states = self.engine.analyze_function(func_code, func_name)
            
            # Check for reentrancy pattern
            vulnerable_lines = self.engine.check_reentrancy_pattern(states)
            
            for line_offset in vulnerable_lines:
                absolute_line = func_start_line + line_offset
                finding = self._create_finding(
                    func_name, absolute_line, contract_source, file_path
                )
                findings.append(finding)
        
        return findings
    
    def _is_safe_function(self, func_code: str) -> bool:
        """Check if function is view or pure."""
        return 'view' in func_code.split('{')[0] or 'pure' in func_code.split('{')[0]
    
    def _has_reentrancy_guard(self, func_code: str) -> bool:
        """Check if function uses reentrancy guard."""
        guards = ['nonReentrant', 'noReentrancy', 'ReentrancyGuard']
        return any(guard in func_code for guard in guards)
    
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
        """Create a finding for detected reentrancy."""
        return DetectorFinding(
            detector_id=self.detector_id,
            title=f"Reentrancy vulnerability in {function_name}",
            description=f"Function '{function_name}' makes an external call and then modifies state. "
                       f"This can lead to reentrancy attacks where the called contract calls back "
                       f"before state changes are complete. Detected through symbolic execution analysis.",
            severity=self.metadata.severity,
            confidence=self.metadata.confidence,
            file_path=file_path,
            line_number=line_number,
            function_name=function_name,
            code_snippet=self._extract_code_snippet(source, line_number),
            remediation="Use the checks-effects-interactions pattern: perform all state changes "
                       "before making external calls, or use OpenZeppelin's ReentrancyGuard.",
            references=self.metadata.references,
            swc_id=self.metadata.swc_id,
            category=self.metadata.category
        )
