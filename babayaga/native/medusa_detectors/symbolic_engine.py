"""Symbolic execution engine for smart contract analysis.

This module provides lightweight symbolic execution capabilities for
analyzing smart contracts. Inspired by Medusa's symbolic analysis approach.

Based on: Medusa's symbolic execution engine
Upstream: https://github.com/crytic/medusa
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple
from enum import Enum


class SymbolicValueType(Enum):
    """Types of symbolic values."""
    UINT = "uint"
    INT = "int"
    ADDRESS = "address"
    BOOL = "bool"
    BYTES = "bytes"
    STRING = "string"
    MAPPING = "mapping"
    ARRAY = "array"


@dataclass
class SymbolicValue:
    """Represents a symbolic value in execution.
    
    Symbolic values track possible states and constraints during analysis.
    """
    name: str
    value_type: SymbolicValueType
    constraints: List[str] = field(default_factory=list)
    concrete_value: Optional[Any] = None
    is_symbolic: bool = True
    
    def add_constraint(self, constraint: str):
        """Add a constraint to this symbolic value."""
        self.constraints.append(constraint)
    
    def can_be_zero(self) -> bool:
        """Check if this value can be zero."""
        if not self.is_symbolic and self.concrete_value is not None:
            return self.concrete_value == 0
        
        # Check constraints
        for constraint in self.constraints:
            if '!= 0' in constraint or '> 0' in constraint:
                return False
        return True
    
    def can_overflow(self) -> bool:
        """Check if this value can overflow."""
        if self.value_type in [SymbolicValueType.UINT, SymbolicValueType.INT]:
            return True
        return False


@dataclass
class SymbolicState:
    """Represents the state of the contract during symbolic execution."""
    storage: Dict[str, SymbolicValue] = field(default_factory=dict)
    balances: Dict[str, SymbolicValue] = field(default_factory=dict)
    msg_sender: Optional[SymbolicValue] = None
    msg_value: Optional[SymbolicValue] = None
    block_timestamp: Optional[SymbolicValue] = None
    path_constraints: List[str] = field(default_factory=list)
    call_depth: int = 0
    revert_conditions: List[str] = field(default_factory=list)
    
    def clone(self) -> 'SymbolicState':
        """Create a deep copy of this state."""
        new_state = SymbolicState()
        new_state.storage = self.storage.copy()
        new_state.balances = self.balances.copy()
        new_state.msg_sender = self.msg_sender
        new_state.msg_value = self.msg_value
        new_state.block_timestamp = self.block_timestamp
        new_state.path_constraints = self.path_constraints.copy()
        new_state.call_depth = self.call_depth
        new_state.revert_conditions = self.revert_conditions.copy()
        return new_state
    
    def add_path_constraint(self, constraint: str):
        """Add a constraint to the current execution path."""
        self.path_constraints.append(constraint)
    
    def is_satisfiable(self) -> bool:
        """Check if the current path constraints are satisfiable.
        
        This is a simplified check - a full implementation would use an SMT solver.
        """
        # Look for obvious contradictions
        for i, c1 in enumerate(self.path_constraints):
            for c2 in self.path_constraints[i+1:]:
                if self._are_contradictory(c1, c2):
                    return False
        return True
    
    def _are_contradictory(self, c1: str, c2: str) -> bool:
        """Check if two constraints contradict each other."""
        # Simple pattern matching for obvious contradictions
        # E.g., "x > 0" and "x == 0" or "x < 0"
        var_pattern = r'(\w+)\s*([<>=!]+)\s*(\d+)'
        
        m1 = re.search(var_pattern, c1)
        m2 = re.search(var_pattern, c2)
        
        if m1 and m2:
            var1, op1, val1 = m1.groups()
            var2, op2, val2 = m2.groups()
            
            if var1 == var2:
                # Check for obvious contradictions
                if op1 == '==' and op2 == '!=' and val1 == val2:
                    return True
                if op1 == '>' and op2 == '<=' and val1 >= val2:
                    return True
        
        return False


class SymbolicExecutionEngine:
    """Lightweight symbolic execution engine for smart contract analysis.
    
    This engine performs symbolic execution to:
    - Track state changes
    - Identify potential vulnerabilities
    - Check invariants
    - Detect property violations
    
    Based on Medusa's symbolic execution approach.
    """
    
    def __init__(self):
        self.initial_state = SymbolicState()
        self.execution_paths: List[SymbolicState] = []
        self.max_depth = 10
        self.max_paths = 100
        
    def analyze_contract(self, contract_source: str, 
                        entry_function: Optional[str] = None) -> List[SymbolicState]:
        """Perform symbolic execution on a contract.
        
        Args:
            contract_source: Solidity source code
            entry_function: Optional specific function to analyze
            
        Returns:
            List of execution paths (final states)
        """
        self.execution_paths = []
        
        # Extract contract structure
        functions = self._extract_functions(contract_source)
        state_vars = self._extract_state_variables(contract_source)
        
        # Initialize symbolic state with state variables
        initial_state = SymbolicState()
        for var_name, var_type in state_vars.items():
            initial_state.storage[var_name] = SymbolicValue(
                name=var_name,
                value_type=self._map_type(var_type),
                is_symbolic=True
            )
        
        # Analyze each function or specific entry function
        target_functions = [f for f in functions if f['name'] == entry_function] if entry_function else functions
        
        for func in target_functions:
            if func['visibility'] in ['public', 'external']:
                self._execute_function(func, initial_state, contract_source)
        
        return self.execution_paths
    
    def _extract_functions(self, source: str) -> List[Dict[str, Any]]:
        """Extract function definitions from contract source."""
        functions = []
        
        # Pattern to match function declarations
        func_pattern = r'function\s+(\w+)\s*\([^)]*\)\s*(public|external|internal|private)?\s*(view|pure|payable)?'
        
        for match in re.finditer(func_pattern, source):
            functions.append({
                'name': match.group(1),
                'visibility': match.group(2) or 'public',
                'modifiers': match.group(3) or '',
                'start_pos': match.start()
            })
        
        return functions
    
    def _extract_state_variables(self, source: str) -> Dict[str, str]:
        """Extract state variable declarations."""
        state_vars = {}
        
        # Pattern for state variable declarations
        var_pattern = r'(uint\d*|int\d*|address|bool|bytes\d*|string|mapping\([^)]+\))\s+(public|private|internal)?\s*(\w+)\s*;'
        
        for match in re.finditer(var_pattern, source):
            var_type = match.group(1)
            var_name = match.group(3)
            state_vars[var_name] = var_type
        
        return state_vars
    
    def _map_type(self, solidity_type: str) -> SymbolicValueType:
        """Map Solidity type to SymbolicValueType."""
        if 'uint' in solidity_type:
            return SymbolicValueType.UINT
        elif 'int' in solidity_type:
            return SymbolicValueType.INT
        elif 'address' in solidity_type:
            return SymbolicValueType.ADDRESS
        elif 'bool' in solidity_type:
            return SymbolicValueType.BOOL
        elif 'bytes' in solidity_type:
            return SymbolicValueType.BYTES
        elif 'string' in solidity_type:
            return SymbolicValueType.STRING
        elif 'mapping' in solidity_type:
            return SymbolicValueType.MAPPING
        else:
            return SymbolicValueType.BYTES
    
    def _execute_function(self, func: Dict[str, Any], 
                         initial_state: SymbolicState, 
                         source: str):
        """Symbolically execute a function.
        
        This is a simplified symbolic execution that tracks:
        - State variable changes
        - External calls
        - Branch conditions
        - Reverts and assertions
        """
        # Initialize execution with function entry state
        current_state = initial_state.clone()
        current_state.msg_sender = SymbolicValue(
            name='msg.sender',
            value_type=SymbolicValueType.ADDRESS,
            is_symbolic=True
        )
        
        # Extract function body
        func_body = self._extract_function_body(source, func['start_pos'])
        
        # Analyze function body for state changes
        self._analyze_function_body(func_body, current_state)
        
        # Add to execution paths if not too many
        if len(self.execution_paths) < self.max_paths:
            self.execution_paths.append(current_state)
    
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
    
    def _analyze_function_body(self, body: str, state: SymbolicState):
        """Analyze function body for state changes and operations."""
        lines = body.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Track assignments to state variables
            assignment_match = re.search(r'(\w+)\s*=\s*(.+);', line)
            if assignment_match:
                var_name = assignment_match.group(1)
                if var_name in state.storage:
                    # State variable assignment
                    state.storage[var_name] = SymbolicValue(
                        name=var_name,
                        value_type=state.storage[var_name].value_type,
                        is_symbolic=True
                    )
            
            # Track require statements
            require_match = re.search(r'require\s*\(([^)]+)\)', line)
            if require_match:
                condition = require_match.group(1)
                state.add_path_constraint(condition)
                state.revert_conditions.append(f"NOT({condition})")
            
            # Track assert statements
            assert_match = re.search(r'assert\s*\(([^)]+)\)', line)
            if assert_match:
                condition = assert_match.group(1)
                state.add_path_constraint(condition)
            
            # Track balance operations
            if 'balance' in line.lower():
                # Track balance changes
                pass
            
            # Track external calls
            if '.call' in line or '.delegatecall' in line or '.send' in line:
                state.call_depth += 1
