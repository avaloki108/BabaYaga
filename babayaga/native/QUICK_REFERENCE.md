# Native Detectors Quick Reference

## Check Versions

```bash
python -m babayaga.native.cli version-info
```

## Update Workflow

```bash
# 1. Check upstream
curl -s https://api.github.com/repos/crytic/slither/releases/latest | jq .tag_name

# 2. Update detector code
# Edit: babayaga/native/slither_detectors/my_detector.py
# Change: source_version="X.Y.Z" and last_updated="YYYY-MM-DD"

# 3. Test
pytest tests/unit/test_native_detectors.py

# 4. Validate with hybrid mode
# Set hybrid_mode=true in babayaga/config/native_config.toml
python -m babayaga.native.cli analyze ./test_contracts/
```

## Usage

```python
# Native only
from babayaga.native.native_engine import NativeAnalysisEngine
engine = NativeAnalysisEngine(console)
result = await engine.analyze_project("./contracts/")

# Hybrid mode
from babayaga.modules.hybrid_slither_module import HybridSlitherModule
module = HybridSlitherModule(console)
findings = await module.run_analysis(target, progress, task_id)
```

## Adding New Detector

```python
# 1. Create detector class
class MyDetector(BaseDetector):
    def get_metadata(self):
        return DetectorMetadata(
            detector_id="native-my-detector",
            source_tool="slither",
            source_version="0.10.0",
            last_updated="2024-01-15",
            # ... other fields
        )
    
    async def analyze(self, source, file_path, context):
        # Implementation
        return findings

# 2. Register in native_engine.py
self.registry.register(MyDetector)

# 3. Add to DETECTORS_MANIFEST.json

# 4. Write tests
```

## File Locations

| File | Purpose |
|------|---------|
| `babayaga/native/base_detector.py` | Base classes |
| `babayaga/native/detector_registry.py` | Registry |
| `babayaga/native/native_engine.py` | Engine |
| `babayaga/native/slither_detectors/` | Slither detectors |
| `babayaga/native/DETECTORS_MANIFEST.json` | Version tracking |
| `babayaga/config/native_config.toml` | Configuration |
| `tests/unit/test_native_detectors.py` | Tests |
| `docs/NATIVE_ANALYSIS.md` | Full documentation |
| `docs/UPDATING_DETECTORS.md` | Update guide |

## Detector Template

```python
from ..base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)

class MyDetector(BaseDetector):
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            detector_id="native-my-id",
            name="My Detector",
            description="What it detects",
            source_tool="slither",           # or mythril, securify2, medusa
            source_version="0.10.0",         # Upstream version
            source_detector_id="upstream-id",
            severity=Severity.HIGH,
            confidence=0.9,
            category=DetectorCategory.REENTRANCY,
            references=["https://..."],
            swc_id="SWC-XXX",
            enabled_by_default=True,
            last_updated="2024-01-15"
        )
    
    async def analyze(self, contract_source, file_path, additional_context):
        findings = []
        lines = contract_source.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            if self._is_vulnerable(line):
                finding = DetectorFinding(
                    detector_id=self.detector_id,
                    title="Vulnerability found",
                    description="Details...",
                    severity=self.metadata.severity,
                    confidence=self.metadata.confidence,
                    file_path=file_path,
                    line_number=line_num,
                    code_snippet=self._extract_code_snippet(contract_source, line_num),
                    remediation="How to fix...",
                    references=self.metadata.references,
                    swc_id=self.metadata.swc_id,
                    category=self.metadata.category
                )
                findings.append(finding)
        
        return findings
    
    def _is_vulnerable(self, line: str) -> bool:
        # Detection logic
        return False
```

## CLI Commands

```bash
# Analyze
python -m babayaga.native.cli analyze ./contracts/ --output results.json

# List detectors
python -m babayaga.native.cli list-detectors

# Version info
python -m babayaga.native.cli version-info

# Export manifest
python -m babayaga.native.cli export-manifest versions.json
```

## Configuration

```toml
# babayaga/config/native_config.toml

[native_analysis]
enabled = true           # Enable native analysis
prefer_native = true     # Use native when available
hybrid_mode = false      # Run both native and external

[slither]
use_native = true                # Use native Slither detectors
fallback_to_binary = true        # Fall back if needed
```

## Testing

```bash
# Run all tests
pytest tests/unit/test_native_detectors.py

# Run specific detector test
pytest tests/unit/test_native_detectors.py::TestMyDetector -v

# With coverage
pytest tests/unit/test_native_detectors.py --cov=babayaga.native
```

## Upstream Resources

| Tool | Repository | Documentation |
|------|------------|---------------|
| Slither | [crytic/slither](https://github.com/crytic/slither) | [Wiki](https://github.com/crytic/slither/wiki/Detector-Documentation) |
| Mythril | [ConsenSys/mythril](https://github.com/ConsenSys/mythril) | [Docs](https://mythril-classic.readthedocs.io/) |
| Securify2 | [eth-sri/securify2](https://github.com/eth-sri/securify2) | [Repo](https://github.com/eth-sri/securify2) |
| Medusa | [crytic/medusa](https://github.com/crytic/medusa) | [Repo](https://github.com/crytic/medusa) |

## Severity Levels

| Level | Use When | Example |
|-------|----------|---------|
| Critical | Immediate exploit, funds at risk | Unprotected ether withdrawal |
| High | Serious vulnerability | Reentrancy with state changes |
| Medium | Moderate risk | tx.origin for auth |
| Low | Minor issue | Deprecated functions |
| Info | Good practice | Missing NatSpec |

## Category Values

```python
DetectorCategory.REENTRANCY
DetectorCategory.ACCESS_CONTROL
DetectorCategory.ARITHMETIC
DetectorCategory.EXTERNAL_CALLS
DetectorCategory.TIMESTAMP
DetectorCategory.RANDOMNESS
DetectorCategory.DELEGATECALL
DetectorCategory.SELFDESTRUCT
DetectorCategory.STORAGE
DetectorCategory.DEPRECATED
DetectorCategory.GAS_OPTIMIZATION
DetectorCategory.CODE_QUALITY
DetectorCategory.LOGIC_ERRORS
```

## Common Patterns

```python
# External call detection
r'\.call\s*\(|\.delegatecall\s*\(|\.send\s*\(|\.transfer\s*\('

# State changes
r'\w+\s*=\s*[^=]|\.push\(|\.pop\(|delete\s+\w+'

# Authorization
r'require\s*\([^)]*msg\.sender|onlyOwner|isAuthorized'

# tx.origin usage
r'tx\.origin\s*==|tx\.origin\s*!='

# Timestamp dependence
r'block\.timestamp|now\s*[<>=]'

# Weak randomness
r'block\.(timestamp|difficulty|number|blockhash)'
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Import error | `pip install -e .` in repo root |
| Detector not found | Check registration in `native_engine.py` |
| Tests failing | Ensure pytest-asyncio installed |
| Version mismatch | Update `source_version` in metadata |
| False positives | Refine detection patterns, add context checks |

## Quick Links

- 📘 Full Documentation: [docs/NATIVE_ANALYSIS.md](../../docs/NATIVE_ANALYSIS.md)
- 🔄 Update Guide: [docs/UPDATING_DETECTORS.md](../../docs/UPDATING_DETECTORS.md)
- 📋 Manifest: [DETECTORS_MANIFEST.json](./DETECTORS_MANIFEST.json)
- 🧪 Tests: [tests/unit/test_native_detectors.py](../../tests/unit/test_native_detectors.py)
- ⚙️ Config: [babayaga/config/native_config.toml](../config/native_config.toml)
