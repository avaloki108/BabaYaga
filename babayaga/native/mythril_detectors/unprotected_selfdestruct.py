"""Native unprotected selfdestruct detector.

Based on: Mythril's unprotected selfdestruct detector
Upstream: https://github.com/ConsenSys/mythril
SWC-106: https://swcregistry.io/docs/SWC-106
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)
from .symbolic_engine import SimplifiedSymbolicEngine


class UnprotectedSelfdestructDetector(BaseDetector):
    """Detects unprotected selfdestruct calls.
    
    Uses symbolic execution to identify selfdestruct calls that
    lack proper access controls.
    
    Based on Mythril's unprotected selfdestruct detection.
    """
    
    def __init__(self):
        super().__init__()
        self.engine = SimplifiedSymbolicEngine()
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-mythril-unprotected-selfdestruct",
            name="Unprotected Selfdestruct (Symbolic Execution)",
            description="Detects selfdestruct calls without proper access controls",
            source_tool="mythril",
            source_version="0.24.8",
            source_detector_id="unprotected-selfdestruct",
            severity=Severity.CRITICAL,
            confidence=0.95,
            category=DetectorCategory.SELFDESTRUCT,
            references=[
                "https://github.com/ConsenSys/mythril/wiki/Unprotected-Selfdestruct",
                "https://swcregistry.io/docs/SWC-106"
            ],
            swc_id="SWC-106",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for unprotected selfdestruct."""
        findings = []
        
        # Extract and analyze functions
        functions = self._extract_functions(contract_source)
        
        for func_name, func_code, func_start_line in functions:
            # Skip private functions (usually safe)
            if 'private' in func_code.split('{')[0]:
                continue
            
            # Check for unprotected selfdestruct
            vulnerable_line = self.engine.check_unprotected_selfdestruct(func_code)
            
            if vulnerable_line is not None:
                absolute_line = func_start_line + vulnerable_line
                finding = self._create_finding(
                    func_name, absolute_line, contract_source, file_path
                )
                findings.append(finding)
        
        return findings
    
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
                       source: str, file_path: str) -> DetectorFinding:
        """Create a finding for unprotected selfdestruct."""
        return DetectorFinding(
            detector_id=self.detector_id,
            title=f"Unprotected selfdestruct in {function_name}",
            description=f"Function '{function_name}' contains a selfdestruct call without proper "
                       f"access controls. Anyone can call this function and destroy the contract, "
                       f"causing permanent loss of functionality and funds. "
                       f"Detected through symbolic execution analysis.",
            severity=self.metadata.severity,
            confidence=self.metadata.confidence,
            file_path=file_path,
            line_number=line_number,
            function_name=function_name,
            code_snippet=self._extract_code_snippet(source, line_number),
            remediation="Add strict access control checks (e.g., require(msg.sender == owner)) to "
                       "restrict selfdestruct to only authorized users, or remove selfdestruct entirely.",
            references=self.metadata.references,
            swc_id=self.metadata.swc_id,
            category=self.metadata.category
        )
