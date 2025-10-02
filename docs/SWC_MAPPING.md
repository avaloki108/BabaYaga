# SWC (Smart Contract Weakness Classification) Mapping

This document maps the native Mythril symbolic execution detectors to their corresponding SWC IDs and provides coverage information.

## Supported SWC Detections

### SWC-101: Integer Overflow and Underflow

**Detector:** `native-mythril-integer-overflow`

**Coverage:** Full

**Description:** Detects arithmetic operations that could overflow or underflow, potentially causing unexpected behavior or security vulnerabilities.

**Detection Method:** Symbolic execution analysis of arithmetic operations

**Conditions Checked:**
- Addition operations that could overflow
- Subtraction operations that could underflow
- Multiplication operations that could overflow
- Considers Solidity version (0.8.0+ has built-in protection)
- Recognizes SafeMath library usage

**Example Vulnerability:**
```solidity
pragma solidity ^0.7.0;

contract Vulnerable {
    uint256 public total;
    
    function add(uint256 amount) public {
        total = total + amount;  // Can overflow
    }
}
```

**Remediation:**
- Use Solidity 0.8.0 or higher (built-in overflow protection)
- Use OpenZeppelin's SafeMath library
- Add explicit overflow checks

---

### SWC-107: Reentrancy

**Detector:** `native-mythril-reentrancy`

**Coverage:** Full

**Description:** Detects reentrancy vulnerabilities where external calls are made before state changes, allowing malicious contracts to re-enter and exploit the contract.

**Detection Method:** Symbolic execution tracking of external calls and state modifications

**Conditions Checked:**
- External calls (call, delegatecall, send, transfer)
- State modifications after external calls
- Function visibility (public/external)
- Reentrancy guard presence

**Example Vulnerability:**
```solidity
contract Vulnerable {
    mapping(address => uint256) public balances;
    
    function withdraw() public {
        uint256 amount = balances[msg.sender];
        msg.sender.call{value: amount}("");  // External call first
        balances[msg.sender] = 0;             // State change after
    }
}
```

**Remediation:**
- Use checks-effects-interactions pattern (update state before external calls)
- Use OpenZeppelin's ReentrancyGuard
- Use transfer() or send() instead of call() where appropriate

---

### SWC-104: Unchecked Call Return Value

**Detector:** `native-mythril-unchecked-call`

**Coverage:** Full

**Description:** Detects external calls whose return values are not checked, which can lead to silent failures.

**Detection Method:** Symbolic execution identifying unchecked low-level calls

**Conditions Checked:**
- Low-level calls (call, delegatecall, send)
- Return value capture and validation
- Require/assert statements following calls

**Example Vulnerability:**
```solidity
contract Vulnerable {
    function sendEther(address payable recipient) public {
        recipient.call{value: 1 ether}("");  // Return value not checked
    }
}
```

**Remediation:**
- Always check return values: `(bool success, ) = recipient.call{value: amount}(""); require(success);`
- Use transfer() which reverts on failure
- Add proper error handling

---

### SWC-105: Unprotected Ether Withdrawal

**Detector:** `native-mythril-unprotected-ether`

**Coverage:** Full

**Description:** Detects functions that can send ether to arbitrary addresses without proper access controls.

**Detection Method:** Symbolic execution analyzing ether transfer functions and access control patterns

**Conditions Checked:**
- Functions that send ether
- Presence of access control (require statements with msg.sender/owner)
- Function visibility

**Example Vulnerability:**
```solidity
contract Vulnerable {
    function withdraw(address payable recipient, uint256 amount) public {
        recipient.call{value: amount}("");  // No access control
    }
}
```

**Remediation:**
- Add access control: `require(msg.sender == owner);`
- Use OpenZeppelin's Ownable contract
- Implement withdrawal patterns with proper authorization

---

### SWC-106: Unprotected SELFDESTRUCT Instruction

**Detector:** `native-mythril-unprotected-selfdestruct`

**Coverage:** Full

**Description:** Detects selfdestruct calls that lack proper access controls, allowing anyone to destroy the contract.

**Detection Method:** Symbolic execution identifying selfdestruct/suicide calls without authorization

**Conditions Checked:**
- Presence of selfdestruct or suicide
- Access control before selfdestruct
- Function visibility

**Example Vulnerability:**
```solidity
contract Vulnerable {
    function kill() public {
        selfdestruct(payable(msg.sender));  // No access control
    }
}
```

**Remediation:**
- Add strict access control: `require(msg.sender == owner);`
- Consider removing selfdestruct entirely
- Use upgradeable patterns instead

---

### SWC-115: Authorization through tx.origin

**Detector:** `native-mythril-tx-origin`

**Coverage:** Full

**Description:** Detects use of tx.origin for authentication, which is vulnerable to phishing attacks.

**Detection Method:** Symbolic execution identifying tx.origin in authorization contexts

**Conditions Checked:**
- tx.origin usage in require/if statements
- Context of authorization checks

**Example Vulnerability:**
```solidity
contract Vulnerable {
    address owner;
    
    function restrictedFunction() public {
        require(tx.origin == owner);  // Vulnerable to phishing
        // ...
    }
}
```

**Remediation:**
- Use msg.sender instead of tx.origin
- Never use tx.origin for authorization

---

## Coverage Summary

| SWC ID | Title | Detector | Status |
|--------|-------|----------|--------|
| SWC-101 | Integer Overflow/Underflow | native-mythril-integer-overflow | ✅ Active |
| SWC-104 | Unchecked Call Return Value | native-mythril-unchecked-call | ✅ Active |
| SWC-105 | Unprotected Ether Withdrawal | native-mythril-unprotected-ether | ✅ Active |
| SWC-106 | Unprotected SELFDESTRUCT | native-mythril-unprotected-selfdestruct | ✅ Active |
| SWC-107 | Reentrancy | native-mythril-reentrancy | ✅ Active |
| SWC-115 | Authorization via tx.origin | native-mythril-tx-origin | ✅ Active |

## Integration with Checklist

The native Mythril detectors map to the following checklist IDs:

```python
SWC_TO_CHECKLIST = {
    "SWC-101": ["SOL-AM-IntegerOverflow-1"],
    "SWC-104": ["SOL-AM-UncheckedSend-1"],
    "SWC-105": ["SOL-AM-UnprotectedEther-1"],
    "SWC-106": ["SOL-AM-UnprotectedSelfDestruct-1"],
    "SWC-107": ["SOL-AM-ReentrancyAttack-1"],
    "SWC-115": ["SOL-AM-TxOrigin-1"]
}
```

## Comparison with External Mythril

### Advantages of Native Implementation

1. **No External Dependencies:** Works without installing Mythril binary
2. **Faster Execution:** No subprocess overhead
3. **Better Integration:** Direct access to findings and metadata
4. **Consistent Results:** Reproducible across environments
5. **Easy Updates:** Track upstream versions in manifest

### Differences from External Mythril

1. **Simplified Symbolic Execution:** Uses pattern-based analysis rather than full EVM semantics
2. **No Blockchain State:** Doesn't analyze deployed contracts
3. **Focused Coverage:** Implements most critical SWC patterns
4. **Performance:** Faster for common patterns, less comprehensive for complex control flow

### When to Use External Mythril

Consider using the external Mythril binary for:
- Complex control flow analysis
- State space exploration with many paths
- Analysis of deployed contracts
- Full EVM semantics requirements

Set `prefer_native = False` in configuration to use external binary.

## Testing and Validation

All native Mythril detectors have comprehensive unit tests:
- `tests/unit/test_native_mythril_detectors.py`

Cross-validation with external Mythril can be performed using:
```bash
# Run both native and external
python scripts/compare_mythril_results.py ./contracts/
```

## Contributing

To add new Mythril-based detectors:

1. Create detector class in `babayaga/native/mythril_detectors/`
2. Implement `get_metadata()` and `analyze()` methods
3. Register in `babayaga/native/native_engine.py`
4. Add tests in `tests/unit/test_native_mythril_detectors.py`
5. Update `DETECTORS_MANIFEST.json` with SWC mapping
6. Update this documentation

## References

- [SWC Registry](https://swcregistry.io/)
- [Mythril Documentation](https://mythril-classic.readthedocs.io/)
- [Mythril GitHub](https://github.com/ConsenSys/mythril)
- [Smart Contract Security Field Guide](https://scsfg.io/)
