"""Native locked ether detector based on Securify2's implementation.

Based on: Securify2's locked ether patterns
Upstream: https://github.com/eth-sri/securify2
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)


class LockedEtherDetector(BaseDetector):
    """Detects contracts that can receive but not withdraw ether.
    
    This detector identifies contracts that can receive ether (payable functions
    or fallback) but have no mechanism to withdraw it, effectively locking funds.
    """
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-securify2-locked-ether",
            name="Locked Ether",
            description="Detects contracts that can receive ether but have no withdrawal mechanism",
            source_tool="securify2",
            source_version="0.1.0",
            source_detector_id="LockedEther",
            severity=Severity.MEDIUM,
            confidence=0.8,
            category=DetectorCategory.LOGIC_ERRORS,
            references=[
                "https://github.com/eth-sri/securify2",
                "https://swcregistry.io/docs/SWC-132"
            ],
            swc_id="SWC-132",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for locked ether vulnerabilities."""
        findings = []
        lines = contract_source.split('\n')
        
        # Check if contract can receive ether
        can_receive = False
        has_withdrawal = False
        contract_name = None
        payable_line = 0
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Track contract name
            contract_match = re.search(r'contract\s+(\w+)', line_stripped)
            if contract_match:
                contract_name = contract_match.group(1)
            
            # Check for ways to receive ether
            if not can_receive:
                if self._can_receive_ether(line_stripped):
                    can_receive = True
                    payable_line = line_num
            
            # Check for ways to withdraw ether
            if not has_withdrawal:
                if self._can_withdraw_ether(line_stripped):
                    has_withdrawal = True
        
        # Report if can receive but cannot withdraw
        if can_receive and not has_withdrawal:
            finding = DetectorFinding(
                detector_id=self.detector_id,
                title=f"Locked ether in contract {contract_name or 'unknown'}",
                description=f"Contract can receive ether (payable function/fallback at line {payable_line}) "
                           f"but has no mechanism to withdraw it. Ether sent to this contract will be locked forever.",
                severity=self.metadata.severity,
                confidence=self.metadata.confidence,
                file_path=file_path,
                line_number=payable_line,
                code_snippet=self._extract_code_snippet(contract_source, payable_line),
                remediation="Add a withdrawal function to allow extracting ether from the contract. "
                           "For example: function withdraw() public onlyOwner { "
                           "payable(owner).transfer(address(this).balance); }",
                references=self.metadata.references,
                swc_id=self.metadata.swc_id,
                category=self.metadata.category
            )
            findings.append(finding)
        
        return findings
    
    def _can_receive_ether(self, line: str) -> bool:
        """Check if line indicates contract can receive ether."""
        # Look for payable keyword in functions
        if 'payable' in line:
            return True
        
        # Look for receive() or fallback() functions
        if 'receive()' in line or 'fallback()' in line:
            return True
        
        return False
    
    def _can_withdraw_ether(self, line: str) -> bool:
        """Check if line indicates a withdrawal mechanism."""
        # Look for transfer, send, or call that sends ether out
        withdrawal_patterns = [
            r'\.transfer\s*\(',
            r'\.send\s*\(',
            r'\.call\s*\{.*value.*:',
            r'payable\s*\([^)]*\)\.transfer',
            r'payable\s*\([^)]*\)\.send',
            r'selfdestruct\s*\(',  # Also counts as withdrawal
        ]
        
        for pattern in withdrawal_patterns:
            if re.search(pattern, line):
                return True
        
        return False
