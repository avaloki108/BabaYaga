"""Conservation invariant detector for smart contracts.

Detects violations of conservation laws such as:
- Balance conservation (sum of balances should not change unexpectedly)
- Supply conservation (total supply tracking)
- Token conservation (tokens shouldn't appear/disappear)

Based on: Medusa's conservation invariant checking
Upstream: https://github.com/crytic/medusa
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)
from .symbolic_engine import SymbolicExecutionEngine, SymbolicState
from .invariant_checker import InvariantChecker, InvariantType


class ConservationInvariantsDetector(BaseDetector):
    """Detects violations of conservation invariants.
    
    This detector uses symbolic execution to verify that:
    - Balances are properly conserved
    - Total supply remains consistent
    - Tokens don't appear or disappear unexpectedly
    """
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-medusa-conservation",
            name="Conservation Invariants",
            description="Detects violations of balance and supply conservation using symbolic analysis",
            source_tool="medusa",
            source_version="0.3.0",
            source_detector_id="conservation-invariants",
            severity=Severity.HIGH,
            confidence=0.8,
            category=DetectorCategory.LOGIC_ERRORS,
            references=[
                "https://github.com/crytic/medusa",
                "https://secure-contracts.com/program-analysis/invariant-testing.html"
            ],
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for conservation invariant violations."""
        findings = []
        
        # Use invariant checker
        checker = InvariantChecker()
        violations = checker.check_invariants(contract_source, InvariantType.CONSERVATION)
        
        # Convert violations to findings
        for violation in violations:
            finding = DetectorFinding(
                detector_id=self.detector_id,
                title=f"Conservation Invariant Violation: {violation.description}",
                description=violation.description,
                severity=self.metadata.severity,
                confidence=self.metadata.confidence,
                file_path=file_path,
                line_number=violation.line_number,
                function_name=violation.function_name,
                remediation=violation.remediation or self._get_remediation(),
                references=self.metadata.references,
                category=self.metadata.category
            )
            findings.append(finding)
        
        # Additional pattern-based checks
        pattern_findings = await self._check_patterns(contract_source, file_path)
        findings.extend(pattern_findings)
        
        return findings
    
    async def _check_patterns(self, source: str, file_path: str) -> List[DetectorFinding]:
        """Check for common conservation violation patterns."""
        findings = []
        lines = source.split('\n')
        
        # Check for unbalanced transfers
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Look for transfer patterns without proper balance checks
            if 'transfer' in line_stripped.lower():
                # Check if there's a balance decrease
                if '-=' in line_stripped or '--' in line_stripped:
                    # Look for corresponding balance increase
                    context_lines = lines[max(0, line_num-3):min(len(lines), line_num+3)]
                    has_increase = any('+=' in l or '++' in l for l in context_lines)
                    
                    if not has_increase:
                        finding = DetectorFinding(
                            detector_id=self.detector_id,
                            title="Potential Balance Conservation Violation",
                            description="Transfer operation decreases balance without corresponding increase",
                            severity=Severity.MEDIUM,
                            confidence=0.6,
                            file_path=file_path,
                            line_number=line_num,
                            code_snippet=self._extract_code_snippet(source, line_num),
                            remediation=self._get_remediation(),
                            references=self.metadata.references,
                            category=self.metadata.category
                        )
                        findings.append(finding)
            
            # Check for total supply modifications without proper tracking
            if 'totalSupply' in line_stripped:
                if any(op in line_stripped for op in ['+=', '-=', '++', '--', '=']):
                    # Look for mint/burn operations
                    context = ' '.join(lines[max(0, line_num-5):min(len(lines), line_num+1)])
                    has_balance_update = 'balance' in context.lower()
                    
                    if not has_balance_update:
                        finding = DetectorFinding(
                            detector_id=self.detector_id,
                            title="Total Supply Modification Without Balance Update",
                            description="totalSupply is modified without corresponding balance change",
                            severity=Severity.HIGH,
                            confidence=0.7,
                            file_path=file_path,
                            line_number=line_num,
                            code_snippet=self._extract_code_snippet(source, line_num),
                            remediation="Ensure totalSupply changes are matched with balance updates",
                            references=self.metadata.references,
                            category=self.metadata.category
                        )
                        findings.append(finding)
        
        return findings
    
    def _get_remediation(self) -> str:
        """Get remediation advice."""
        return ("Ensure that all balance and supply operations maintain conservation laws. "
                "When tokens are transferred, the sum of balances should remain constant. "
                "When minting, increase totalSupply; when burning, decrease it. "
                "Use SafeMath or Solidity 0.8+ to prevent overflow/underflow.")
