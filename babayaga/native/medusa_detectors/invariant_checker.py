"""Invariant checking framework for symbolic analysis.

This module provides the base framework for checking various types of
invariants in smart contracts using symbolic execution.

Based on: Medusa's invariant checking approach
Upstream: https://github.com/crytic/medusa
"""

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable

from .symbolic_engine import SymbolicExecutionEngine, SymbolicState, SymbolicValue


class InvariantType(Enum):
    """Types of invariants that can be checked."""
    CONSERVATION = "conservation"  # Balance/supply conservation
    PERMISSION = "permission"      # Access control
    LIVENESS = "liveness"          # State reachability
    PROPERTY = "property"          # Custom properties


@dataclass
class InvariantViolation:
    """Represents a detected invariant violation."""
    invariant_type: InvariantType
    description: str
    violated_condition: str
    execution_path: SymbolicState
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    severity: str = "High"
    remediation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            'invariant_type': self.invariant_type.value,
            'description': self.description,
            'violated_condition': self.violated_condition,
            'line_number': self.line_number,
            'function_name': self.function_name,
            'severity': self.severity,
            'remediation': self.remediation,
            'path_constraints': self.execution_path.path_constraints
        }


class InvariantChecker:
    """Base class for invariant checking.
    
    This class provides the framework for checking various invariants
    on smart contracts using symbolic execution.
    """
    
    def __init__(self):
        self.symbolic_engine = SymbolicExecutionEngine()
        self.violations: List[InvariantViolation] = []
    
    def check_invariants(self, contract_source: str, 
                        invariant_type: InvariantType) -> List[InvariantViolation]:
        """Check invariants of a specific type on the contract.
        
        Args:
            contract_source: Solidity source code
            invariant_type: Type of invariant to check
            
        Returns:
            List of detected violations
        """
        self.violations = []
        
        # Perform symbolic execution
        execution_paths = self.symbolic_engine.analyze_contract(contract_source)
        
        # Check each path for violations
        for path in execution_paths:
            if invariant_type == InvariantType.CONSERVATION:
                self._check_conservation_invariants(path, contract_source)
            elif invariant_type == InvariantType.PERMISSION:
                self._check_permission_invariants(path, contract_source)
            elif invariant_type == InvariantType.LIVENESS:
                self._check_liveness_invariants(path, contract_source)
            elif invariant_type == InvariantType.PROPERTY:
                self._check_property_invariants(path, contract_source)
        
        return self.violations
    
    def _check_conservation_invariants(self, state: SymbolicState, source: str):
        """Check conservation invariants (balances, supply, etc.)."""
        # Look for balance tracking variables
        for var_name, var_value in state.storage.items():
            if 'balance' in var_name.lower() or 'supply' in var_name.lower():
                # Check if balance can be negative
                if var_value.can_be_zero() and 'balance' in var_name.lower():
                    # This is acceptable for balances
                    pass
                
                # Check for potential underflow
                if var_value.can_overflow():
                    self.violations.append(InvariantViolation(
                        invariant_type=InvariantType.CONSERVATION,
                        description=f"Variable '{var_name}' may overflow/underflow, "
                                  f"violating conservation of {var_name}",
                        violated_condition=f"{var_name} overflow check",
                        execution_path=state,
                        severity="High",
                        remediation="Use SafeMath library or Solidity 0.8+ for arithmetic operations"
                    ))
    
    def _check_permission_invariants(self, state: SymbolicState, source: str):
        """Check permission/access control invariants."""
        # Check if msg.sender is constrained
        if state.msg_sender and state.msg_sender.is_symbolic:
            # Look for functions that modify critical state without access control
            for var_name in state.storage:
                if any(keyword in var_name.lower() for keyword in ['owner', 'admin', 'authorized']):
                    # Check if there are constraints on msg.sender
                    sender_constrained = any(
                        'msg.sender' in constraint 
                        for constraint in state.path_constraints
                    )
                    
                    if not sender_constrained:
                        self.violations.append(InvariantViolation(
                            invariant_type=InvariantType.PERMISSION,
                            description=f"Critical variable '{var_name}' can be modified without "
                                      f"proper access control",
                            violated_condition=f"msg.sender access check for {var_name}",
                            execution_path=state,
                            severity="High",
                            remediation="Add access control modifiers (onlyOwner, etc.) to sensitive functions"
                        ))
    
    def _check_liveness_invariants(self, state: SymbolicState, source: str):
        """Check liveness invariants (reachability, non-stuck states)."""
        # Check for states that always revert
        if len(state.revert_conditions) > 0:
            # Analyze if any execution path can complete without reverting
            all_paths_revert = len(state.path_constraints) == len(state.revert_conditions)
            
            if all_paths_revert:
                self.violations.append(InvariantViolation(
                    invariant_type=InvariantType.LIVENESS,
                    description="Function has no reachable non-reverting execution path",
                    violated_condition="All paths lead to revert",
                    execution_path=state,
                    severity="Medium",
                    remediation="Review require/assert conditions for potential deadlock"
                ))
    
    def _check_property_invariants(self, state: SymbolicState, source: str):
        """Check custom property invariants defined in the contract."""
        # Look for invariant functions (echidna_*, invariant_*)
        invariant_pattern = r'function\s+(echidna_\w+|invariant_\w+)\s*\([^)]*\)\s*.*returns\s*\(\s*bool\s*\)'
        
        for match in re.finditer(invariant_pattern, source):
            property_name = match.group(1)
            
            # Extract the property function body
            func_start = match.start()
            func_body = self._extract_function_body(source, func_start)
            
            # Simple heuristic: if the property function can return false, flag it
            if 'return false' in func_body or 'return !' in func_body:
                self.violations.append(InvariantViolation(
                    invariant_type=InvariantType.PROPERTY,
                    description=f"Property '{property_name}' may be violated",
                    violated_condition=f"{property_name} can return false",
                    execution_path=state,
                    severity="High",
                    remediation="Review the conditions that cause this property to fail"
                ))
    
    def _extract_function_body(self, source: str, start_pos: int) -> str:
        """Extract function body from source."""
        # Find the opening brace
        open_brace = source.find('{', start_pos)
        if open_brace == -1:
            return ""
        
        # Find matching closing brace
        brace_count = 1
        pos = open_brace + 1
        while pos < len(source) and brace_count > 0:
            if source[pos] == '{':
                brace_count += 1
            elif source[pos] == '}':
                brace_count -= 1
            pos += 1
        
        return source[open_brace:pos]


class InvariantRegistry:
    """Registry for custom invariant checkers."""
    
    def __init__(self):
        self.checkers: Dict[str, Callable] = {}
    
    def register(self, name: str, checker: Callable):
        """Register a custom invariant checker."""
        self.checkers[name] = checker
    
    def get_checker(self, name: str) -> Optional[Callable]:
        """Get a registered checker by name."""
        return self.checkers.get(name)
    
    def list_checkers(self) -> List[str]:
        """List all registered checker names."""
        return list(self.checkers.keys())
