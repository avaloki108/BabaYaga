# Native Security Analysis

BabaYaga now includes native implementations of security analysis capabilities from leading tools (Slither, Mythril, Medusa, Securify2) that work without requiring their binaries.

## Overview

The native analysis system provides several key benefits:

1. **No External Dependencies**: Run security checks without installing Slither, Mythril, etc.
2. **Easy Updates**: Track which upstream tool versions each detector is based on
3. **Hybrid Mode**: Use native implementations alongside external tools
4. **Faster Execution**: No subprocess overhead
5. **Better Integration**: Direct access to findings and metadata

## Quick Start

### Using Native Analysis

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

### Using Hybrid Mode

The hybrid module can use native implementations, external tools, or both:

```python
from babayaga.modules.hybrid_slither_module import HybridSlitherModule

# Uses configuration from native_config.toml
module = HybridSlitherModule(console)

# Run analysis (automatically selects native or external)
findings = await module.run_analysis(target, progress, task_id)
```

### CLI Usage

```bash
# Analyze a contract
python -m babayaga.native.cli analyze ./contracts/

# List available detectors
python -m babayaga.native.cli list-detectors

# Show version information
python -m babayaga.native.cli version-info

# Export version manifest
python -m babayaga.native.cli export-manifest versions.json
```

## Configuration

Configuration is managed through `babayaga/config/native_config.toml`:

```toml
[native_analysis]
enabled = true          # Enable native analysis
prefer_native = true    # Use native when available
hybrid_mode = false     # Run both native and external

[slither]
use_native = true                # Use native Slither detectors
fallback_to_binary = true        # Fall back to binary if needed
enabled_detectors = []           # Specific detectors to enable
disabled_detectors = []          # Specific detectors to disable
```

## Architecture

### Detector Structure

Each detector implements the `BaseDetector` interface:

```python
class MyDetector(BaseDetector):
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-my-detector",
            name="My Security Check",
            description="Detects XYZ vulnerability",
            source_tool="slither",
            source_version="0.10.0",  # Upstream version
            source_detector_id="my-detector",
            severity=Severity.HIGH,
            confidence=0.9,
            category=DetectorCategory.REENTRANCY,
            swc_id="SWC-XXX",
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source, file_path, additional_context):
        # Implementation
        findings = []
        # ... analyze code ...
        return findings
```

### Version Tracking

Version tracking is managed through:

1. **DetectorMetadata**: Each detector includes:
   - `source_tool`: The original tool (e.g., "slither")
   - `source_version`: Upstream tool version
   - `source_detector_id`: ID in the upstream tool
   - `last_updated`: Date of last sync

2. **DETECTORS_MANIFEST.json**: Central manifest tracking:
   - All implemented detectors
   - Their upstream versions
   - Implementation files
   - Planned detectors

3. **Registry**: The detector registry provides:
   - `get_version_info()`: Get all version information
   - `export_version_manifest()`: Export manifest file

## Updating Detectors

When upstream tools release new versions, follow this process:

### 1. Check Current Versions

```bash
python -m babayaga.native.cli version-info
```

This shows which detectors need updating.

### 2. Review Upstream Changes

Check the upstream tool's changelog:
- **Slither**: https://github.com/crytic/slither/releases
- **Mythril**: https://github.com/ConsenSys/mythril/releases
- **Securify2**: https://github.com/eth-sri/securify2/releases
- **Medusa**: https://github.com/crytic/medusa/releases

### 3. Update Detector Implementation

Modify the detector file to match upstream changes:

```python
# babayaga/native/slither_detectors/my_detector.py

def get_metadata(self) -> DetectorMetadata:
    return DetectorMetadata(
        # ... other fields ...
        source_version="0.11.0",  # Update this
        last_updated="2024-02-01"  # Update this
    )

async def analyze(self, contract_source, file_path, additional_context):
    # Update analysis logic based on upstream changes
    pass
```

### 4. Update Manifest

Update `babayaga/native/DETECTORS_MANIFEST.json`:

```json
{
  "detector_id": "native-my-detector",
  "source_version": "0.11.0",
  "last_updated": "2024-02-01"
}
```

### 5. Test Changes

```bash
# Run detector tests
pytest tests/unit/test_native_detectors.py

# Validate with real contracts
python -m babayaga.native.cli analyze ./test_contracts/
```

### 6. Cross-Validate

Compare results with the upstream tool:

```bash
# Run both native and external
# Set hybrid_mode = true in config

# Check for differences
python -m babayaga.native.cli analyze ./contracts/ --output native_results.json
slither ./contracts/ --json external_results.json

# Compare outputs
python scripts/compare_results.py native_results.json external_results.json
```

## Implemented Detectors

### Slither Detectors (3 implemented)

| Detector ID | Name | Upstream ID | Version | Status |
|-------------|------|-------------|---------|--------|
| native-reentrancy-eth | Reentrancy Vulnerability | reentrancy-eth | 0.10.0 | ✅ Active |
| native-tx-origin | Dangerous tx.origin Usage | tx-origin | 0.10.0 | ✅ Active |
| native-unchecked-call | Unchecked External Call | unchecked-lowlevel | 0.10.0 | ✅ Active |

### Planned Detectors

See `babayaga/native/DETECTORS_MANIFEST.json` for the complete roadmap:

**Slither** (10 planned):
- arbitrary-send-eth
- suicidal
- uninitialized-state
- controlled-delegatecall
- timestamp
- weak-prng
- ... and more

**Mythril** (5 planned):
- integer-overflow
- integer-underflow
- delegatecall-to-untrusted
- unprotected-selfdestruct
- state-change-external-calls

**Securify2** (3 planned):
- dao-vulnerability
- locked-ether
- unrestricted-write

**Medusa** (3 planned):
- invariant-violations
- assertion-failures
- property-violations

## Adding New Detectors

### Step 1: Create Detector Class

Create a new file in the appropriate directory:

```python
# babayaga/native/slither_detectors/my_new_detector.py

from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)

class MyNewDetector(BaseDetector):
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-my-new-detector",
            name="My New Security Check",
            description="Detects XYZ vulnerability",
            source_tool="slither",
            source_version="0.10.0",
            source_detector_id="my-new-detector",
            severity=Severity.HIGH,
            confidence=0.9,
            category=DetectorCategory.ACCESS_CONTROL,
            references=["https://..."],
            swc_id="SWC-XXX",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source, file_path, additional_context):
        findings = []
        # Implement detection logic
        return findings
```

### Step 2: Register Detector

Add to `babayaga/native/slither_detectors/__init__.py`:

```python
from .my_new_detector import MyNewDetector

__all__ = [
    # ... existing detectors ...
    'MyNewDetector',
]
```

Register in `babayaga/native/native_engine.py`:

```python
def _initialize_detectors(self):
    # ... existing registrations ...
    self.registry.register(MyNewDetector)
```

### Step 3: Add Tests

Create tests in `tests/unit/test_native_detectors.py`:

```python
class TestMyNewDetector:
    @pytest.mark.asyncio
    async def test_detect_vulnerability(self):
        detector = MyNewDetector()
        
        vulnerable_code = """
        // Code with vulnerability
        """
        
        findings = await detector.analyze(vulnerable_code, "test.sol")
        assert len(findings) >= 1
```

### Step 4: Update Manifest

Add to `DETECTORS_MANIFEST.json`:

```json
{
  "detector_id": "native-my-new-detector",
  "name": "My New Security Check",
  "upstream_detector_id": "my-new-detector",
  "source_version": "0.10.0",
  "last_updated": "2024-01-15",
  "implementation_file": "babayaga/native/slither_detectors/my_new_detector.py",
  "status": "active"
}
```

## Best Practices

### 1. Always Track Versions

Include accurate version information in detector metadata:

```python
DetectorMetadata(
    source_tool="slither",
    source_version="0.10.0",  # Match upstream
    last_updated="2024-01-15"  # Date of sync
)
```

### 2. Document Limitations

If your implementation differs from upstream, document it:

```python
class MyDetector(BaseDetector):
    """Detects XYZ vulnerability.
    
    Note: This is a simplified pattern-based implementation.
    The upstream tool uses full AST analysis. For complete
    accuracy, consider using hybrid mode.
    """
```

### 3. Use Hybrid Mode for Validation

During development, use hybrid mode to validate:

```toml
[native_analysis]
hybrid_mode = true  # Run both native and external
```

### 4. Add Comprehensive Tests

Test both positive and negative cases:

```python
async def test_detect_vulnerability():
    # Should detect issue
    findings = await detector.analyze(vulnerable_code, "test.sol")
    assert len(findings) >= 1

async def test_no_false_positive():
    # Should NOT detect issue in safe code
    findings = await detector.analyze(safe_code, "test.sol")
    assert len(findings) == 0
```

### 5. Regular Updates

Set up a schedule to check for upstream updates:

```bash
# Monthly check
python -m babayaga.native.cli version-info

# Check upstream releases
# Slither: https://github.com/crytic/slither/releases
# etc.
```

## Troubleshooting

### Issue: Detector not finding vulnerabilities

**Solution**: Check if your patterns match the actual code:

```python
# Add debug output
print(f"Analyzing line: {line}")
print(f"Pattern match: {bool(re.search(pattern, line))}")
```

### Issue: Too many false positives

**Solution**: Refine detection patterns:

```python
# Add context checking
if self._is_vulnerability(line) and self._is_in_correct_context(line):
    # Report finding
```

### Issue: Version mismatch warnings

**Solution**: Update detector to match upstream version:

1. Check upstream changelog
2. Update detector logic if needed
3. Update `source_version` and `last_updated`

## Performance Considerations

### Native vs External

- **Native**: Faster for multiple small checks, no subprocess overhead
- **External**: More accurate for complex analysis (AST, control flow)
- **Hybrid**: Best accuracy, runs both for validation

### Optimization Tips

1. **Batch Processing**: Analyze multiple files in parallel
2. **Selective Detectors**: Disable unnecessary detectors
3. **Caching**: Cache results for unchanged files
4. **Progressive Analysis**: Run quick checks first, deep analysis later

## Contributing

We welcome contributions of new detectors! See the main CONTRIBUTING.md guide and follow these detector-specific guidelines:

1. Ensure detector is based on a recognized upstream tool
2. Include accurate version tracking
3. Add comprehensive tests
4. Document any limitations or differences from upstream
5. Update DETECTORS_MANIFEST.json

## Resources

- **Native Analysis README**: `babayaga/native/README.md`
- **Detector Manifest**: `babayaga/native/DETECTORS_MANIFEST.json`
- **Configuration**: `babayaga/config/native_config.toml`
- **Tests**: `tests/unit/test_native_detectors.py`

### Upstream Tool Documentation

- **Slither**: https://github.com/crytic/slither/wiki/Detector-Documentation
- **Mythril**: https://mythril-classic.readthedocs.io/
- **SWC Registry**: https://swcregistry.io/
- **Smart Contract Best Practices**: https://consensys.github.io/smart-contract-best-practices/
