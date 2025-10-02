"""Native unprotected ether withdrawal detector.

Based on: Mythril's unprotected ether withdrawal detector
Upstream: https://github.com/ConsenSys/mythril
SWC-105: https://swcregistry.io/docs/SWC-105
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)
from .symbolic_engine import SimplifiedSymbolicEngine


class UnprotectedEtherDetector(BaseDetector):
    """Detects unprotected ether withdrawal functions.
    
    Uses symbolic execution to identify functions that can send ether
    without proper access controls.
    
    Based on Mythril's unprotected ether withdrawal detection.
    """
    
    def __init__(self):
        super().__init__()
        self.engine = SimplifiedSymbolicEngine()
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-mythril-unprotected-ether",
            name="Unprotected Ether Withdrawal (Symbolic Execution)",
            description="Detects functions that can send ether without access controls",
            source_tool="mythril",
            source_version="0.24.8",
            source_detector_id="unprotected-ether-withdrawal",
            severity=Severity.HIGH,
            confidence=0.9,
            category=DetectorCategory.ACCESS_CONTROL,
            references=[
                "https://github.com/ConsenSys/mythril/wiki/Unprotected-Ether-Withdrawal",
                "https://swcregistry.io/docs/SWC-105"
            ],
            swc_id="SWC-105",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for unprotected ether withdrawal."""
        findings = []
        
        # Extract and analyze functions
        functions = self._extract_functions(contract_source)
        
        for func_name, func_code, func_start_line in functions:
            # Skip constructor and private functions (usually safe)
            if func_name == 'constructor' or 'private' in func_code.split('{')[0]:
                continue
            
            # Run symbolic execution
            states = self.engine.analyze_function(func_code, func_name)
            
            # Check for unprotected ether withdrawal
            if self.engine.check_unprotected_ether(func_code, states):
                # Find the line with the ether transfer
                transfer_line = self._find_ether_transfer_line(func_code, func_start_line)
                
                finding = self._create_finding(
                    func_name, transfer_line, contract_source, file_path
                )
                findings.append(finding)
        
        return findings
    
    def _find_ether_transfer_line(self, func_code: str, func_start_line: int) -> int:
        """Find the line number of ether transfer in function."""
        lines = func_code.split('\n')
        
        for i, line in enumerate(lines):
            if any(pattern in line for pattern in ['.call', '.send', '.transfer']):
                return func_start_line + i
        
        return func_start_line
    
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
        """Create a finding for unprotected ether withdrawal."""
        return DetectorFinding(
            detector_id=self.detector_id,
            title=f"Unprotected ether withdrawal in {function_name}",
            description=f"Function '{function_name}' can send ether to arbitrary addresses without "
                       f"proper access controls. Anyone can call this function and potentially "
                       f"drain the contract's balance. Detected through symbolic execution analysis.",
            severity=self.metadata.severity,
            confidence=self.metadata.confidence,
            file_path=file_path,
            line_number=line_number,
            function_name=function_name,
            code_snippet=self._extract_code_snippet(source, line_number),
            remediation="Add access control checks (e.g., require(msg.sender == owner)) or use "
                       "OpenZeppelin's Ownable contract to restrict who can withdraw ether.",
            references=self.metadata.references,
            swc_id=self.metadata.swc_id,
            category=self.metadata.category
        )
