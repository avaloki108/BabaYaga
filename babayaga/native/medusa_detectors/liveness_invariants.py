"""Liveness invariant detector for smart contracts.

Detects violations of liveness properties such as:
- Unreachable code or states
- Deadlocked functions (all paths revert)
- Stuck states (no way to progress)

Based on: Medusa's liveness property checking
Upstream: https://github.com/crytic/medusa
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)
from .symbolic_engine import SymbolicExecutionEngine
from .invariant_checker import InvariantChecker, InvariantType


class LivenessInvariantsDetector(BaseDetector):
    """Detects violations of liveness invariants.
    
    This detector uses symbolic execution to verify that:
    - Functions are reachable and can complete successfully
    - No deadlock conditions exist
    - State transitions are possible
    """
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-medusa-liveness",
            name="Liveness Invariants",
            description="Detects deadlocks and unreachable states using symbolic analysis",
            source_tool="medusa",
            source_version="0.3.0",
            source_detector_id="liveness-invariants",
            severity=Severity.MEDIUM,
            confidence=0.7,
            category=DetectorCategory.LOGIC_ERRORS,
            references=[
                "https://github.com/crytic/medusa",
                "https://secure-contracts.com/program-analysis/liveness.html"
            ],
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for liveness invariant violations."""
        findings = []
        
        # Use invariant checker
        checker = InvariantChecker()
        violations = checker.check_invariants(contract_source, InvariantType.LIVENESS)
        
        # Convert violations to findings
        for violation in violations:
            finding = DetectorFinding(
                detector_id=self.detector_id,
                title=f"Liveness Invariant Violation: {violation.description}",
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
        """Check for common liveness violation patterns."""
        findings = []
        lines = source.split('\n')
        
        current_function = None
        current_function_line = None
        require_count = 0
        has_early_return = False
        has_reachable_end = False
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Track function boundaries
            func_match = re.search(r'function\s+(\w+)', line_stripped)
            if func_match:
                # Check previous function
                if current_function and require_count > 0 and not has_reachable_end:
                    # Function might be deadlocked
                    if require_count >= 3:  # Multiple requires without clear success path
                        finding = DetectorFinding(
                            detector_id=self.detector_id,
                            title="Potential Deadlock Condition",
                            description=f"Function '{current_function}' has multiple require statements "
                                      f"without a clear successful execution path",
                            severity=Severity.MEDIUM,
                            confidence=0.6,
                            file_path=file_path,
                            line_number=current_function_line,
                            function_name=current_function,
                            code_snippet=self._extract_code_snippet(source, current_function_line),
                            remediation=self._get_remediation(),
                            references=self.metadata.references,
                            category=self.metadata.category
                        )
                        findings.append(finding)
                
                # Reset for new function
                current_function = func_match.group(1)
                current_function_line = line_num
                require_count = 0
                has_early_return = False
                has_reachable_end = False
            
            # Track require statements
            if current_function and 'require' in line_stripped:
                require_count += 1
            
            # Track return statements
            if current_function and 'return' in line_stripped:
                has_reachable_end = True
            
            # Check for unreachable code after return
            if has_early_return and line_stripped and not line_stripped.startswith('//'):
                if not line_stripped.startswith('}'):
                    # Code after return
                    finding = DetectorFinding(
                        detector_id=self.detector_id,
                        title="Unreachable Code",
                        description=f"Code in '{current_function}' appears after a return statement and is unreachable",
                        severity=Severity.LOW,
                        confidence=0.8,
                        file_path=file_path,
                        line_number=line_num,
                        function_name=current_function,
                        code_snippet=self._extract_code_snippet(source, line_num),
                        remediation="Remove unreachable code or restructure function logic",
                        references=self.metadata.references,
                        category=self.metadata.category
                    )
                    findings.append(finding)
                    has_early_return = False  # Reset to avoid duplicate findings
            
            if 'return' in line_stripped and not line_stripped.startswith('//'):
                has_early_return = True
            
            # Check for always-false conditions
            if 'require' in line_stripped or 'if' in line_stripped:
                # Look for obviously false conditions like require(false) or if (false)
                if re.search(r'(require|if)\s*\(\s*false\s*\)', line_stripped):
                    finding = DetectorFinding(
                        detector_id=self.detector_id,
                        title="Always-False Condition",
                        description=f"Function '{current_function}' has a condition that is always false, "
                                  f"making code unreachable",
                        severity=Severity.MEDIUM,
                        confidence=0.9,
                        file_path=file_path,
                        line_number=line_num,
                        function_name=current_function,
                        code_snippet=self._extract_code_snippet(source, line_num),
                        remediation="Remove or fix the always-false condition",
                        references=self.metadata.references,
                        category=self.metadata.category
                    )
                    findings.append(finding)
        
        return findings
    
    def _get_remediation(self) -> str:
        """Get remediation advice."""
        return ("Ensure that functions have at least one reachable successful execution path. "
                "Review require/assert conditions to prevent deadlocks. Remove unreachable code. "
                "Consider edge cases where the contract might get stuck in a particular state.")
