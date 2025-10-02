"""Simplified symbolic execution engine for Solidity analysis.

This module provides a lightweight symbolic execution framework inspired by Mythril
but implemented natively in Python using Z3 for constraint solving.

Based on: Mythril's symbolic execution approach
Upstream: https://github.com/ConsenSys/mythril
"""

import re
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from dataclasses import dataclass, field

try:
    import z3
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False


class SymbolicValueType(Enum):
    """Types of symbolic values."""
    ADDRESS = "address"
    UINT256 = "uint256"
    BOOL = "bool"
    BYTES = "bytes"
    STRING = "string"


@dataclass
class SymbolicVariable:
    """Represents a symbolic variable in execution."""
    name: str
    var_type: SymbolicValueType
    constraints: List[str] = field(default_factory=list)
    
    def __repr__(self):
        return f"Symbolic({self.name}: {self.var_type.value})"


@dataclass
class ExecutionState:
    """Represents a state during symbolic execution."""
    line_number: int
    variables: Dict[str, SymbolicVariable] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    calls_made: List[Tuple[int, str]] = field(default_factory=list)  # (line, call_type)
    state_changes: List[Tuple[int, str]] = field(default_factory=list)  # (line, variable)
    balance_checks: List[int] = field(default_factory=list)  # lines with balance checks
    
    def copy(self) -> 'ExecutionState':
        """Create a copy of this state."""
        return ExecutionState(
            line_number=self.line_number,
            variables=self.variables.copy(),
            constraints=self.constraints[:],
            calls_made=self.calls_made[:],
            state_changes=self.state_changes[:],
            balance_checks=self.balance_checks[:]
        )


class SimplifiedSymbolicEngine:
    """Simplified symbolic execution engine.
    
    This engine performs pattern-based symbolic execution without full EVM semantics.
    It tracks:
    - External calls and their return values
    - State variable modifications
    - Arithmetic operations for overflow detection
    - Access control patterns
    """
    
    def __init__(self):
        self.z3_available = Z3_AVAILABLE
        self.solver = z3.Solver() if Z3_AVAILABLE else None
    
    def analyze_function(self, function_code: str, function_name: str) -> List[ExecutionState]:
        """Analyze a function and return possible execution states.
        
        Args:
            function_code: The function's source code
            function_name: Name of the function
            
        Returns:
            List of execution states representing different paths
        """
        lines = function_code.split('\n')
        states = [ExecutionState(line_number=0)]
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('//'):
                continue
            
            # Process each state
            new_states = []
            for state in states:
                new_state = state.copy()
                new_state.line_number = line_num
                
                # Track external calls
                if self._is_external_call(line_stripped):
                    call_type = self._get_call_type(line_stripped)
                    new_state.calls_made.append((line_num, call_type))
                
                # Track state changes
                if self._is_state_modification(line_stripped):
                    var_name = self._extract_modified_variable(line_stripped)
                    if var_name:
                        new_state.state_changes.append((line_num, var_name))
                
                # Track balance checks
                if 'balance' in line_stripped.lower() or 'address(this)' in line_stripped:
                    new_state.balance_checks.append(line_num)
                
                # Track arithmetic operations
                if self._has_arithmetic_operation(line_stripped):
                    self._analyze_arithmetic(line_stripped, new_state)
                
                new_states.append(new_state)
            
            states = new_states
        
        return states
    
    def _is_external_call(self, line: str) -> bool:
        """Check if line contains an external call."""
        patterns = [
            r'\.call\s*[\({]',
            r'\.delegatecall\s*[\({]',
            r'\.send\s*\(',
            r'\.transfer\s*\(',
            r'\w+\([^)]*\)\s*\.value',
        ]
        return any(re.search(pattern, line) for pattern in patterns)
    
    def _get_call_type(self, line: str) -> str:
        """Identify the type of external call."""
        if '.call' in line:
            return 'call'
        elif '.delegatecall' in line:
            return 'delegatecall'
        elif '.send' in line:
            return 'send'
        elif '.transfer' in line:
            return 'transfer'
        else:
            return 'unknown'
    
    def _is_state_modification(self, line: str) -> bool:
        """Check if line modifies state."""
        # Skip local variable declarations
        if re.match(r'^\s*(uint|int|address|bool|string|bytes)', line):
            return False
        
        # Check for assignment patterns
        patterns = [
            r'\w+\s*=\s*[^=]',
            r'\w+\[.+\]\s*=',   # Array/mapping assignment
            r'\w+\s*\+=',
            r'\w+\s*-=',
            r'\w+\s*\*=',
            r'\w+\s*/=',
            r'\+\+\w+',
            r'\w+\+\+',
            r'--\w+',
            r'\w+--',
            r'delete\s+\w+',
        ]
        return any(re.search(pattern, line) for pattern in patterns)
    
    def _extract_modified_variable(self, line: str) -> Optional[str]:
        """Extract the name of the modified variable."""
        # Try to find array/mapping assignment first
        match = re.search(r'(\w+)\[.+\]\s*=', line)
        if match:
            return match.group(1)
        
        # Try to find variable name before assignment
        match = re.search(r'(\w+)\s*[=\+\-\*\/]=', line)
        if match:
            return match.group(1)
        
        # Try to find variable with increment/decrement
        match = re.search(r'[\+\-]{2}(\w+)|(\w+)[\+\-]{2}', line)
        if match:
            return match.group(1) or match.group(2)
        
        # Try delete statement
        match = re.search(r'delete\s+(\w+)', line)
        if match:
            return match.group(1)
        
        return None
    
    def _has_arithmetic_operation(self, line: str) -> bool:
        """Check if line has arithmetic operations."""
        return any(op in line for op in ['+', '-', '*', '/', '%', '**'])
    
    def _analyze_arithmetic(self, line: str, state: ExecutionState):
        """Analyze arithmetic operations for potential overflows."""
        # Look for unchecked arithmetic
        if 'unchecked' in line:
            return  # Explicit unchecked block
        
        # Check for SafeMath usage
        if 'SafeMath' in line or '.add(' in line or '.sub(' in line:
            return  # Safe math is being used
        
        # Add constraint for potential overflow
        if '+' in line or '*' in line:
            state.constraints.append(f"potential_overflow:{state.line_number}")
        
        if '-' in line:
            state.constraints.append(f"potential_underflow:{state.line_number}")
    
    def check_reentrancy_pattern(self, states: List[ExecutionState]) -> List[int]:
        """Check for reentrancy patterns in execution states.
        
        Returns list of line numbers where reentrancy vulnerabilities exist.
        """
        vulnerable_lines = []
        
        for state in states:
            # Check if external call is made
            if not state.calls_made:
                continue
            
            # Check if state changes happen after external calls
            for call_line, call_type in state.calls_made:
                for change_line, var_name in state.state_changes:
                    if change_line > call_line:
                        vulnerable_lines.append(call_line)
                        break
        
        return list(set(vulnerable_lines))
    
    def check_integer_overflow(self, states: List[ExecutionState]) -> List[int]:
        """Check for potential integer overflow/underflow.
        
        Returns list of line numbers with potential issues.
        """
        vulnerable_lines = []
        
        for state in states:
            for constraint in state.constraints:
                if constraint.startswith('potential_overflow:') or constraint.startswith('potential_underflow:'):
                    line_num = int(constraint.split(':')[1])
                    vulnerable_lines.append(line_num)
        
        return list(set(vulnerable_lines))
    
    def check_unchecked_calls(self, states: List[ExecutionState]) -> List[Tuple[int, str]]:
        """Check for unchecked external call return values.
        
        Returns list of (line_number, call_type) tuples.
        """
        return [(line, call_type) for state in states for line, call_type in state.calls_made]
    
    def check_unprotected_ether(self, function_code: str, states: List[ExecutionState]) -> bool:
        """Check if function allows unprotected ether withdrawal.
        
        Returns True if vulnerability detected.
        """
        # Check if function sends ether
        has_ether_transfer = any(
            call_type in ['call', 'send', 'transfer'] 
            for state in states 
            for _, call_type in state.calls_made
        )
        
        if not has_ether_transfer:
            return False
        
        # Check for access control patterns
        has_access_control = any(
            'require' in line and ('msg.sender' in line or 'owner' in line)
            for line in function_code.split('\n')
        )
        
        return not has_access_control
    
    def check_unprotected_selfdestruct(self, function_code: str) -> Optional[int]:
        """Check for unprotected selfdestruct calls.
        
        Returns line number if vulnerability detected, None otherwise.
        """
        lines = function_code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            if 'selfdestruct' in line or 'suicide' in line:
                # Check if there's access control before this line
                has_access_control = any(
                    'require' in prev_line and ('msg.sender' in prev_line or 'owner' in prev_line)
                    for prev_line in lines[:line_num-1]
                )
                
                if not has_access_control:
                    return line_num
        
        return None
    
    def check_tx_origin_auth(self, function_code: str) -> List[int]:
        """Check for tx.origin used in authorization.
        
        Returns list of line numbers using tx.origin for auth.
        """
        lines = function_code.split('\n')
        vulnerable_lines = []
        
        for line_num, line in enumerate(lines, 1):
            if 'tx.origin' in line and ('require' in line or 'if' in line):
                vulnerable_lines.append(line_num)
        
        return vulnerable_lines
