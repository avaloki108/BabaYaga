"""Native uninitialized storage pointer detector based on Securify2's implementation.

Based on: Securify2's uninitialized storage pointer patterns
Upstream: https://github.com/eth-sri/securify2
"""

import re
from typing import List, Optional, Dict, Any

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)


class UninitializedStorageDetector(BaseDetector):
    """Detects uninitialized storage pointer vulnerabilities.
    
    This detector identifies variables that are declared with storage
    location but not initialized, which can lead to unexpected behavior.
    """
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-securify2-uninitialized-storage",
            name="Uninitialized Storage Pointer",
            description="Detects uninitialized storage pointers that may point to unexpected storage slots",
            source_tool="securify2",
            source_version="0.1.0",
            source_detector_id="UninitializedStoragePointer",
            severity=Severity.HIGH,
            confidence=0.9,
            category=DetectorCategory.STORAGE,
            references=[
                "https://github.com/eth-sri/securify2",
                "https://swcregistry.io/docs/SWC-109"
            ],
            swc_id="SWC-109",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for uninitialized storage pointer vulnerabilities."""
        findings = []
        lines = contract_source.split('\n')
        
        current_function = None
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Track function boundaries
            func_match = re.search(r'function\s+(\w+)', line_stripped)
            if func_match:
                current_function = func_match.group(1)
            
            # Look for storage variable declarations without initialization
            # Pattern: storage location without assignment
            if self._is_uninitialized_storage(line_stripped):
                finding = DetectorFinding(
                    detector_id=self.detector_id,
                    title=f"Uninitialized storage pointer in {current_function or 'contract'}",
                    description=f"Storage pointer declared at line {line_num} is not initialized. "
                               f"This can lead to unexpected behavior as it may point to arbitrary storage slots.",
                    severity=self.metadata.severity,
                    confidence=self.metadata.confidence,
                    file_path=file_path,
                    line_number=line_num,
                    function_name=current_function,
                    code_snippet=self._extract_code_snippet(contract_source, line_num),
                    remediation="Initialize storage pointers explicitly or use memory data location for local variables. "
                               "For example: 'MyStruct storage myStruct = myStructs[index];' or use 'memory' instead of 'storage'.",
                    references=self.metadata.references,
                    swc_id=self.metadata.swc_id,
                    category=self.metadata.category
                )
                findings.append(finding)
        
        return findings
    
    def _is_uninitialized_storage(self, line: str) -> bool:
        """Check if line contains uninitialized storage pointer."""
        # Look for variable declarations with 'storage' keyword but no initialization
        # Pattern: type storage varName; (without = ...)
        storage_pattern = r'\w+\s+storage\s+\w+\s*;'
        if re.search(storage_pattern, line):
            # Make sure it's not initialized
            if '=' not in line:
                return True
        
        # Also check for storage pointers in local variable declarations
        # Pattern: Type storage varName (in function body, not initialized)
        if 'storage' in line and ';' in line:
            # Check it's not a parameter or initialized
            if '=' not in line and 'function' not in line and '(' not in line:
                return True
        
        return False
