# BabaYaga Quick Start Guide 🚀

Get up and running with BabaYaga in under 5 minutes!

---

## ⚡ Super Quick Start (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/avaloki108/BabaYaga.git
cd BabaYaga

# 2. Run the automated installer
python install.py

# 3. Start BabaYaga
python -m babayaga
```

That's it! The installer will handle everything for you.

---

## 🐳 Docker Quick Start

```bash
# 1. Clone and start
git clone https://github.com/avaloki108/BabaYaga.git
cd BabaYaga
docker-compose up -d

# 2. Access the application
open http://localhost:8000
```

---

## 🛠️ Manual Installation

### Prerequisites
- Python 3.12+ 
- Node.js 18+ (for some tools)
- Git

### Step-by-Step

```bash
# 1. Clone repository
git clone https://github.com/avaloki108/BabaYaga.git
cd BabaYaga

# 2. Install Python dependencies
pip install -e .[dev,security,test]

# 3. Install security tools (optional but recommended)
# Slither
pip install slither-analyzer

# Mythril
pip install mythril

# Foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup

# 4. Install Ollama (for AI features)
curl -fsSL https://ollama.ai/install.sh | sh

# 5. Download AI models
ollama pull qwen2.5-coder:32b
ollama pull llama3.1:8b

# 6. Create configuration
mkdir -p ~/.babayaga
cp babayaga/config.toml ~/.babayaga/config.toml
```

---

## 🎯 First Audit

### Interactive Mode

```bash
# Start interactive client
python -m babayaga

# Available commands:
BabaYaga> audit ./my-contract/
BabaYaga> quick MyContract.sol
BabaYaga> status
BabaYaga> help
```

### Direct Commands

```bash
# Comprehensive audit
python -m babayaga audit ./contracts/

# Quick scan (faster)
python -m babayaga quick MyContract.sol

# Elite hunt (advanced)
python -m babayaga hunt ./project/ --agents 10 --threshold 200
```

---

## 📝 Basic Usage Examples

### Example 1: Audit a Single Contract

```bash
# Create a test contract
cat > test.sol << 'EOF'
pragma solidity ^0.8.0;

contract VulnerableContract {
    mapping(address => uint256) public balances;
    
    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }
    
    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount);
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success);
        balances[msg.sender] -= amount;  // Reentrancy bug!
    }
}
EOF

# Run audit
python -m babayaga audit test.sol
```

### Example 2: Audit a Foundry Project

```bash
# Audit your Foundry project
cd your-foundry-project/
python -m babayaga audit .

# BabaYaga will automatically:
# - Detect Foundry project
# - Run Slither analysis
# - Run Mythril symbolic execution
# - Execute Foundry fuzzing tests
# - Enhance findings with AI
# - Generate comprehensive report
```

### Example 3: Quick Scan

```bash
# Fast vulnerability scan
python -m babayaga quick ./contracts/Token.sol

# Output:
# 🔍 Quick Scan Results
# ├── Critical: 0
# ├── High: 2
# ├── Medium: 5
# └── Low: 3
```

---

## ⚙️ Configuration

### Quick Configuration

```bash
# View current configuration
cat ~/.babayaga/config.toml

# Edit configuration
nano ~/.babayaga/config.toml
```

### Common Configuration Changes

```toml
# Adjust AI model
[models]
primary_model = "qwen2.5-coder:14b"  # Lighter model

# Adjust scan intensity
[elite]
minimum_score_threshold = 100  # Lower threshold = more findings

# Enable/disable tools
[security_tools]
slither_enabled = true
mythril_enabled = false  # Disable if slow
foundry_enabled = true
```

---

## 🔍 Understanding Output

### Report Structure

```
🛡️ Web3 Security Audit Report - HIGH RISK

📊 Audit Summary
┌─────────────────┬───────┬────────┐
│ Total Findings  │    12 │   📋   │
│ Critical        │     2 │   🔴   │
│ High            │     4 │   🟡   │
│ Medium          │     5 │   🟠   │
│ Low             │     1 │   🟢   │
│ Risk Score      │    45 │  HIGH  │
└─────────────────┴───────┴────────┘

🔍 Top Security Findings
┌──────────┬────────────┬─────────────────────────┬────────────┐
│ Severity │ Tool       │ Finding                 │ Confidence │
├──────────┼────────────┼─────────────────────────┼────────────┤
│ CRITICAL │ slither    │ Reentrancy in withdraw  │       0.95 │
│ HIGH     │ mythril    │ Integer overflow        │       0.87 │
│ HIGH     │ custom     │ Unchecked external call │       0.82 │
└──────────┴────────────┴─────────────────────────┴────────────┘

🎯 Key Recommendations:
• 🚨 IMMEDIATE ACTION REQUIRED: Critical vulnerabilities found
• ⚠️ High-severity issues require prompt attention
• 🧠 LLM-generated remediation guidance available
```

### Severity Levels

| Level | Icon | Description | Action Required |
|-------|------|-------------|-----------------|
| **Critical** | 🔴 | Immediate exploitation possible | Fix immediately |
| **High** | 🟡 | Severe security risk | Fix urgently |
| **Medium** | 🟠 | Moderate security risk | Fix soon |
| **Low** | 🟢 | Minor issue or optimization | Fix when possible |
| **Info** | ℹ️ | Informational | Review |

---

## 🆘 Troubleshooting

### Common Issues

#### Issue: "Ollama not found"
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Verify installation
ollama --version

# Pull a model
ollama pull qwen2.5-coder:14b
```

#### Issue: "Slither not available"
```bash
# Install Slither
pip install slither-analyzer

# Verify
slither --version
```

#### Issue: "ModuleNotFoundError: No module named 'httpx'"
```bash
# Install missing dependency
pip install httpx
```

#### Issue: "No Solidity files found"
```bash
# Make sure you're in the right directory
ls -la *.sol

# Or specify the full path
python -m babayaga audit /full/path/to/contracts/
```

### Debug Mode

```bash
# Run with debug output
export BABAYAGA_DEBUG=true
python -m babayaga audit ./contracts/

# Check logs
tail -f babayaga.log
```

---

## 📚 Next Steps

Once you're comfortable with the basics:

1. **Read the Full Documentation**
   - [README.md](README.md) - Complete feature list
   - [CONFIGURATION.md](CONFIGURATION.md) - Detailed configuration
   - [DESIGN.md](design/DESIGN.md) - Architecture details

2. **Explore Advanced Features**
   - Elite hunt mode for persistent scanning
   - Multi-agent vulnerability research
   - Custom detector configuration
   - CI/CD integration

3. **Join the Community**
   - Report issues on GitHub
   - Contribute improvements
   - Share your findings

---

## 💡 Pro Tips

1. **Start with Quick Scan**
   - Use `quick` command first for fast overview
   - Then run full `audit` on interesting targets

2. **Adjust Thresholds**
   - Lower threshold for more findings
   - Higher threshold for critical issues only

3. **Use Stealth Mode**
   ```bash
   python -m babayaga audit ./contracts/ --stealth
   ```

4. **Parallel Analysis**
   - BabaYaga runs tools in parallel by default
   - Adjust in config for slower machines

5. **Export Reports**
   ```bash
   # JSON export
   python -m babayaga audit ./contracts/ --export json
   
   # Markdown report
   python -m babayaga audit ./contracts/ --export markdown
   ```

---

## 🎓 Example Workflow

Here's a complete audit workflow:

```bash
# 1. Clone target project
git clone https://github.com/example/defi-protocol.git
cd defi-protocol

# 2. Quick reconnaissance
python -m babayaga quick ./contracts/

# 3. Full comprehensive audit
python -m babayaga audit ./contracts/ --stealth

# 4. Review findings
# BabaYaga will show interactive report in terminal

# 5. Export for team review
python -m babayaga export --format markdown --output audit-report.md

# 6. Address critical findings
# (Fix vulnerabilities in code)

# 7. Re-scan to verify fixes
python -m babayaga audit ./contracts/
```

---

## 🚀 Ready to Go!

You're now ready to use BabaYaga for your Web3 security audits!

**Quick Reference:**
- Start: `python -m babayaga`
- Audit: `python -m babayaga audit <target>`
- Quick Scan: `python -m babayaga quick <target>`
- Help: `python -m babayaga --help`

**Need Help?**
- Check [README.md](README.md) for detailed documentation
- See [COMPREHENSIVE_REVIEW.md](COMPREHENSIVE_REVIEW.md) for technical details
- Report issues on [GitHub Issues](https://github.com/avaloki108/BabaYaga/issues)

---

**Happy Hunting! 💀🔍**

*"With a fucking pencil... and some smart contracts"*
