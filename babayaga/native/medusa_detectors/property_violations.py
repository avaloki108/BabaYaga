"""Property violation detector for smart contracts.

Detects violations of custom properties and invariants defined in contracts:
- echidna_* properties
- invariant_* properties
- Custom assertions

Based on: Medusa's property testing approach
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


class PropertyViolationDetector(BaseDetector):
    """Detects violations of custom contract properties.
    
    This detector uses symbolic execution to verify that:
    - echidna_* property functions always return true
    - invariant_* functions are maintained
    - Custom assertions hold
    """
    
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-medusa-properties",
            name="Property Violations",
            description="Detects violations of custom contract properties using symbolic analysis",
            source_tool="medusa",
            source_version="0.3.0",
            source_detector_id="property-violations",
            severity=Severity.HIGH,
            confidence=0.75,
            category=DetectorCategory.LOGIC_ERRORS,
            references=[
                "https://github.com/crytic/medusa",
                "https://github.com/crytic/echidna",
                "https://secure-contracts.com/program-analysis/property-testing.html"
            ],
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract for property violations."""
        findings = []
        
        # Use invariant checker
        checker = InvariantChecker()
        violations = checker.check_invariants(contract_source, InvariantType.PROPERTY)
        
        # Convert violations to findings
        for violation in violations:
            finding = DetectorFinding(
                detector_id=self.detector_id,
                title=f"Property Violation: {violation.description}",
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
        """Check for property-related patterns."""
        findings = []
        lines = source.split('\n')
        
        # Track property functions
        property_functions = self._extract_property_functions(source)
        
        # Analyze each property function
        for prop_func in property_functions:
            func_name = prop_func['name']
            func_line = prop_func['line']
            func_body = prop_func['body']
            
            # Check if property can fail
            can_return_false = self._can_return_false(func_body)
            
            if can_return_false:
                finding = DetectorFinding(
                    detector_id=self.detector_id,
                    title=f"Property '{func_name}' May Be Violated",
                    description=f"Property function '{func_name}' contains conditions that may return false, "
                              f"indicating a potential invariant violation",
                    severity=Severity.HIGH,
                    confidence=0.7,
                    file_path=file_path,
                    line_number=func_line,
                    function_name=func_name,
                    code_snippet=self._extract_code_snippet(source, func_line),
                    remediation=self._get_remediation_for_property(func_name),
                    references=self.metadata.references,
                    category=self.metadata.category
                )
                findings.append(finding)
        
        # Check for assert statements that might fail
        for line_num, line in enumerate(lines, 1):
            if 'assert' in line and not line.strip().startswith('//'):
                # Extract assertion condition
                assert_match = re.search(r'assert\s*\(([^)]+)\)', line)
                if assert_match:
                    condition = assert_match.group(1).strip()
                    
                    # Check if assertion looks suspicious
                    if self._is_suspicious_assertion(condition):
                        finding = DetectorFinding(
                            detector_id=self.detector_id,
                            title="Potentially Failing Assertion",
                            description=f"Assertion '{condition}' may fail under certain conditions",
                            severity=Severity.MEDIUM,
                            confidence=0.6,
                            file_path=file_path,
                            line_number=line_num,
                            code_snippet=self._extract_code_snippet(source, line_num),
                            remediation="Review assertion conditions and ensure they hold for all valid inputs",
                            references=self.metadata.references,
                            category=self.metadata.category
                        )
                        findings.append(finding)
        
        return findings
    
    def _extract_property_functions(self, source: str) -> List[Dict[str, Any]]:
        """Extract property function definitions."""
        properties = []
        lines = source.split('\n')
        
        # Pattern for property functions
        property_pattern = r'function\s+(echidna_\w+|invariant_\w+)\s*\([^)]*\)\s*.*returns\s*\(\s*bool\s*\)'
        
        for line_num, line in enumerate(lines, 1):
            match = re.search(property_pattern, line)
            if match:
                func_name = match.group(1)
                
                # Extract function body
                func_body = self._extract_function_body_from_line(source, line_num)
                
                properties.append({
                    'name': func_name,
                    'line': line_num,
                    'body': func_body
                })
        
        return properties
    
    def _extract_function_body_from_line(self, source: str, line_num: int) -> str:
        """Extract function body starting from a specific line."""
        lines = source.split('\n')
        
        # Find opening brace
        start_line = line_num - 1
        while start_line < len(lines):
            if '{' in lines[start_line]:
                break
            start_line += 1
        
        if start_line >= len(lines):
            return ""
        
        # Find closing brace
        brace_count = 0
        body_lines = []
        
        for i in range(start_line, len(lines)):
            line = lines[i]
            body_lines.append(line)
            
            brace_count += line.count('{') - line.count('}')
            
            if brace_count == 0 and '{' in lines[start_line]:
                break
        
        return '\n'.join(body_lines)
    
    def _can_return_false(self, func_body: str) -> bool:
        """Check if function body can return false."""
        # Look for patterns that return false
        patterns = [
            r'return\s+false',
            r'return\s+!',
            r'return\s+\w+\s*==\s*false',
            r'return\s+.*\s*<\s*',
            r'return\s+.*\s*>\s*',
            r'return\s+.*\s*!=\s*'
        ]
        
        for pattern in patterns:
            if re.search(pattern, func_body):
                return True
        
        return False
    
    def _is_suspicious_assertion(self, condition: str) -> bool:
        """Check if an assertion condition looks suspicious."""
        # Assertions that compare non-constants might fail
        suspicious_patterns = [
            r'\w+\s*[<>]=?\s*\w+',  # Comparisons
            r'\w+\s*==\s*\w+',       # Equality checks between variables
            r'\w+\s*!=\s*\w+',       # Inequality checks
        ]
        
        # But not if comparing to constants
        if re.search(r'\s*(==|!=|<|>)\s*\d+', condition):
            return False
        
        for pattern in suspicious_patterns:
            if re.search(pattern, condition):
                return True
        
        return False
    
    def _get_remediation(self) -> str:
        """Get remediation advice."""
        return ("Review the conditions that cause property functions to fail. "
                "Ensure that invariants are properly maintained throughout the contract lifecycle. "
                "Consider using formal verification tools for critical properties.")
    
    def _get_remediation_for_property(self, property_name: str) -> str:
        """Get specific remediation for a property."""
        if 'balance' in property_name.lower():
            return ("Ensure that balance invariants are maintained. "
                   "Check that all balance operations (transfers, mints, burns) preserve the expected properties.")
        elif 'owner' in property_name.lower():
            return ("Verify that ownership properties are preserved. "
                   "Ensure owner can only be changed through authorized functions.")
        elif 'supply' in property_name.lower():
            return ("Check that total supply invariants hold. "
                   "Verify that minting and burning operations maintain correct supply accounting.")
        else:
            return self._get_remediation()
