"""Native block hash usage detector based on Slither's implementation.

Based on: Slither's weak PRNG and block hash detectors
Upstream: https://github.com/crytic/slither/blob/master/slither/detectors/statements/
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)


class BlockHashUsageDetector(BaseDetector):
    """Detects dangerous usage of block properties for randomness.
    
    Block properties (blockhash, block.number, block.difficulty, etc.)
    are predictable and should not be used for random number generation.
    
    Based on Slither's weak-prng detector.
    """
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-block-hash-usage",
            name="Weak Randomness from Block Properties",
            description="Detects use of block properties for random number generation",
            source_tool="slither",
            source_version="0.10.0",
            source_detector_id="weak-prng",
            severity=Severity.HIGH,
            confidence=0.8,
            category=DetectorCategory.RANDOMNESS,
            references=[
                "https://github.com/crytic/slither/wiki/Detector-Documentation#weak-PRNG",
                "https://swcregistry.io/docs/SWC-120"
            ],
            swc_id="SWC-120",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for weak randomness from block properties."""
        findings = []
        lines = contract_source.split('\n')
        
        current_function = None
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Track function boundaries
            func_match = re.search(r'function\s+(\w+)', line_stripped)
            if func_match:
                current_function = func_match.group(1)
            
            # Look for weak randomness patterns
            if self._is_weak_randomness(line_stripped):
                finding = DetectorFinding(
                    detector_id=self.detector_id,
                    title=f"Weak randomness in {current_function or 'contract'}",
                    description=f"Weak source of randomness at line {line_num}. "
                               f"Block properties (blockhash, block.number, block.timestamp, "
                               f"block.difficulty) are predictable and can be manipulated by miners. "
                               f"They should never be used as a source of randomness.",
                    severity=self.metadata.severity,
                    confidence=self.metadata.confidence,
                    file_path=file_path,
                    line_number=line_num,
                    function_name=current_function,
                    code_snippet=self._extract_code_snippet(contract_source, line_num),
                    remediation="Use a secure source of randomness:\n"
                               "  - Chainlink VRF (Verifiable Random Function)\n"
                               "  - Commit-reveal schemes\n"
                               "  - Oracle-based randomness\n"
                               "Never use block properties for randomness in production contracts.",
                    references=self.metadata.references,
                    swc_id=self.metadata.swc_id,
                    category=self.metadata.category
                )
                findings.append(finding)
        
        return findings
    
    def _is_weak_randomness(self, line: str) -> bool:
        """Check if line uses weak randomness from block properties."""
        # Block properties that are weak for randomness
        weak_sources = [
            r'blockhash\s*\(',
            r'block\.blockhash\s*\(',
            r'block\.number',
            r'block\.timestamp',
            r'block\.difficulty',
            r'block\.gaslimit',
            r'\bnow\b',
        ]
        
        # Check if any weak source is used
        has_weak_source = any(re.search(pattern, line) for pattern in weak_sources)
        
        if not has_weak_source:
            return False
        
        # Check if it's being used for randomness (modulo, assignment, etc.)
        randomness_patterns = [
            r'%',                           # Modulo operation
            r'random\w*\s*=',              # Assignment to random variable
            r'rand\w*\s*=',                # Assignment to rand variable
            r'seed\w*\s*=',                # Assignment to seed variable
            r'keccak256\s*\(',             # Hash function (often used for randomness)
            r'sha256\s*\(',                # Hash function
        ]
        
        return any(re.search(pattern, line, re.IGNORECASE) for pattern in randomness_patterns)
