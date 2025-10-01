"""BabaYaga Configuration System - Machine-specific and user-customizable settings."""

import json
import os
import toml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

@dataclass
class MCPServerConfig:
    """Configuration for an individual MCP server."""
    name: str
    type: str = "stdio"
    command: str = ""
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None
    disabled: bool = False
    description: str = ""
    capabilities: List[str] = field(default_factory=list)

@dataclass
class ModelConfig:
    """Configuration for LLM models."""
    primary_model: str = "qwen2.5-coder:32b"
    fallback_model: str = "llama3.1:70b"
    code_model: str = "qwen2.5-coder:32b"
    reasoning_model: str = "gpt-4o"
    temperature: float = 0.1
    max_tokens: int = 4096
    context_window: int = 32768
    provider: str = "ollama"  # ollama, openai, anthropic, grok
    
@dataclass
class EliteSettings:
    """Elite audit configuration."""
    minimum_score_threshold: int = 200
    stealth_mode_default: bool = True
    persistence_mode_default: bool = True
    conference_worthy_threshold: int = 500
    max_parallel_agents: int = 10
    enable_novel_attack_generation: bool = True

@dataclass
class SecurityToolsConfig:
    """Security tools configuration."""
    slither_enabled: bool = True
    mythril_enabled: bool = True
    securify2_enabled: bool = True
    echidna_enabled: bool = True
    medusa_enabled: bool = True
    foundry_enabled: bool = True
    fuzz_utils_enabled: bool = True
    solhint_enabled: bool = True
    nuclei_enabled: bool = True
    custom_tools: Dict[str, Dict[str, Any]] = field(default_factory=dict)

class BabaYagaConfigManager:
    """
    BabaYaga Configuration Manager - Handles machine-specific and user configurations.
    
    Supports:
    - Custom MCP server configurations
    - Model selection and provider settings
    - Elite audit parameters
    - Security tool configurations
    - Environment-specific settings
    """
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        
        # Configuration paths
        self.config_dir = Path.home() / ".babayaga"
        self.config_file = self.config_dir / "config.toml"
        self.mcp_config_file = self.config_dir / "mcp_servers.json"
        self.models_config_file = self.config_dir / "models.toml"
        
        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)
        
        # Load configurations
        self.config = self._load_config()
        self.mcp_servers = self._load_mcp_servers()
        self.models = self._load_models_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load main BabaYaga configuration."""
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return toml.load(f)
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load config: {e}[/yellow]")
        
        # Return default configuration
        return self._get_default_config()
    
    def _load_mcp_servers(self) -> Dict[str, MCPServerConfig]:
        """Load MCP server configurations."""
        
        servers = {}
        
        if self.mcp_config_file.exists():
            try:
                with open(self.mcp_config_file, 'r') as f:
                    data = json.load(f)
                    
                for name, config in data.get('mcpServers', {}).items():
                    servers[name] = MCPServerConfig(
                        name=name,
                        type=config.get('type', 'stdio'),
                        command=config.get('command', ''),
                        args=config.get('args', []),
                        env=config.get('env', {}),
                        cwd=config.get('cwd'),
                        disabled=config.get('disabled', False),
                        description=config.get('description', ''),
                        capabilities=config.get('capabilities', [])
                    )
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load MCP servers: {e}[/yellow]")
        
        return servers
    
    def _load_models_config(self) -> ModelConfig:
        """Load model configuration."""
        
        if self.models_config_file.exists():
            try:
                with open(self.models_config_file, 'r') as f:
                    data = toml.load(f)
                    return ModelConfig(**data.get('models', {}))
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load models config: {e}[/yellow]")
        
        return ModelConfig()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default BabaYaga configuration."""
        
        return {
            'elite': {
                'minimum_score_threshold': 200,
                'stealth_mode_default': True,
                'persistence_mode_default': True,
                'conference_worthy_threshold': 500,
                'max_parallel_agents': 10,
                'enable_novel_attack_generation': True
            },
            'security_tools': {
                'slither_enabled': True,
                'mythril_enabled': True,
                'securify2_enabled': True,
                'echidna_enabled': True,
                'medusa_enabled': True,
                'foundry_enabled': True,
                'fuzz_utils_enabled': True,
                'solhint_enabled': True,
                'nuclei_enabled': True
            },
            'output': {
                'default_format': 'rich_console',
                'export_formats': ['json', 'markdown', 'html'],
                'include_proof_of_concept': True,
                'include_remediation': True,
                'include_economic_impact': True
            },
            'logging': {
                'level': 'INFO',
                'file': 'babayaga.log',
                'max_size': '10MB',
                'backup_count': 5
            }
        }
    
    def setup_initial_config(self):
        """Interactive setup for first-time configuration."""
        
        self.console.print(Panel(
            "[bold red]💀 BabaYaga Initial Configuration[/bold red]\n\n"
            "[yellow]Let's configure BabaYaga for your machine...[/yellow]",
            border_style="red"
        ))
        
        # Model configuration
        self._setup_models()
        
        # MCP server configuration
        self._setup_mcp_servers()
        
        # Elite settings
        self._setup_elite_settings()
        
        # Save all configurations
        self._save_all_configs()
        
        self.console.print("[green]✅ BabaYaga configuration complete![/green]")
    
    def _setup_models(self):
        """Interactive model configuration."""
        
        self.console.print("\n[bold cyan]🤖 Model Configuration[/bold cyan]")
        
        # Primary model
        primary_model = Prompt.ask(
            "Primary model for analysis",
            default=self.models.primary_model,
            choices=[
                "qwen2.5-coder:32b",
                "qwen2.5-coder:14b", 
                "qwen2.5-coder:7b",
                "llama3.1:70b",
                "llama3.1:8b",
                "gpt-4o",
                "gpt-4o-mini",
                "claude-3-5-sonnet",
                "grok-beta",
                "custom"
            ]
        )
        
        if primary_model == "custom":
            primary_model = Prompt.ask("Enter custom model name (e.g., ollama/gpt-oss:20b)")
        
        # Code-specific model
        code_model = Prompt.ask(
            "Code analysis model",
            default=primary_model,
            choices=[
                "qwen2.5-coder:32b",
                "qwen2.5-coder:14b",
                "deepseek-coder:33b",
                "codellama:34b",
                "custom"
            ]
        )
        
        if code_model == "custom":
            code_model = Prompt.ask("Enter custom code model name")
        
        # Provider
        provider = "ollama"
        if any(model.startswith(("gpt-", "claude-", "grok-")) for model in [primary_model, code_model]):
            provider = Prompt.ask(
                "Model provider",
                choices=["ollama", "openai", "anthropic", "grok"],
                default="ollama"
            )
        
        # Update model configuration
        self.models.primary_model = primary_model
        self.models.code_model = code_model
        self.models.provider = provider
        
        # Advanced settings
        if Confirm.ask("Configure advanced model settings?", default=False):
            self.models.temperature = float(Prompt.ask("Temperature (0.0-2.0)", default=str(self.models.temperature)))
            self.models.max_tokens = int(Prompt.ask("Max tokens", default=str(self.models.max_tokens)))
    
    def _setup_mcp_servers(self):
        """Interactive MCP server configuration."""
        
        self.console.print("\n[bold cyan]🔌 MCP Server Configuration[/bold cyan]")
        
        # Ask if user wants to import existing MCP config
        if Confirm.ask("Do you have an existing MCP configuration file?", default=True):
            config_path = Prompt.ask("Path to MCP config file", default="~/.claude_desktop_config.json")
            config_path = Path(config_path).expanduser()
            
            if config_path.exists():
                self._import_mcp_config(config_path)
            else:
                self.console.print(f"[red]File not found: {config_path}[/red]")
        
        # Show current MCP servers
        self._display_mcp_servers()
        
        # Allow adding custom servers
        while Confirm.ask("Add a custom MCP server?", default=False):
            self._add_custom_mcp_server()
    
    def _import_mcp_config(self, config_path: Path):
        """Import MCP configuration from existing file."""
        
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            
            imported_count = 0
            for name, config in data.get('mcpServers', {}).items():
                self.mcp_servers[name] = MCPServerConfig(
                    name=name,
                    type=config.get('type', 'stdio'),
                    command=config.get('command', ''),
                    args=config.get('args', []),
                    env=config.get('env', {}),
                    cwd=config.get('cwd'),
                    disabled=config.get('disabled', False)
                )
                imported_count += 1
            
            self.console.print(f"[green]✅ Imported {imported_count} MCP servers[/green]")
            
        except Exception as e:
            self.console.print(f"[red]Error importing MCP config: {e}[/red]")
    
    def _display_mcp_servers(self):
        """Display current MCP server configuration."""
        
        if not self.mcp_servers:
            self.console.print("[yellow]No MCP servers configured[/yellow]")
            return
        
        table = Table(title="🔌 Configured MCP Servers")
        table.add_column("Name", style="cyan")
        table.add_column("Command", style="white")
        table.add_column("Status", justify="center")
        table.add_column("Description", style="dim")
        
        for name, server in self.mcp_servers.items():
            status = "❌ Disabled" if server.disabled else "✅ Enabled"
            description = server.description or "No description"
            command = f"{server.command} {' '.join(server.args[:2])}"
            if len(command) > 40:
                command = command[:37] + "..."
            
            table.add_row(name, command, status, description)
        
        self.console.print(table)
    
    def _add_custom_mcp_server(self):
        """Add a custom MCP server."""
        
        name = Prompt.ask("Server name")
        command = Prompt.ask("Command")
        args_str = Prompt.ask("Arguments (space-separated)", default="")
        args = args_str.split() if args_str else []
        cwd = Prompt.ask("Working directory (optional)", default="")
        description = Prompt.ask("Description (optional)", default="")
        
        # Environment variables
        env = {}
        while Confirm.ask("Add environment variable?", default=False):
            key = Prompt.ask("Environment variable name")
            value = Prompt.ask(f"Value for {key}")
            env[key] = value
        
        self.mcp_servers[name] = MCPServerConfig(
            name=name,
            command=command,
            args=args,
            env=env,
            cwd=cwd if cwd else None,
            description=description
        )
        
        self.console.print(f"[green]✅ Added MCP server: {name}[/green]")
    
    def _setup_elite_settings(self):
        """Configure elite audit settings."""
        
        self.console.print("\n[bold cyan]💀 Elite Audit Settings[/bold cyan]")
        
        if Confirm.ask("Configure elite audit parameters?", default=False):
            threshold = int(Prompt.ask(
                "Minimum score threshold (Novelty × Exploitability × Impact)",
                default="200"
            ))
            
            max_agents = int(Prompt.ask(
                "Maximum parallel agents",
                default="10"
            ))
            
            stealth_default = Confirm.ask("Enable stealth mode by default?", default=True)
            
            self.config['elite']['minimum_score_threshold'] = threshold
            self.config['elite']['max_parallel_agents'] = max_agents
            self.config['elite']['stealth_mode_default'] = stealth_default
    
    def _save_all_configs(self):
        """Save all configuration files."""
        
        # Save main config
        with open(self.config_file, 'w') as f:
            toml.dump(self.config, f)
        
        # Save MCP servers
        mcp_data = {
            'mcpServers': {
                name: {
                    'type': server.type,
                    'command': server.command,
                    'args': server.args,
                    'env': server.env,
                    'cwd': server.cwd,
                    'disabled': server.disabled,
                    'description': server.description,
                    'capabilities': server.capabilities
                }
                for name, server in self.mcp_servers.items()
            }
        }
        
        with open(self.mcp_config_file, 'w') as f:
            json.dump(mcp_data, f, indent=2)
        
        # Save models config
        models_data = {
            'models': {
                'primary_model': self.models.primary_model,
                'fallback_model': self.models.fallback_model,
                'code_model': self.models.code_model,
                'reasoning_model': self.models.reasoning_model,
                'temperature': self.models.temperature,
                'max_tokens': self.models.max_tokens,
                'context_window': self.models.context_window,
                'provider': self.models.provider
            }
        }
        
        with open(self.models_config_file, 'w') as f:
            toml.dump(models_data, f)
    
    def get_model_config(self, model_type: str = "primary") -> str:
        """Get model configuration for specific use case."""
        
        model_map = {
            'primary': self.models.primary_model,
            'code': self.models.code_model,
            'reasoning': self.models.reasoning_model,
            'fallback': self.models.fallback_model
        }
        
        return model_map.get(model_type, self.models.primary_model)
    
    def get_enabled_mcp_servers(self) -> Dict[str, MCPServerConfig]:
        """Get all enabled MCP servers."""
        
        return {
            name: server 
            for name, server in self.mcp_servers.items() 
            if not server.disabled
        }
    
    def get_elite_config(self) -> EliteSettings:
        """Get elite audit configuration."""
        
        elite_config = self.config.get('elite', {})
        return EliteSettings(
            minimum_score_threshold=elite_config.get('minimum_score_threshold', 200),
            stealth_mode_default=elite_config.get('stealth_mode_default', True),
            persistence_mode_default=elite_config.get('persistence_mode_default', True),
            conference_worthy_threshold=elite_config.get('conference_worthy_threshold', 500),
            max_parallel_agents=elite_config.get('max_parallel_agents', 10),
            enable_novel_attack_generation=elite_config.get('enable_novel_attack_generation', True)
        )
    
    def get_security_tools_config(self) -> SecurityToolsConfig:
        """Get security tools configuration."""
        
        tools_config = self.config.get('security_tools', {})
        return SecurityToolsConfig(
            slither_enabled=tools_config.get('slither_enabled', True),
            mythril_enabled=tools_config.get('mythril_enabled', True),
            securify2_enabled=tools_config.get('securify2_enabled', True),
            echidna_enabled=tools_config.get('echidna_enabled', True),
            medusa_enabled=tools_config.get('medusa_enabled', True),
            foundry_enabled=tools_config.get('foundry_enabled', True),
            fuzz_utils_enabled=tools_config.get('fuzz_utils_enabled', True),
            solhint_enabled=tools_config.get('solhint_enabled', True),
            nuclei_enabled=tools_config.get('nuclei_enabled', True),
            custom_tools=tools_config.get('custom_tools', {})
        )
    
    def update_model(self, model_type: str, model_name: str):
        """Update a specific model configuration."""
        
        if model_type == "primary":
            self.models.primary_model = model_name
        elif model_type == "code":
            self.models.code_model = model_name
        elif model_type == "reasoning":
            self.models.reasoning_model = model_name
        elif model_type == "fallback":
            self.models.fallback_model = model_name
        
        self._save_all_configs()
        self.console.print(f"[green]✅ Updated {model_type} model to: {model_name}[/green]")
    
    def show_current_config(self):
        """Display current configuration."""
        
        # Models table
        models_table = Table(title="🤖 Model Configuration")
        models_table.add_column("Type", style="cyan")
        models_table.add_column("Model", style="white")
        models_table.add_column("Provider", style="yellow")
        
        models_table.add_row("Primary", self.models.primary_model, self.models.provider)
        models_table.add_row("Code Analysis", self.models.code_model, self.models.provider)
        models_table.add_row("Reasoning", self.models.reasoning_model, self.models.provider)
        models_table.add_row("Fallback", self.models.fallback_model, self.models.provider)
        
        self.console.print(models_table)
        
        # Elite settings table
        elite_config = self.get_elite_config()
        elite_table = Table(title="💀 Elite Settings")
        elite_table.add_column("Setting", style="cyan")
        elite_table.add_column("Value", style="white")
        
        elite_table.add_row("Minimum Score Threshold", str(elite_config.minimum_score_threshold))
        elite_table.add_row("Max Parallel Agents", str(elite_config.max_parallel_agents))
        elite_table.add_row("Stealth Mode Default", "✅" if elite_config.stealth_mode_default else "❌")
        elite_table.add_row("Conference Worthy Threshold", str(elite_config.conference_worthy_threshold))
        
        self.console.print(elite_table)
        
        # MCP servers
        self._display_mcp_servers()

# Convenience function for getting configuration
def get_babayaga_config() -> BabaYagaConfigManager:
    """Get BabaYaga configuration manager instance."""
    return BabaYagaConfigManager()

# Configuration class for backward compatibility
class BabaYagaConfig:
    """Backward compatibility configuration class."""
    
    def __init__(self):
        self.manager = get_babayaga_config()
        
        # Check if this is first run
        if not self.manager.config_file.exists():
            self.manager.setup_initial_config()
    
    @property
    def model(self):
        return self.manager.models
    
    @property
    def elite(self):
        return self.manager.get_elite_config()
    
    @property
    def security_tools(self):
        return self.manager.get_security_tools_config()
    
    @property
    def mcp_servers(self):
        return self.manager.get_enabled_mcp_servers()
