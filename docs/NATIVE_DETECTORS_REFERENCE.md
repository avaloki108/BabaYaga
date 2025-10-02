# Native Detectors Reference

This document provides a comprehensive reference for all native security detectors implemented in BabaYaga.

## Overview

BabaYaga includes native implementations of security detectors from leading tools like Slither, Mythril, and others. These detectors run without requiring external tool binaries, providing faster analysis and better integration.

## Supported Detectors

### Slither-Based Detectors (7 implemented)

#### 1. Reentrancy Detector

**ID:** `native-reentrancy-eth`  
**Source:** Slither v0.10.0 (reentrancy-eth)  
**Severity:** High  
**SWC:** SWC-107

**Description:**  
Detects reentrancy vulnerabilities where external calls are made before state changes are complete.

**Vulnerable Pattern:**
```solidity
function withdraw() public {
    uint256 amount = balances[msg.sender];
    msg.sender.call{value: amount}("");  // External call
    balances[msg.sender] = 0;            // State change AFTER call - vulnerable!
}
```

**Safe Pattern:**
```solidity
function withdraw() public {
    uint256 amount = balances[msg.sender];
    balances[msg.sender] = 0;            // State change BEFORE call - safe!
    msg.sender.call{value: amount}("");
}
```

**Remediation:**
- Use the checks-effects-interactions pattern
- Make state changes before external calls
- Use reentrancy guards (e.g., OpenZeppelin's ReentrancyGuard)

---

#### 2. tx.origin Detector

**ID:** `native-tx-origin`  
**Source:** Slither v0.10.0 (tx-origin)  
**Severity:** Medium  
**SWC:** SWC-115

**Description:**  
Detects dangerous usage of `tx.origin` for authorization checks.

**Vulnerable Pattern:**
```solidity
function restrictedFunction() public {
    require(tx.origin == owner, "Not owner");  // Vulnerable to phishing!
    // Critical operation
}
```

**Safe Pattern:**
```solidity
function restrictedFunction() public {
    require(msg.sender == owner, "Not owner");  // Safe!
    // Critical operation
}
```

**Remediation:**
- Replace `tx.origin` with `msg.sender` for authorization
- `msg.sender` represents the immediate caller, not the transaction origin

---

#### 3. Unchecked Call Detector

**ID:** `native-unchecked-call`  
**Source:** Slither v0.10.0 (unchecked-lowlevel)  
**Severity:** Medium  
**SWC:** SWC-104

**Description:**  
Detects external calls whose return values are not checked.

**Vulnerable Pattern:**
```solidity
function sendEther(address payable recipient) public {
    recipient.call{value: 1 ether}("");  // Return value not checked!
}
```

**Safe Pattern:**
```solidity
function sendEther(address payable recipient) public {
    (bool success, ) = recipient.call{value: 1 ether}("");
    require(success, "Transfer failed");  // Checked!
}
```

**Remediation:**
- Always check return values from low-level calls
- Consider using `transfer()` which reverts automatically
- Use tuple destructuring: `(bool success, ) = addr.call(...)`

---

#### 4. Integer Overflow/Underflow Detector

**ID:** `native-integer-overflow`  
**Source:** Slither v0.10.0 (integer-overflow)  
**Severity:** High  
**SWC:** SWC-101

**Description:**  
Detects arithmetic operations that could overflow or underflow in Solidity < 0.8.0.

**Vulnerable Pattern (Solidity < 0.8.0):**
```solidity
pragma solidity ^0.7.0;

contract Vulnerable {
    uint256 public balance;
    
    function addBalance(uint256 amount) public {
        balance += amount;  // Can overflow!
    }
}
```

**Safe Pattern (Multiple Options):**

Option 1: Use Solidity 0.8.0+
```solidity
pragma solidity ^0.8.0;

contract Safe {
    uint256 public balance;
    
    function addBalance(uint256 amount) public {
        balance += amount;  // Safe - built-in overflow checks!
    }
}
```

Option 2: Use SafeMath (for older Solidity)
```solidity
pragma solidity ^0.7.0;
import "@openzeppelin/contracts/math/SafeMath.sol";

contract Safe {
    using SafeMath for uint256;
    uint256 public balance;
    
    function addBalance(uint256 amount) public {
        balance = balance.add(amount);  // Safe with SafeMath
    }
}
```

**Remediation:**
- Upgrade to Solidity 0.8.0+ (has built-in overflow checks)
- Use SafeMath library for Solidity < 0.8.0
- Use `unchecked` blocks only when you're certain overflow is safe

---

#### 5. Timestamp Dependence Detector

**ID:** `native-timestamp-dependence`  
**Source:** Slither v0.10.0 (timestamp)  
**Severity:** Low-Medium  
**SWC:** SWC-116

**Description:**  
Detects dangerous dependence on `block.timestamp` or `now`.

**Vulnerable Pattern:**
```solidity
function checkDeadline() public view returns (bool) {
    require(block.timestamp < deadline, "Expired");  // Can be manipulated!
    return true;
}

function random() public view returns (uint256) {
    return uint256(keccak256(abi.encodePacked(block.timestamp))) % 100;  // Weak randomness!
}
```

**Safe Pattern:**
```solidity
// For deadlines, allow ~15 second variance
function checkDeadline() public view returns (bool) {
    // OK if the variance doesn't matter
    require(block.timestamp < deadline, "Expired");
    return true;
}

// For randomness, use secure solution
function random() public returns (uint256) {
    // Use Chainlink VRF or other secure randomness source
    requestRandomness(keyHash, fee);
}
```

**Remediation:**
- Avoid using `block.timestamp` for critical logic
- Never use for random number generation
- Use `block.number` for relative time measurements
- Use oracles (e.g., Chainlink VRF) for randomness
- Tolerate ~15 second variance if using for deadlines

---

#### 6. Block Hash Usage Detector (Weak Randomness)

**ID:** `native-block-hash-usage`  
**Source:** Slither v0.10.0 (weak-prng)  
**Severity:** High  
**SWC:** SWC-120

**Description:**  
Detects use of block properties for random number generation.

**Vulnerable Pattern:**
```solidity
function random() public view returns (uint256) {
    // All of these are predictable and manipulable!
    return uint256(blockhash(block.number - 1)) % 100;
    // or: block.timestamp, block.difficulty, block.number
}
```

**Safe Pattern:**
```solidity
import "@chainlink/contracts/src/v0.8/VRFConsumerBase.sol";

contract SafeRandom is VRFConsumerBase {
    bytes32 internal keyHash;
    uint256 internal fee;
    
    function getRandomNumber() public returns (bytes32 requestId) {
        require(LINK.balanceOf(address(this)) >= fee, "Not enough LINK");
        return requestRandomness(keyHash, fee);
    }
    
    function fulfillRandomness(bytes32 requestId, uint256 randomness) internal override {
        // Use secure randomness here
    }
}
```

**Remediation:**
- Use Chainlink VRF (Verifiable Random Function)
- Use commit-reveal schemes for user-generated randomness
- Use oracle-based randomness solutions
- Never use block properties for randomness in production

---

#### 7. Access Control Detector

**ID:** `native-access-control`  
**Source:** Slither v0.10.0 (unprotected-upgrade)  
**Severity:** High  
**SWC:** SWC-106

**Description:**  
Detects functions with missing or weak access control on critical operations.

**Vulnerable Pattern:**
```solidity
contract Vulnerable {
    address public owner;
    
    // No access control - anyone can change owner!
    function transferOwnership(address newOwner) public {
        owner = newOwner;
    }
    
    // No access control - anyone can destroy contract!
    function destroy() public {
        selfdestruct(payable(msg.sender));
    }
}
```

**Safe Pattern:**
```solidity
contract Safe {
    address public owner;
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    
    function transferOwnership(address newOwner) public onlyOwner {
        owner = newOwner;
    }
    
    function destroy() public onlyOwner {
        selfdestruct(payable(owner));
    }
}
```

**Remediation:**
- Add access control modifiers to critical functions
- Use OpenZeppelin's Ownable or AccessControl contracts
- Functions that modify state, transfer funds, or change ownership need protection
- Use `require(msg.sender == authorized)` at minimum

---

## Missing/Planned Detectors

The following detectors are planned for future implementation:

### High Priority (Slither)
- `arbitrary-send-eth` - Arbitrary ether transfers
- `suicidal` - Unprotected selfdestruct
- `controlled-delegatecall` - Controlled delegatecall destination
- `uninitialized-state` - Uninitialized state variables

### Medium Priority (Slither)
- `locked-ether` - Contracts that lock ether
- `shadowing-state` - State variable shadowing
- `incorrect-equality` - Dangerous strict equalities
- `assembly-usage` - Assembly usage

### Future (Mythril)
- `delegatecall-to-untrusted` - Delegatecall to untrusted contract
- `unprotected-selfdestruct` - Unprotected selfdestruct
- `state-change-external-calls` - State changes after external calls

### Future (Securify2)
- `dao-vulnerability` - DAO pattern vulnerabilities
- `unrestricted-write` - Unrestricted storage write

## Configuration

### Enabling/Disabling Detectors

In `native_config.toml`:
```toml
[native_analysis]
enabled = true
prefer_native = true

[slither]
use_native = true
enabled_detectors = [
    "native-reentrancy-eth",
    "native-tx-origin",
    "native-unchecked-call",
    "native-integer-overflow",
    "native-timestamp-dependence",
    "native-block-hash-usage",
    "native-access-control"
]
disabled_detectors = []
```

### Using in Code

```python
from babayaga.native.native_engine import NativeAnalysisEngine
from rich.console import Console

console = Console()
engine = NativeAnalysisEngine(console)

# Analyze a single file
result = await engine.analyze_file("MyContract.sol")

# Analyze a project
result = await engine.analyze_project("./contracts/")

# Filter by detector
config = {
    'only_enabled': True,
    'detector_ids': ['native-reentrancy-eth', 'native-tx-origin']
}
result = await engine.analyze_file("MyContract.sol", config)
```

## Performance Comparison

| Tool | Method | Speed | Accuracy | Dependencies |
|------|--------|-------|----------|--------------|
| Native Detectors | Pure Python | Fast | Good | None |
| Slither Binary | Subprocess | Medium | Excellent | Slither |
| Hybrid Mode | Both | Slower | Best | Optional |

**Recommendations:**
- **Development**: Use native detectors for fast feedback
- **CI/CD**: Use hybrid mode for comprehensive coverage
- **Production Audits**: Use hybrid + external tools

## Limitations

### Current Implementation Limitations

1. **Pattern-Based Detection**: Native detectors use regex patterns, not full AST analysis
   - May miss complex control flow scenarios
   - May produce false positives in edge cases

2. **Cross-Contract Analysis**: Limited cross-contract flow analysis
   - Each file analyzed independently
   - May miss inter-contract vulnerabilities

3. **Type Analysis**: Basic type checking only
   - No full type inference
   - May miss type-related issues

### When to Use External Tools

Use external Slither binary when:
- You need 100% accuracy for production audits
- Cross-contract analysis is required
- Complex control flow analysis needed
- Type system analysis required

## Version Tracking

Each detector tracks its upstream tool version:

```python
metadata = detector.get_metadata()
print(f"Source: {metadata.source_tool} v{metadata.source_version}")
print(f"Last updated: {metadata.last_updated}")
```

Check version information:
```bash
python -m babayaga.native.cli version-info
```

Export version manifest:
```bash
python -m babayaga.native.cli export-manifest versions.json
```

## Contributing

To add a new detector:

1. Create detector class in `babayaga/native/slither_detectors/`
2. Implement `get_metadata()` and `analyze()` methods
3. Register in `native_engine.py`
4. Add tests in `tests/unit/test_native_detectors.py`
5. Update this documentation

See [UPDATING_DETECTORS.md](UPDATING_DETECTORS.md) for detailed instructions.

## References

- [Slither Documentation](https://github.com/crytic/slither/wiki/Detector-Documentation)
- [SWC Registry](https://swcregistry.io/)
- [Smart Contract Best Practices](https://consensys.github.io/smart-contract-best-practices/)
- [OpenZeppelin Security](https://docs.openzeppelin.com/contracts/4.x/security)
