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
├── securify2_detectors/      # Native Securify2 implementations
│   ├── integer_overflow.py
│   ├── uninitialized_storage.py
│   ├── missing_access_control.py
│   ├── timestamp_dependence.py
│   ├── unsafe_delegatecall.py
│   ├── unprotected_selfdestruct.py
│   └── locked_ether.py
├── mythril_detectors/        # Native Mythril implementations (planned)
└── medusa_detectors/         # Native Medusa implementations (planned)
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

## Implemented Detectors

### Slither-Based Detectors
- **Reentrancy Detection**: Detects reentrancy vulnerabilities (SWC-107)
- **tx.origin Usage**: Detects dangerous use of tx.origin for authorization (SWC-115)
- **Unchecked Calls**: Detects unchecked return values from low-level calls (SWC-104)

### Securify2-Based Detectors (Datalog-Inspired)
- **Integer Overflow/Underflow**: Detects unchecked arithmetic operations (SWC-101)
- **Uninitialized Storage**: Detects uninitialized storage pointers (SWC-109)
- **Missing Access Control**: Detects state-changing functions without access control (SWC-105)
- **Timestamp Dependence**: Detects reliance on block.timestamp (SWC-116)
- **Unsafe Delegatecall**: Detects delegatecall to untrusted addresses (SWC-112)
- **Unprotected Selfdestruct**: Detects selfdestruct without access control (SWC-106)
- **Locked Ether**: Detects contracts that can receive but not withdraw ether (SWC-132)

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

### Phase 2: Securify2 Detectors ✓
- [x] Integer overflow/underflow detection
- [x] Uninitialized storage pointer detection
- [x] Missing access control detection
- [x] Timestamp dependence detection
- [x] Unsafe delegatecall detection
- [x] Unprotected selfdestruct detection
- [x] Locked ether detection
- [ ] Additional Securify2 patterns (DAO vulnerability, unrestricted write, etc.)

### Phase 3: Mythril Detectors
- [ ] Delegatecall to untrusted callee
- [ ] State change after external calls
- [ ] Additional Mythril detectors

### Phase 4: Medusa Integration
- [ ] Invariant checking (Medusa-style)
- [ ] Property-based testing integration

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

## Resources

- **Slither Detectors**: https://github.com/crytic/slither/wiki/Detector-Documentation
- **Mythril Docs**: https://mythril-classic.readthedocs.io/
- **SWC Registry**: https://swcregistry.io/
- **Smart Contract Best Practices**: https://consensys.github.io/smart-contract-best-practices/
