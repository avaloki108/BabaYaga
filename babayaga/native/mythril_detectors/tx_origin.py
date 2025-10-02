"""Native tx.origin authentication detector.

Based on: Mythril's tx.origin detector
Upstream: https://github.com/ConsenSys/mythril
SWC-115: https://swcregistry.io/docs/SWC-115
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)
from .symbolic_engine import SimplifiedSymbolicEngine


class TxOriginSymbolicDetector(BaseDetector):
    """Detects usage of tx.origin for authentication.
    
    Uses symbolic execution to identify patterns where tx.origin
    is used for authorization, which is vulnerable to phishing attacks.
    
    Based on Mythril's tx.origin detection.
    """
    
    def __init__(self):
        super().__init__()
        self.engine = SimplifiedSymbolicEngine()
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-mythril-tx-origin",
            name="Dangerous tx.origin Usage (Symbolic Execution)",
            description="Detects use of tx.origin for authentication using symbolic execution",
            source_tool="mythril",
            source_version="0.24.8",
            source_detector_id="tx-origin",
            severity=Severity.MEDIUM,
            confidence=0.9,
            category=DetectorCategory.ACCESS_CONTROL,
            references=[
                "https://github.com/ConsenSys/mythril/wiki/Tx.Origin-Authentication",
                "https://swcregistry.io/docs/SWC-115"
            ],
            swc_id="SWC-115",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for tx.origin usage in authentication."""
        findings = []
        
        # Extract and analyze functions
        functions = self._extract_functions(contract_source)
        
        for func_name, func_code, func_start_line in functions:
            # Check for tx.origin usage
            vulnerable_lines = self.engine.check_tx_origin_auth(func_code)
            
            for line_offset in vulnerable_lines:
                absolute_line = func_start_line + line_offset
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
        """Create a finding for tx.origin usage."""
        return DetectorFinding(
            detector_id=self.detector_id,
            title=f"Dangerous use of tx.origin in {function_name}",
            description=f"Function '{function_name}' uses tx.origin for authentication. "
                       f"tx.origin should never be used for authorization as it is vulnerable "
                       f"to phishing attacks where a malicious contract can trick a user into "
                       f"authorizing an action. Detected through symbolic execution analysis.",
            severity=self.metadata.severity,
            confidence=self.metadata.confidence,
            file_path=file_path,
            line_number=line_number,
            function_name=function_name,
            code_snippet=self._extract_code_snippet(source, line_number),
            remediation="Use msg.sender instead of tx.origin for authorization checks. "
                       "msg.sender refers to the immediate caller, while tx.origin refers to "
                       "the original transaction sender.",
            references=self.metadata.references,
            swc_id=self.metadata.swc_id,
            category=self.metadata.category
        )
