"""Native unchecked call detector using symbolic execution.

Based on: Mythril's unchecked call detector
Upstream: https://github.com/ConsenSys/mythril
SWC-104: https://swcregistry.io/docs/SWC-104
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)
from .symbolic_engine import SimplifiedSymbolicEngine


class UncheckedCallSymbolicDetector(BaseDetector):
    """Detects unchecked external call return values.
    
    Uses symbolic execution to identify external calls whose return
    values are not checked, which can lead to silent failures.
    
    Based on Mythril's unchecked call detection.
    """
    
    def __init__(self):
        super().__init__()
        self.engine = SimplifiedSymbolicEngine()
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-mythril-unchecked-call",
            name="Unchecked Call Return Value (Symbolic Execution)",
            description="Detects external calls with unchecked return values using symbolic execution",
            source_tool="mythril",
            source_version="0.24.8",
            source_detector_id="unchecked-send",
            severity=Severity.MEDIUM,
            confidence=0.85,
            category=DetectorCategory.EXTERNAL_CALLS,
            references=[
                "https://github.com/ConsenSys/mythril/wiki/Unchecked-Call-Return-Value",
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
        
        # Extract and analyze functions
        functions = self._extract_functions(contract_source)
        
        for func_name, func_code, func_start_line in functions:
            # Run symbolic execution
            states = self.engine.analyze_function(func_code, func_name)
            
            # Check for unchecked calls
            unchecked_calls = self.engine.check_unchecked_calls(states)
            
            for line_offset, call_type in unchecked_calls:
                absolute_line = func_start_line + line_offset
                
                # Check if return value is actually checked
                if self._is_return_checked(func_code, line_offset):
                    continue
                
                finding = self._create_finding(
                    func_name, absolute_line, call_type, contract_source, file_path
                )
                findings.append(finding)
        
        return findings
    
    def _is_return_checked(self, func_code: str, call_line_offset: int) -> bool:
        """Check if call return value is checked."""
        lines = func_code.split('\n')
        if call_line_offset >= len(lines):
            return False
        
        call_line = lines[call_line_offset]
        
        # Check if result is captured and checked
        if re.search(r'\(bool\s+\w+,', call_line) or re.search(r'bool\s+\w+\s*=.*\.call', call_line):
            # Return value is captured, check if it's used in require/if
            for line in lines[call_line_offset:call_line_offset+5]:
                if 'require' in line or 'assert' in line or 'if' in line:
                    return True
        
        return False
    
    def _extract_functions(self, source: str) -> List[tuple]:
        """Extract functions from contract source."""
        functions = []
        lines = source.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            func_match = re.match(r'function\s+(\w+)\s*\([^)]*\)', line)
            if func_match:
                func_name = func_match.group(1)
                func_start_line = i + 1
                
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
                       call_type: str, source: str, file_path: str) -> DetectorFinding:
        """Create a finding for unchecked call."""
        return DetectorFinding(
            detector_id=self.detector_id,
            title=f"Unchecked {call_type} return value in {function_name}",
            description=f"Function '{function_name}' makes an external {call_type} call but does not "
                       f"check its return value. This can lead to silent failures where the call "
                       f"fails but execution continues. Detected through symbolic execution analysis.",
            severity=self.metadata.severity,
            confidence=self.metadata.confidence,
            file_path=file_path,
            line_number=line_number,
            function_name=function_name,
            code_snippet=self._extract_code_snippet(source, line_number),
            remediation="Always check the return value of external calls using require() or assert(). "
                       "Example: (bool success, ) = recipient.call{value: amount}(\"\"); require(success);",
            references=self.metadata.references,
            swc_id=self.metadata.swc_id,
            category=self.metadata.category
        )
