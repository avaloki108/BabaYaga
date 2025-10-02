# Native Security Analysis Implementation

This package contains native implementations of security analysis capabilities from leading tools (Slither, Mythril, Medusa, Securify2) without depending on their binaries.

## Overview

The native analysis system provides:

1. **Binary-Free Analysis**: Run security checks without external tool dependencies
2. **Version Tracking**: Each detector tracks its upstream tool version
3. **Easy Updates**: Clear mapping to upstream detectors for synchronization
4. **Hybrid Mode**: Can work alongside external tools or independently
5. **Extensibility**: Framework supports custom detectors

## Architecture

```
babayaga/native/
├── base_detector.py          # Base classes for all detectors
├── detector_registry.py      # Central registry for detector management
├── native_engine.py          # Analysis orchestration engine
├── DETECTORS_MANIFEST.json   # Version tracking manifest
├── slither_detectors/        # Native Slither detector implementations
│   ├── reentrancy.py
│   ├── tx_origin.py
│   └── unchecked_call.py
├── mythril_detectors/        # Native Mythril implementations (planned)
├── medusa_detectors/         # Native Medusa implementations (planned)
└── securify2_detectors/      # Native Securify2 implementations (planned)
```

## Using Native Analysis

### Basic Usage

```python
from rich.console import Console
from babayaga.native.native_engine import NativeAnalysisEngine

console = Console()
engine = NativeAnalysisEngine(console)

# Analyze a single file
result = await engine.analyze_file("MyContract.sol")

# Analyze a project
result = await engine.analyze_project("./contracts/")
```

### With Configuration

```python
config = {
    'only_enabled': True,  # Only run enabled detectors
    'detectors': ['native-reentrancy-eth', 'native-tx-origin'],  # Specific detectors
}

result = await engine.analyze_project("./contracts/", config)
```

### Detector Registry

```python
from babayaga.native.detector_registry import get_registry

registry = get_registry()

# Get all detectors
all_detectors = registry.get_all_detectors()

# Get detectors from specific tool
slither_detectors = registry.get_detectors_by_tool('slither')

# Get version information
version_info = registry.get_version_info()

# Export version manifest
registry.export_version_manifest('detector_versions.json')
```

## Implementing New Detectors

### 1. Create Detector Class

```python
from babayaga.native.base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)

class MyDetector(BaseDetector):
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-my-detector",
            name="My Security Check",
            description="Detects XYZ vulnerability",
            source_tool="slither",  # or mythril, securify2, medusa
            source_version="0.10.0",  # Upstream version
            source_detector_id="my-detector",  # ID in upstream tool
            severity=Severity.HIGH,
            confidence=0.9,
            category=DetectorCategory.REENTRANCY,
            references=["https://..."],
            swc_id="SWC-XXX",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source: str, file_path: str,
                     additional_context=None) -> List[DetectorFinding]:
        findings = []
        # Implementation here
        return findings
```

### 2. Register Detector

```python
from babayaga.native.detector_registry import register_detector

register_detector(MyDetector)
```

### 3. Update Manifest

Add entry to `DETECTORS_MANIFEST.json`:

```json
{
  "detector_id": "native-my-detector",
  "name": "My Security Check",
  "upstream_detector_id": "my-detector",
  "source_version": "0.10.0",
  "last_updated": "2024-01-15",
  "implementation_file": "babayaga/native/.../my_detector.py",
  "status": "active"
}
```

## Syncing with Upstream Tools

### Updating Detectors

When upstream tools (Slither, Mythril, etc.) release new versions:

1. **Check DETECTORS_MANIFEST.json**: Review which detectors need updating
2. **Review Upstream Changes**: Check the upstream tool's changelog
3. **Update Detector Code**: Modify the detector implementation
4. **Update Metadata**: Change `source_version` and `last_updated` in detector
5. **Update Manifest**: Update the manifest file
6. **Test**: Verify the detector works with new patterns
7. **Cross-Validate**: Compare results with the upstream tool

### Example Update Process

```bash
# 1. Check current versions
cat babayaga/native/DETECTORS_MANIFEST.json

# 2. Review upstream changes
# Visit https://github.com/crytic/slither/releases

# 3. Update detector implementation
# Edit babayaga/native/slither_detectors/reentrancy.py

# 4. Update metadata in detector
# Change source_version and last_updated fields

# 5. Run tests
pytest tests/unit/test_native_detectors.py

# 6. Export new manifest
python -c "
from babayaga.native.native_engine import NativeAnalysisEngine
from rich.console import Console
engine = NativeAnalysisEngine(Console())
engine.export_version_manifest('DETECTORS_MANIFEST.json')
"
```

## Detector Categories

- **REENTRANCY**: Reentrancy vulnerabilities
- **ACCESS_CONTROL**: Authorization and access control issues
- **ARITHMETIC**: Integer overflow/underflow
- **EXTERNAL_CALLS**: Issues with external calls
- **TIMESTAMP**: Timestamp dependence
- **RANDOMNESS**: Weak randomness
- **DELEGATECALL**: Delegatecall issues
- **SELFDESTRUCT**: Selfdestruct vulnerabilities
- **STORAGE**: Storage issues
- **DEPRECATED**: Deprecated functions
- **GAS_OPTIMIZATION**: Gas optimization opportunities
- **CODE_QUALITY**: Code quality issues
- **LOGIC_ERRORS**: Logic errors

## Severity Levels

- **CRITICAL**: Immediate threat, likely to be exploited
- **HIGH**: Serious vulnerability, should be fixed ASAP
- **MEDIUM**: Moderate risk, should be addressed
- **LOW**: Minor issue, good practice to fix
- **INFO**: Informational, no immediate risk

## Benefits of Native Implementation

1. **No External Dependencies**: Works without installing Slither/Mythril binaries
2. **Faster Execution**: No subprocess overhead
3. **Better Integration**: Direct access to findings and metadata
4. **Customization**: Easy to extend and customize detectors
5. **Version Control**: Track exactly which tool versions are implemented
6. **Hybrid Usage**: Can complement external tools for comprehensive coverage

## Roadmap

### Phase 1: Slither Detectors ✓
- [x] Reentrancy detection
- [x] tx.origin usage
- [x] Unchecked calls
- [ ] Additional Slither detectors (see DETECTORS_MANIFEST.json)

### Phase 2: Mythril Detectors
- [ ] Integer overflow/underflow
- [ ] Unprotected selfdestruct
- [ ] Delegatecall to untrusted callee
- [ ] Additional Mythril detectors

### Phase 3: Medusa & Securify2
- [x] Invariant checking (Medusa-style)
  - [x] Conservation invariants (balance/supply tracking)
  - [x] Permission invariants (access control)
  - [x] Liveness invariants (state reachability)
  - [x] Property violation detection
- [ ] Datalog patterns (Securify2-style)
- [x] Property-based testing integration

### Phase 4: Advanced Features
- [ ] AST-based analysis (more accurate than regex)
- [ ] Control flow analysis
- [ ] Data flow tracking
- [ ] Symbolic execution integration

## Contributing

When adding new detectors:

1. Follow the existing detector structure
2. Include comprehensive metadata with upstream version
3. Add tests for the detector
4. Update DETECTORS_MANIFEST.json
5. Document any patterns or limitations
6. Cross-validate with upstream tool if possible

## Medusa-Style Symbolic Analysis

The native engine now includes Medusa-inspired symbolic analysis and invariant checking:

### Conservation Invariants (`native-medusa-conservation`)

Detects violations of conservation laws:
- Balance conservation (sum of balances should not change unexpectedly)
- Supply conservation (total supply tracking)
- Token conservation (tokens shouldn't appear/disappear)

**Example violation:**
```solidity
function mint(address to, uint256 amount) public {
    balances[to] += amount;
    // Missing: totalSupply += amount;
}
```

### Permission Invariants (`native-medusa-permissions`)

Detects missing or improper access control:
- Critical functions without access control
- Improper owner/admin checks
- Unauthorized state modifications

**Example violation:**
```solidity
function setOwner(address newOwner) public {
    owner = newOwner;  // Missing: require(msg.sender == owner);
}
```

### Liveness Invariants (`native-medusa-liveness`)

Detects deadlocks and unreachable states:
- Functions that always revert
- Unreachable code paths
- Stuck states

**Example violation:**
```solidity
function withdraw() public {
    require(paused == false);
    require(balance > 0);
    require(msg.sender == owner);
    // If all three conditions are never true together, function is deadlocked
}
```

### Property Violations (`native-medusa-properties`)

Detects violations of custom properties:
- echidna_* property functions
- invariant_* functions
- Custom assertions

**Example property:**
```solidity
function echidna_balance_conservation() public view returns (bool) {
    return totalSupply == sumOfBalances();
}
```

## Symbolic Execution Engine

The symbolic execution engine provides:
- **Symbolic State Tracking**: Track possible states and constraints
- **Path Exploration**: Explore execution paths symbolically
- **Constraint Solving**: Identify satisfiable/unsatisfiable conditions
- **Invariant Verification**: Check invariants across execution paths

### Limitations

- **Simplified SMT Solving**: Uses pattern matching instead of full SMT solver
- **Limited Loop Unrolling**: Deep loops may not be fully analyzed
- **Heuristic-Based**: Some checks use heuristics rather than complete symbolic analysis
- **No External Calls**: External contract interactions are approximated

### Future Enhancements

- Integration with Z3 or other SMT solvers
- More sophisticated path exploration strategies
- Support for complex data structures (nested mappings, structs)
- Cross-contract symbolic analysis
- Temporal properties (LTL/CTL)

## Resources

- **Slither Detectors**: https://github.com/crytic/slither/wiki/Detector-Documentation
- **Mythril Docs**: https://mythril-classic.readthedocs.io/
- **Medusa**: https://github.com/crytic/medusa
- **Echidna**: https://github.com/crytic/echidna
- **SWC Registry**: https://swcregistry.io/
- **Smart Contract Best Practices**: https://consensys.github.io/smart-contract-best-practices/
