# Native Mythril Symbolic Execution

BabaYaga now includes a native Python implementation of Mythril's symbolic execution capabilities that works without requiring the external Mythril binary.

## Overview

The native Mythril implementation provides:

- **Symbolic Execution Engine**: Lightweight Z3-based symbolic execution for Solidity
- **SWC Vulnerability Detection**: Implements 6 major SWC (Smart Contract Weakness) patterns
- **No External Dependencies**: Works without installing Mythril binary
- **Hybrid Mode**: Automatic fallback to external Mythril if needed
- **Full Integration**: Seamlessly works with existing orchestrators and agents

## Quick Start

### Using Native Mythril Module

```python
from babayaga.modules.native_mythril_module import NativeMythrilModule
from rich.console import Console

console = Console()
module = NativeMythrilModule(console)

# Quick analysis
findings = await module.run_quick_analysis("MyContract.sol")

# With progress tracking
from rich.progress import Progress

with Progress() as progress:
    task_id = progress.add_task("[cyan]Analyzing...", total=100)
    findings = await module.run_analysis("MyContract.sol", progress, task_id)
```

### Using Mythril Adapter

```python
from babayaga.core.adapters import MythrilAdapter
from rich.console import Console
from pathlib import Path

console = Console()
adapter = MythrilAdapter(console, prefer_native=True)

# Run analysis on repository
findings = await adapter.run(Path("./contracts"))
```

### Using Regular Mythril Module (Hybrid Mode)

```python
from babayaga.modules.mythril_module import MythrilModule
from rich.console import Console

console = Console()
module = MythrilModule(console, prefer_native=True)  # Uses native by default

# Falls back to binary if native fails
findings = await module.run_analysis("MyContract.sol", progress, task_id)
```

## Supported Vulnerabilities

### SWC-101: Integer Overflow/Underflow

Detects arithmetic operations that could overflow or underflow.

**Example:**
```solidity
pragma solidity ^0.7.0;

contract Vulnerable {
    uint256 public total;
    
    function add(uint256 amount) public {
        total = total + amount;  // ❌ Can overflow
    }
}
```

**Detection:** ✅ Symbolic execution analyzes arithmetic operations
**Severity:** High

---

### SWC-104: Unchecked Call Return Value

Detects external calls whose return values are not checked.

**Example:**
```solidity
function sendEther(address payable recipient) public {
    recipient.call{value: 1 ether}("");  // ❌ Return value not checked
}
```

**Detection:** ✅ Tracks external calls and return value usage
**Severity:** Medium

---

### SWC-105: Unprotected Ether Withdrawal

Detects functions that can send ether without access controls.

**Example:**
```solidity
function withdraw(address payable recipient, uint256 amount) public {
    recipient.call{value: amount}("");  // ❌ No access control
}
```

**Detection:** ✅ Analyzes ether transfers and access control patterns
**Severity:** High

---

### SWC-106: Unprotected Selfdestruct

Detects selfdestruct calls without access controls.

**Example:**
```solidity
function kill() public {
    selfdestruct(payable(msg.sender));  // ❌ No access control
}
```

**Detection:** ✅ Identifies unprotected contract destruction
**Severity:** Critical

---

### SWC-107: Reentrancy

Detects reentrancy vulnerabilities where state is modified after external calls.

**Example:**
```solidity
function withdraw() public {
    uint256 amount = balances[msg.sender];
    msg.sender.call{value: amount}("");  // ❌ External call first
    balances[msg.sender] = 0;             // ❌ State change after
}
```

**Detection:** ✅ Symbolic execution tracks call ordering
**Severity:** High

---

### SWC-115: Authorization via tx.origin

Detects use of tx.origin for authentication (vulnerable to phishing).

**Example:**
```solidity
function restrictedFunction() public {
    require(tx.origin == owner);  // ❌ Vulnerable to phishing
}
```

**Detection:** ✅ Identifies tx.origin in authorization contexts
**Severity:** Medium

---

## Configuration

### Prefer Native Implementation

By default, the native implementation is preferred:

```python
# Explicitly use native
module = MythrilModule(console, prefer_native=True)
adapter = MythrilAdapter(console, prefer_native=True)

# Force external binary
module = MythrilModule(console, prefer_native=False)
```

### Hybrid Mode

In hybrid mode, the system tries native first and falls back to external:

```python
module = MythrilModule(console, prefer_native=True)
findings = await module.run_analysis(target, progress, task_id)
# Automatically tries native, then binary if native fails
```

## Architecture

### Symbolic Execution Engine

The native implementation uses a simplified symbolic execution approach:

```
┌─────────────────────────────────────┐
│   Solidity Source Code              │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│   Function Extraction               │
│   - Parse function definitions      │
│   - Extract function bodies         │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│   Symbolic Execution                │
│   - Track external calls            │
│   - Track state modifications       │
│   - Track arithmetic operations     │
│   - Use Z3 for constraints          │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│   Vulnerability Detection           │
│   - Reentrancy patterns             │
│   - Overflow/underflow              │
│   - Access control issues           │
│   - Unchecked calls                 │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│   Findings Report                   │
│   - SWC classification              │
│   - Severity and confidence         │
│   - Code snippets                   │
│   - Remediation advice              │
└─────────────────────────────────────┘
```

### Detector Architecture

Each detector implements the `BaseDetector` interface:

```python
class IntegerOverflowDetector(BaseDetector):
    def get_metadata(self) -> DetectorMetadata:
        """Return metadata about this detector."""
        return DetectorMetadata(
            detector_id="native-mythril-integer-overflow",
            source_tool="mythril",
            source_version="0.24.8",
            swc_id="SWC-101",
            # ...
        )
    
    async def analyze(self, contract_source: str, 
                     file_path: str) -> List[DetectorFinding]:
        """Analyze contract for vulnerabilities."""
        # Implementation using symbolic engine
```

## Performance

### Native vs External Comparison

| Aspect | Native | External (Binary) |
|--------|--------|------------------|
| **Startup Time** | ~0.1s | ~2-3s |
| **Analysis Speed** | Fast for common patterns | Slower but more thorough |
| **Memory Usage** | Low | Medium-High |
| **Accuracy** | Good for major patterns | Excellent |
| **Installation** | No external deps | Requires Mythril binary |

### When to Use Each

**Use Native When:**
- Quick analysis needed
- No Mythril binary available
- Analyzing simple contracts
- Running in CI/CD pipelines
- Checking common vulnerabilities

**Use External When:**
- Need comprehensive analysis
- Complex control flow
- Analyzing deployed contracts
- Maximum accuracy required

## Testing

All native detectors have comprehensive unit tests:

```bash
# Run Mythril detector tests
pytest tests/unit/test_native_mythril_detectors.py -v

# Run all native detector tests
pytest tests/unit/test_native_*.py -v
```

## Troubleshooting

### Z3 Not Available

If Z3 is not available, install it:

```bash
pip install z3-solver
```

The symbolic engine will still work without Z3 but with reduced capabilities.

### Native Analysis Fails

The system automatically falls back to external Mythril:

```python
# Hybrid mode handles this automatically
module = MythrilModule(console, prefer_native=True)
findings = await module.run_analysis(target, progress, task_id)
# Will try native first, then binary
```

### Force External Binary

```python
module = MythrilModule(console, prefer_native=False)
# Will skip native and use binary directly
```

## Limitations

The native implementation has some limitations compared to full Mythril:

1. **Simplified Symbolic Execution**: Uses pattern-based analysis rather than full EVM semantics
2. **No Blockchain State**: Cannot analyze deployed contracts or blockchain state
3. **Limited Path Exploration**: Focuses on common vulnerability patterns
4. **No SMT Optimization**: Simpler constraint solving than full Mythril

For comprehensive analysis, consider using the external Mythril binary or hybrid mode.

## Contributing

To add new Mythril-based detectors:

1. Create detector in `babayaga/native/mythril_detectors/`
2. Implement `get_metadata()` and `analyze()` methods
3. Register in `babayaga/native/native_engine.py`
4. Add tests in `tests/unit/test_native_mythril_detectors.py`
5. Update `DETECTORS_MANIFEST.json`
6. Update documentation

See [NATIVE_ANALYSIS.md](./NATIVE_ANALYSIS.md) for detailed contributing guide.

## References

- [Mythril Documentation](https://mythril-classic.readthedocs.io/)
- [SWC Registry](https://swcregistry.io/)
- [Z3 Theorem Prover](https://github.com/Z3Prover/z3)
- [SWC Mapping Documentation](./SWC_MAPPING.md)
