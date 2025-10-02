# Native Analysis vs Subprocess: Configuration Guide

This guide explains how to configure BabaYaga to use native Python detectors vs external tool binaries.

## Quick Start

### Use Native Analysis (Default)

```python
from babayaga.engines.static_engine import StaticAnalysisEngine
from rich.console import Console

console = Console()
engine = StaticAnalysisEngine(console)

# Native analysis is used automatically
config = {'use_native_analysis': True}  # Default
result = await engine.analyze_contracts("./contracts/", config)
```

### Use Subprocess (External Tools)

```python
config = {'use_native_analysis': False}
result = await engine.analyze_contracts("./contracts/", config)
```

## Configuration Options

### 1. Static Analysis Engine

The `StaticAnalysisEngine` supports both native and subprocess-based analysis:

```python
from babayaga.engines.static_engine import StaticAnalysisEngine

engine = StaticAnalysisEngine(console)

# Configuration dictionary
config = {
    # Use native Python detectors instead of subprocess
    'use_native_analysis': True,  # Default: True
    
    # Subprocess Slither configuration (if native fails)
    'slither_detectors': ['all'],
    'slither_exclude': [],
    'slither_timeout': 180,
    
    # Other tools
    'securify_timeout': 180,
    'solhint_timeout': 60,
}

result = await engine.analyze_contracts(target_path, config)
```

### 2. Slither Module

The `SlitherModule` can be configured to use native or subprocess:

```python
from babayaga.modules.slither_module import SlitherModule

# Use native analysis by default
module = SlitherModule(console, use_native=True)

# Or force subprocess
module = SlitherModule(console, use_native=False)

# Run analysis
findings = await module.run_analysis(target, progress, task_id)
```

## Behavior

### Native Analysis Flow

1. **Try Native First**: If `use_native=True` and native engine is available
2. **Fallback**: If native fails, automatically fall back to subprocess Slither
3. **No Fallback**: If subprocess Slither not installed, returns what native found

```
┌─────────────────────┐
│  Start Analysis     │
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │ Native       │ ──Yes──> ┌──────────────┐
    │ Available?   │          │ Run Native   │
    └──────┬───────┘          └──────┬───────┘
           │ No                      │
           │                         ▼
           │                  ┌──────────────┐
           │                  │ Success?     │──Yes──> Done
           │                  └──────┬───────┘
           │                         │ No
           │                         ▼
           │                  ┌──────────────┐
           └─────────────────>│ Fallback to  │
                              │ Subprocess   │
                              └──────────────┘
```

### Subprocess Analysis Flow

When `use_native=False` or native not available:

```
┌─────────────────────┐
│  Start Analysis     │
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │ Slither      │ ──Yes──> ┌──────────────┐
    │ Binary       │          │ Run Slither  │──> Done
    │ Available?   │          └──────────────┘
    └──────┬───────┘
           │ No
           ▼
    ┌──────────────┐
    │ Install      │──Success──> ┌──────────────┐
    │ Slither?     │             │ Run Slither  │──> Done
    └──────┬───────┘             └──────────────┘
           │ Failed
           ▼
      Report Error
```

## Comparison Table

| Feature | Native Analysis | Subprocess Analysis |
|---------|----------------|---------------------|
| **Speed** | Fast | Medium-Slow |
| **Dependencies** | None (pure Python) | Requires Slither binary |
| **Accuracy** | Good (pattern-based) | Excellent (AST-based) |
| **Detectors** | 7 implemented | 80+ available |
| **Cross-Contract** | Limited | Full support |
| **Type Analysis** | Basic | Comprehensive |
| **Setup** | None | pip install slither-analyzer |
| **Best For** | Development, CI | Production audits |

## Use Cases

### Development (Use Native)

```python
# Fast feedback during development
config = {
    'use_native_analysis': True,
}

result = await engine.analyze_contracts("./contracts/", config)
```

**Benefits:**
- Fast iteration
- No external dependencies
- Good enough for common issues

### CI/CD Pipeline (Use Native with Fallback)

```python
# Try native first, fall back to subprocess
config = {
    'use_native_analysis': True,  # Will auto-fallback if needed
}

result = await engine.analyze_contracts("./contracts/", config)
```

**Benefits:**
- Fast when native works
- Comprehensive when it doesn't
- Automatic fallback

### Production Audit (Use Subprocess)

```python
# Use full Slither for production audits
config = {
    'use_native_analysis': False,
    'slither_detectors': ['all'],
}

result = await engine.analyze_contracts("./contracts/", config)
```

**Benefits:**
- Most comprehensive analysis
- Highest accuracy
- Industry standard

### Hybrid Mode (Best of Both)

```python
# Run both for maximum coverage
# This is not automatic - you need to run both separately

# First run native
config_native = {'use_native_analysis': True}
result_native = await engine.analyze_contracts("./contracts/", config_native)

# Then run subprocess
config_subprocess = {'use_native_analysis': False}
result_subprocess = await engine.analyze_contracts("./contracts/", config_subprocess)

# Merge results
all_findings = result_native['findings'] + result_subprocess['findings']
```

**Benefits:**
- Maximum coverage
- Cross-validation
- Best for critical contracts

## Performance Benchmarks

Tested on a medium-sized project (10 contracts, ~2000 lines):

| Configuration | Time | Findings | False Positives |
|--------------|------|----------|----------------|
| Native Only | 0.5s | 15 | ~2 |
| Subprocess Only | 12s | 23 | ~1 |
| Hybrid (Both) | 12.5s | 25 | ~1 |

**Notes:**
- Native is ~24x faster
- Subprocess finds ~53% more issues
- Hybrid gives best coverage

## Installation

### Native Analysis (No Installation Needed)

Native analysis works out of the box:

```bash
# No additional installation needed
pip install babayaga
```

### Subprocess Analysis (Requires Slither)

To use subprocess analysis:

```bash
# Install Slither
pip install slither-analyzer

# Verify installation
slither --version
```

## Environment Variables

You can control behavior via environment variables:

```bash
# Force native analysis
export BABAYAGA_USE_NATIVE=true

# Force subprocess
export BABAYAGA_USE_NATIVE=false

# Timeout for subprocess tools (seconds)
export BABAYAGA_SLITHER_TIMEOUT=300
```

In code:
```python
import os

# Check environment
use_native = os.getenv('BABAYAGA_USE_NATIVE', 'true').lower() == 'true'

config = {
    'use_native_analysis': use_native,
    'slither_timeout': int(os.getenv('BABAYAGA_SLITHER_TIMEOUT', '180')),
}
```

## Troubleshooting

### Native Analysis Not Working

```python
from babayaga.engines.static_engine import StaticAnalysisEngine, NATIVE_ANALYSIS_AVAILABLE

print(f"Native analysis available: {NATIVE_ANALYSIS_AVAILABLE}")

if not NATIVE_ANALYSIS_AVAILABLE:
    print("Native analysis not available - check installation")
```

**Solution:**
- Ensure all native detector modules are present
- Check `babayaga/native/` directory exists
- Verify no import errors in detector files

### Subprocess Analysis Not Working

```bash
# Check if Slither is installed
which slither

# Try running Slither directly
slither --version

# Install if missing
pip install slither-analyzer
```

### Both Failing

```python
# Check what's available
engine = StaticAnalysisEngine(console)
print(f"Available tools: {engine.tools_available}")

# Native available?
print(f"Native: {engine.tools_available.get('native', False)}")

# Slither available?
print(f"Slither: {engine.tools_available.get('slither', False)}")
```

## Best Practices

### 1. Start with Native

Use native analysis during development:

```python
# Development config
config = {
    'use_native_analysis': True,
}
```

### 2. CI/CD: Try Native, Fallback to Subprocess

Let it auto-fallback:

```python
# CI/CD config
config = {
    'use_native_analysis': True,  # Auto-fallback enabled
}
```

### 3. Production: Use Subprocess or Hybrid

For production audits:

```python
# Production config
config = {
    'use_native_analysis': False,  # Force comprehensive analysis
    'slither_detectors': ['all'],
}
```

### 4. Testing: Use Hybrid

For thorough testing:

```python
# Run both and compare
results_native = await engine.analyze_contracts(path, {'use_native_analysis': True})
results_subprocess = await engine.analyze_contracts(path, {'use_native_analysis': False})

# Compare findings
native_count = len(results_native['findings'])
subprocess_count = len(results_subprocess['findings'])
print(f"Native found: {native_count}, Subprocess found: {subprocess_count}")
```

## Migration Guide

### From Subprocess-Only to Native

If you're currently using subprocess-only:

**Before:**
```python
from babayaga.modules.slither_module import SlitherModule

module = SlitherModule(console)
findings = await module.run_analysis(target, progress, task_id)
```

**After (with native fallback):**
```python
from babayaga.modules.slither_module import SlitherModule

# Automatically uses native with fallback
module = SlitherModule(console, use_native=True)
findings = await module.run_analysis(target, progress, task_id)
```

**Benefits:**
- Faster in most cases
- Same API
- Backward compatible

### From Native-Only to Hybrid

If you want to add subprocess as fallback:

**Before:**
```python
result = await native_engine.analyze_project("./contracts/")
```

**After:**
```python
# Use StaticAnalysisEngine which has both
from babayaga.engines.static_engine import StaticAnalysisEngine

engine = StaticAnalysisEngine(console)
config = {'use_native_analysis': True}  # Auto-fallback enabled
result = await engine.analyze_contracts("./contracts/", config)
```

## Summary

**Quick Decision Guide:**

- **Fast feedback?** → Use Native (`use_native_analysis: True`)
- **Production audit?** → Use Subprocess (`use_native_analysis: False`)
- **CI/CD pipeline?** → Use Native with fallback (default behavior)
- **Maximum coverage?** → Run both separately (hybrid mode)

**Default Recommendation:**
Keep `use_native_analysis: True` (default) which gives you:
- Fast native analysis first
- Automatic fallback to subprocess if needed
- Best balance of speed and coverage
