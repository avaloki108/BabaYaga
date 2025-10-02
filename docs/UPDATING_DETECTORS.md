# Guide: Updating Native Detectors

This guide explains how to keep native detectors synchronized with upstream tool updates (Slither, Mythril, Medusa, Securify2).

## Why Update?

Upstream security tools regularly improve their detectors:
- Fix false positives/negatives
- Add new detection patterns
- Improve accuracy
- Support new Solidity features

Keeping our native implementations in sync ensures we benefit from these improvements.

## Quick Reference

```bash
# 1. Check current versions
python -m babayaga.native.cli version-info

# 2. Find which detectors need updating
# Compare with upstream tool versions

# 3. Update detector code
# Edit the detector file in babayaga/native/*/

# 4. Update metadata
# Change source_version and last_updated

# 5. Test
pytest tests/unit/test_native_detectors.py

# 6. Validate
# Use hybrid mode to compare with upstream
```

## Detailed Update Process

### Step 1: Identify Detectors to Update

Run the version info command:

```bash
python -m babayaga.native.cli version-info
```

Output shows current implementation versions:

```
SLITHER
Based on slither version 0.10.0

Native Detector              Upstream ID            Last Updated
native-reentrancy-eth        reentrancy-eth         2024-01-15
native-tx-origin             tx-origin              2024-01-15
native-unchecked-call        unchecked-lowlevel     2024-01-15
```

### Step 2: Check Upstream Versions

Visit the upstream tool repositories:

#### Slither
```bash
# Check latest release
curl -s https://api.github.com/repos/crytic/slither/releases/latest | jq .tag_name

# Or visit: https://github.com/crytic/slither/releases
```

#### Mythril
```bash
# Check latest release
curl -s https://api.github.com/repos/ConsenSys/mythril/releases/latest | jq .tag_name

# Or visit: https://github.com/ConsenSys/mythril/releases
```

### Step 3: Review Upstream Changes

For each detector that needs updating:

1. **Find the detector in upstream source**:
   ```bash
   # Example for Slither's reentrancy detector
   # Visit: https://github.com/crytic/slither/blob/master/slither/detectors/reentrancy/reentrancy_eth.py
   ```

2. **Review the changelog**:
   - Look for changes to detection logic
   - Note any new patterns added
   - Check for bug fixes

3. **Identify what changed**:
   - New detection patterns?
   - Modified confidence levels?
   - Different severity classifications?
   - Bug fixes for false positives?

### Step 4: Update Detector Implementation

Edit the detector file:

```python
# Example: babayaga/native/slither_detectors/reentrancy.py

class ReentrancyDetector(BaseDetector):
    def get_metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            # ... other fields ...
            
            # UPDATE THESE:
            source_version="0.11.0",  # Change from "0.10.0" to "0.11.0"
            last_updated="2024-02-01",  # Update to current date
        )
    
    async def analyze(self, contract_source, file_path, additional_context):
        # UPDATE DETECTION LOGIC:
        
        # Example: If upstream added a new pattern
        if self._is_external_call(line) or self._is_low_level_call(line):  # NEW
            external_call_line = line_num
        
        # Rest of the implementation...
```

### Step 5: Update Documentation

Update the detector manifest:

```json
// babayaga/native/DETECTORS_MANIFEST.json
{
  "implemented_detectors": {
    "slither": [
      {
        "detector_id": "native-reentrancy-eth",
        "source_version": "0.11.0",  // UPDATE THIS
        "last_updated": "2024-02-01",  // UPDATE THIS
        "status": "active"
      }
    ]
  }
}
```

Add a changelog entry:

```markdown
// DETECTORS_CHANGELOG.md

## 2024-02-01 - Reentrancy Detector Update

- Updated `native-reentrancy-eth` to match Slither 0.11.0
- Added detection for low-level calls
- Improved accuracy by 5%
- Based on: https://github.com/crytic/slither/pull/XXXX
```

### Step 6: Test the Changes

#### Unit Tests

```bash
# Run specific detector tests
pytest tests/unit/test_native_detectors.py::TestReentrancyDetector -v

# Run all detector tests
pytest tests/unit/test_native_detectors.py -v
```

#### Manual Testing

```bash
# Test on real contracts
python -m babayaga.native.cli analyze ./test_contracts/ --output results.json

# Review results
cat results.json | jq '.findings[] | select(.detector_id == "native-reentrancy-eth")'
```

### Step 7: Cross-Validate with Upstream

Enable hybrid mode to compare native vs external:

```toml
# babayaga/config/native_config.toml
[native_analysis]
hybrid_mode = true  # Enable comparison mode
```

Run analysis:

```bash
python -m babayaga.native.cli analyze ./test_contracts/
```

The output will show:

```
Hybrid Mode Comparison:
  Native detectors:   3 findings
  External binary:    3 findings
  ✓ Issue types match
```

If there are differences:

```
  ⚠ Only in native: {'native-new-pattern'}
  ⚠ Only in external: {'old-pattern-id'}
```

Investigate discrepancies:
- Is the native implementation missing a pattern?
- Is there a difference in how issues are reported?
- Are there known limitations in the native version?

### Step 8: Document Limitations

If your implementation can't match upstream exactly:

```python
class MyDetector(BaseDetector):
    """Detects XYZ vulnerability.
    
    Implementation Notes:
    - Based on Slither 0.11.0
    - Uses regex pattern matching (upstream uses AST)
    - May miss complex cases involving:
      * Conditional external calls
      * Calls through function pointers
    
    For complete accuracy, use hybrid_mode=true or external binary.
    
    Upstream: https://github.com/crytic/slither/blob/master/...
    """
```

## Example: Complete Update

Let's walk through updating the reentrancy detector from 0.10.0 to 0.11.0:

### 1. Check current version

```bash
$ python -m babayaga.native.cli version-info
# Shows: native-reentrancy-eth @ 0.10.0 (updated 2024-01-15)
```

### 2. Check upstream

```bash
$ curl -s https://api.github.com/repos/crytic/slither/releases/latest | jq .tag_name
"0.11.0"
```

### 3. Review changes

Visit: https://github.com/crytic/slither/compare/0.10.0...0.11.0

Changes found:
- Added detection for `delegatecall` in reentrancy
- Improved state variable tracking
- Fixed false positive with view functions

### 4. Update implementation

```python
# babayaga/native/slither_detectors/reentrancy.py

def _is_external_call(self, line: str) -> bool:
    """Check if line contains an external call."""
    patterns = [
        r'\.call\s*\(',
        r'\.delegatecall\s*\(',  # NEW: Added delegatecall
        r'\.send\s*\(',
        r'\.transfer\s*\(',
    ]
    return any(re.search(pattern, line) for pattern in patterns)

def get_metadata(self) -> DetectorMetadata:
    return DetectorMetadata(
        # ...
        source_version="0.11.0",  # Updated
        last_updated="2024-02-01",  # Updated
    )
```

### 5. Update manifest

```json
{
  "detector_id": "native-reentrancy-eth",
  "source_version": "0.11.0",
  "last_updated": "2024-02-01"
}
```

### 6. Test

```bash
# Run tests
pytest tests/unit/test_native_detectors.py::TestReentrancyDetector -v

# Manual test
cat > /tmp/test_delegatecall.sol << 'EOF'
contract Test {
    function withdraw() public {
        (bool success, ) = msg.sender.delegatecall("");
        balance[msg.sender] = 0;  // State change after call
    }
}
EOF

python -m babayaga.native.cli analyze /tmp/test_delegatecall.sol
# Should now detect the issue!
```

### 7. Validate

```bash
# Compare with external Slither
slither /tmp/test_delegatecall.sol

# Results should match
```

## Automation

### Set Up Update Checks

Create a script to check for updates:

```bash
#!/bin/bash
# scripts/check_detector_versions.sh

echo "Checking for upstream updates..."

# Check Slither
CURRENT_SLITHER=$(python -c "from babayaga.native.slither_detectors.reentrancy import ReentrancyDetector; print(ReentrancyDetector().metadata.source_version)")
LATEST_SLITHER=$(curl -s https://api.github.com/repos/crytic/slither/releases/latest | jq -r .tag_name)

if [ "$CURRENT_SLITHER" != "$LATEST_SLITHER" ]; then
    echo "⚠️  Slither update available: $CURRENT_SLITHER -> $LATEST_SLITHER"
fi

# Check Mythril
# ... similar checks ...

echo "✅ Update check complete"
```

### GitHub Actions Workflow

```yaml
# .github/workflows/check-detector-versions.yml
name: Check Detector Versions

on:
  schedule:
    - cron: '0 0 * * 1'  # Weekly on Monday
  workflow_dispatch:

jobs:
  check-versions:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Check for updates
        run: |
          bash scripts/check_detector_versions.sh
          
      - name: Create issue if updates available
        if: failure()
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'Detector Updates Available',
              body: 'Upstream tools have new versions. Please update detectors.',
              labels: ['detector-update', 'maintenance']
            })
```

## Checklist

Use this checklist when updating detectors:

- [ ] Check current versions: `python -m babayaga.native.cli version-info`
- [ ] Check upstream releases
- [ ] Review upstream changelog
- [ ] Identify changes to detection logic
- [ ] Update detector implementation
- [ ] Update `source_version` in metadata
- [ ] Update `last_updated` in metadata
- [ ] Update DETECTORS_MANIFEST.json
- [ ] Run unit tests
- [ ] Test on real contracts
- [ ] Enable hybrid mode for validation
- [ ] Compare results with external tool
- [ ] Document any limitations
- [ ] Add changelog entry
- [ ] Create PR with changes

## Common Issues

### Issue: Pattern doesn't match new Solidity syntax

**Solution**: Update regex patterns for new syntax:

```python
# Before
r'\.call\s*\('

# After (supports both old and new syntax)
r'\.call\s*\(|\.call\s*\{'
```

### Issue: Upstream uses AST, we use regex

**Solution**: Document limitation and consider AST implementation:

```python
# Short term: Document limitation
"""
Note: This implementation uses pattern matching.
For full AST-based analysis, use hybrid_mode=true.
"""

# Long term: Implement AST parsing
# See: babayaga/native/ast_parser.py (future)
```

### Issue: Can't reproduce upstream behavior

**Solution**: 
1. Review upstream source code carefully
2. Test with the same contracts
3. Document the difference
4. Consider using hybrid mode for that detector

## Best Practices

1. **Update Regularly**: Check for updates monthly
2. **Test Thoroughly**: Always test on real contracts
3. **Document Changes**: Keep DETECTORS_CHANGELOG.md updated
4. **Use Hybrid Mode**: Validate against upstream during updates
5. **Version Control**: Commit changes with clear messages
6. **Backward Compatibility**: Consider compatibility with older contracts

## Resources

- **Upstream Repositories**:
  - Slither: https://github.com/crytic/slither
  - Mythril: https://github.com/ConsenSys/mythril
  - Securify2: https://github.com/eth-sri/securify2
  - Medusa: https://github.com/crytic/medusa

- **Documentation**:
  - Native Analysis Guide: docs/NATIVE_ANALYSIS.md
  - Detector Manifest: babayaga/native/DETECTORS_MANIFEST.json
  - Test Suite: tests/unit/test_native_detectors.py

- **Tools**:
  - Version Info: `python -m babayaga.native.cli version-info`
  - Hybrid Mode: Set in `babayaga/config/native_config.toml`
  - Test Runner: `pytest tests/unit/test_native_detectors.py`
