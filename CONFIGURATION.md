# BabaYaga Configuration Guide

## 🔧 Quick Setup

BabaYaga supports machine-specific configurations for models, MCP servers, and elite audit settings.

### First-Time Setup

```bash
# Interactive configuration setup
python -m babayaga.config.setup_cli setup

# Or use the main CLI
python -m babayaga
# (Will prompt for configuration on first run)
```

## 🤖 Model Configuration

### Setting Your Primary Models

```bash
# Set primary analysis model
babayaga-config model set primary qwen2.5-coder:32b

# Set code-specific model  
babayaga-config model set code qwen2.5-coder:32b

# Set reasoning model
babayaga-config model set reasoning gpt-4o

# Set fallback model
babayaga-config model set fallback llama3.1:70b
```

### Supported Model Formats

**Ollama Models:**
```bash
qwen2.5-coder:32b      # Best for code analysis
qwen2.5-coder:14b      # Good balance of speed/quality
llama3.1:70b           # Excellent reasoning
deepseek-coder:33b     # Alternative code model
codellama:34b          # Meta's code model
```

**Custom Models:**
```bash
ollama/gpt-oss:20b     # Your custom OSS model
ollama/your-model:tag  # Any custom model
```

**API Models:**
```bash
gpt-4o                 # OpenAI GPT-4
claude-3-5-sonnet      # Anthropic Claude
grok-beta              # xAI Grok
```

## 🔌 MCP Server Configuration

### Import Existing MCP Configuration

```bash
# Import from Claude Desktop config
babayaga-config mcp import ~/.claude_desktop_config.json

# Import from custom location
babayaga-config mcp import /path/to/your/mcp_config.json
```

### Add Custom MCP Servers

```bash
# Add a simple MCP server
babayaga-config mcp add my-server python3 --args server.py --cwd /path/to/server

# Add with environment variables
babayaga-config mcp add grok-server uv --args run python grok_server.py \
  --env GROK_API_KEY=your-key --env MODEL=grok-code-fast-1 \
  --cwd /home/user/MCP/Grok_Mcp

# Add Node.js MCP server
babayaga-config mcp add nuclei-server node --args /path/to/nuclei-mcp/build/index.js \
  --cwd /path/to/nuclei-mcp
```

### Manage MCP Servers

```bash
# List all MCP servers
babayaga-config mcp list

# Enable/disable servers
babayaga-config mcp enable server-name
babayaga-config mcp disable server-name
```

## 💀 Elite Audit Settings

### Configure Elite Parameters

```bash
# Set minimum score threshold (Novelty × Exploitability × Impact)
babayaga-config elite threshold 200

# Set maximum parallel agents
babayaga-config elite agents 10
```

### Elite Settings Explained

- **Minimum Score Threshold**: Only findings with `Novelty × Exploitability × Impact ≥ threshold` are reported
- **Conference Worthy Threshold**: Findings above 500 are considered conference-worthy
- **Max Parallel Agents**: Number of vulnerability hunters to run simultaneously
- **Stealth Mode**: Reduces logging and operates more quietly
- **Persistence Mode**: Continues hunting until quality threshold is met

## 📁 Configuration Files

BabaYaga stores configuration in `~/.babayaga/`:

```
~/.babayaga/
├── config.toml           # Main configuration
├── mcp_servers.json      # MCP server definitions
└── models.toml           # Model configurations
```

### Example Configuration Files

**`~/.babayaga/config.toml`**
```toml
[elite]
minimum_score_threshold = 200
stealth_mode_default = true
persistence_mode_default = true
conference_worthy_threshold = 500
max_parallel_agents = 10
enable_novel_attack_generation = true

[security_tools]
slither_enabled = true
mythril_enabled = true
securify2_enabled = true
echidna_enabled = true  # Native implementation (no external binary required)
medusa_enabled = true
foundry_enabled = true
nuclei_enabled = true

[output]
default_format = "rich_console"
export_formats = ["json", "markdown", "html"]
include_proof_of_concept = true
include_remediation = true
include_economic_impact = true
```

**`~/.babayaga/models.toml`**
```toml
[models]
primary_model = "qwen2.5-coder:32b"
fallback_model = "llama3.1:70b"
code_model = "qwen2.5-coder:32b"
reasoning_model = "gpt-4o"
temperature = 0.1
max_tokens = 4096
context_window = 32768
provider = "ollama"
```

**`~/.babayaga/mcp_servers.json`**
```json
{
  "mcpServers": {
    "grok-mcp-server": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "grok_mcp_server.py"],
      "env": {
        "GROK_API_KEY": "your-api-key",
        "GROK_MODEL": "grok-code-fast-1"
      },
      "cwd": "/home/user/MCP/Grok_Mcp",
      "disabled": false,
      "description": "Grok AI integration for enhanced analysis"
    },
    "nuclei-mcp": {
      "type": "stdio", 
      "command": "node",
      "args": ["/home/user/MCP/nuclei-mcp/build/index.js"],
      "env": {},
      "cwd": "/home/user/MCP/nuclei-mcp",
      "disabled": false,
      "description": "Nuclei vulnerability scanner integration"
    }
  }
}
```

## 🚀 Usage Examples

### Basic Usage with Custom Config

```bash
# Start BabaYaga with your configuration
python -m babayaga

# Run audit with specific model
python -m babayaga audit ./contracts/ --model qwen2.5-coder:32b

# Elite hunt with stealth mode
python -m babayaga hunt ./target-project/ --stealth --threshold 300
```

### Environment-Specific Configurations

**Development Machine:**
```bash
# Fast models for quick iteration
babayaga-config model set primary qwen2.5-coder:7b
babayaga-config elite threshold 100
babayaga-config elite agents 5
```

**Production Audit Server:**
```bash
# High-quality models for thorough analysis
babayaga-config model set primary qwen2.5-coder:32b
babayaga-config model set reasoning gpt-4o
babayaga-config elite threshold 200
babayaga-config elite agents 10
```

**Laptop (Resource Constrained):**
```bash
# Lightweight configuration
babayaga-config model set primary llama3.1:8b
babayaga-config elite agents 3
babayaga-config elite threshold 150
```

## 🔍 Viewing Current Configuration

```bash
# Show all current settings
babayaga-config show

# List available models
babayaga-config model list

# List MCP servers
babayaga-config mcp list
```

## 🛠️ Advanced Configuration

### Custom Security Tools

Add custom security tools to your configuration:

```toml
[security_tools.custom_tools]
my_analyzer = {
  command = "python3",
  args = ["/path/to/my_analyzer.py"],
  enabled = true,
  description = "Custom vulnerability analyzer"
}
```

### Environment Variables

BabaYaga respects these environment variables:

```bash
export BABAYAGA_CONFIG_DIR="~/.babayaga"
export BABAYAGA_MODEL="qwen2.5-coder:32b"
export BABAYAGA_STEALTH_MODE="true"
export BABAYAGA_THRESHOLD="200"
```

### API Keys and Secrets

Store API keys securely in your environment:

```bash
# For OpenAI models
export OPENAI_API_KEY="your-openai-key"

# For Anthropic models  
export ANTHROPIC_API_KEY="your-anthropic-key"

# For Grok models
export GROK_API_KEY="your-grok-key"
```

## 🔄 Migration and Backup

### Backup Configuration

```bash
# Backup your configuration
cp -r ~/.babayaga ~/.babayaga.backup

# Or create a portable config
tar -czf babayaga-config.tar.gz -C ~ .babayaga
```

### Migrate to New Machine

```bash
# On new machine, restore configuration
tar -xzf babayaga-config.tar.gz -C ~

# Or copy individual files
scp -r old-machine:~/.babayaga ~/.babayaga
```

## 🆘 Troubleshooting

### Common Issues

**Models not found:**
```bash
# Check if Ollama is running
ollama list

# Pull missing models
ollama pull qwen2.5-coder:32b
```

**MCP servers not connecting:**
```bash
# Test MCP server manually
python3 /path/to/server.py

# Check server logs
babayaga-config mcp list
```

**Configuration not loading:**
```bash
# Reset configuration
rm -rf ~/.babayaga
python -m babayaga.config.setup_cli setup
```

### Debug Mode

```bash
# Run with debug logging
BABAYAGA_DEBUG=true python -m babayaga audit ./contracts/
```

---

**💀 BabaYaga is now configured and ready to hunt vulnerabilities with deadly precision!**
