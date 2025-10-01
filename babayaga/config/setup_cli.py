#!/usr/bin/env python3
"""BabaYaga Configuration CLI - Easy setup and management of BabaYaga configurations."""

import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .babayaga_config import BabaYagaConfigManager

def create_config_parser():
    """Create configuration CLI parser."""
    
    parser = argparse.ArgumentParser(
        prog='babayaga-config',
        description='BabaYaga Configuration Manager',
        epilog='Configure BabaYaga for your specific environment'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Configuration commands')
    
    # Setup command
    setup_parser = subparsers.add_parser(
        'setup',
        help='Interactive configuration setup'
    )
    setup_parser.add_argument(
        '--force',
        action='store_true',
        help='Force reconfiguration even if config exists'
    )
    
    # Show command
    show_parser = subparsers.add_parser(
        'show',
        help='Show current configuration'
    )
    
    # Model commands
    model_parser = subparsers.add_parser(
        'model',
        help='Model configuration'
    )
    model_subparsers = model_parser.add_subparsers(dest='model_command')
    
    # Set model
    set_model_parser = model_subparsers.add_parser('set', help='Set model')
    set_model_parser.add_argument('type', choices=['primary', 'code', 'reasoning', 'fallback'])
    set_model_parser.add_argument('model', help='Model name (e.g., qwen2.5-coder:32b)')
    
    # List models
    model_subparsers.add_parser('list', help='List available models')
    
    # MCP commands
    mcp_parser = subparsers.add_parser(
        'mcp',
        help='MCP server configuration'
    )
    mcp_subparsers = mcp_parser.add_subparsers(dest='mcp_command')
    
    # Import MCP config
    import_parser = mcp_subparsers.add_parser('import', help='Import MCP configuration')
    import_parser.add_argument('file', help='Path to MCP configuration file')
    
    # List MCP servers
    mcp_subparsers.add_parser('list', help='List MCP servers')
    
    # Add MCP server
    add_mcp_parser = mcp_subparsers.add_parser('add', help='Add MCP server')
    add_mcp_parser.add_argument('name', help='Server name')
    add_mcp_parser.add_argument('command', help='Command to run')
    add_mcp_parser.add_argument('--args', nargs='*', help='Command arguments')
    add_mcp_parser.add_argument('--cwd', help='Working directory')
    add_mcp_parser.add_argument('--env', action='append', help='Environment variables (KEY=VALUE)')
    
    # Enable/disable MCP server
    enable_parser = mcp_subparsers.add_parser('enable', help='Enable MCP server')
    enable_parser.add_argument('name', help='Server name')
    
    disable_parser = mcp_subparsers.add_parser('disable', help='Disable MCP server')
    disable_parser.add_argument('name', help='Server name')
    
    # Elite settings
    elite_parser = subparsers.add_parser(
        'elite',
        help='Elite audit settings'
    )
    elite_subparsers = elite_parser.add_subparsers(dest='elite_command')
    
    # Set threshold
    threshold_parser = elite_subparsers.add_parser('threshold', help='Set minimum score threshold')
    threshold_parser.add_argument('value', type=int, help='Threshold value')
    
    # Set max agents
    agents_parser = elite_subparsers.add_parser('agents', help='Set max parallel agents')
    agents_parser.add_argument('value', type=int, help='Number of agents')
    
    return parser

def main():
    """Main configuration CLI entry point."""
    
    console = Console()
    parser = create_config_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        config_manager = BabaYagaConfigManager(console)
        
        if args.command == 'setup':
            if args.force or not config_manager.config_file.exists():
                config_manager.setup_initial_config()
            else:
                console.print("[yellow]Configuration already exists. Use --force to reconfigure.[/yellow]")
        
        elif args.command == 'show':
            config_manager.show_current_config()
        
        elif args.command == 'model':
            handle_model_commands(config_manager, args, console)
        
        elif args.command == 'mcp':
            handle_mcp_commands(config_manager, args, console)
        
        elif args.command == 'elite':
            handle_elite_commands(config_manager, args, console)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Configuration cancelled.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

def handle_model_commands(config_manager, args, console):
    """Handle model-related commands."""
    
    if args.model_command == 'set':
        config_manager.update_model(args.type, args.model)
    
    elif args.model_command == 'list':
        show_available_models(console)

def show_available_models(console):
    """Show available models."""
    
    table = Table(title="🤖 Available Models")
    table.add_column("Provider", style="cyan")
    table.add_column("Model", style="white")
    table.add_column("Description", style="dim")
    
    models = [
        ("Ollama", "qwen2.5-coder:32b", "Best for code analysis (32B parameters)"),
        ("Ollama", "qwen2.5-coder:14b", "Good for code analysis (14B parameters)"),
        ("Ollama", "qwen2.5-coder:7b", "Fast code analysis (7B parameters)"),
        ("Ollama", "llama3.1:70b", "General reasoning (70B parameters)"),
        ("Ollama", "llama3.1:8b", "Fast general model (8B parameters)"),
        ("Ollama", "deepseek-coder:33b", "Alternative code model"),
        ("Ollama", "codellama:34b", "Meta's code model"),
        ("OpenAI", "gpt-4o", "Latest GPT-4 model"),
        ("OpenAI", "gpt-4o-mini", "Faster GPT-4 variant"),
        ("Anthropic", "claude-3-5-sonnet", "Claude 3.5 Sonnet"),
        ("Grok", "grok-beta", "xAI's Grok model"),
        ("Custom", "ollama/gpt-oss:20b", "Custom OSS model"),
        ("Custom", "ollama/your-model:tag", "Your custom model")
    ]
    
    for provider, model, description in models:
        table.add_row(provider, model, description)
    
    console.print(table)

def handle_mcp_commands(config_manager, args, console):
    """Handle MCP-related commands."""
    
    if args.mcp_command == 'import':
        config_path = Path(args.file).expanduser()
        if config_path.exists():
            config_manager._import_mcp_config(config_path)
            config_manager._save_all_configs()
        else:
            console.print(f"[red]File not found: {config_path}[/red]")
    
    elif args.mcp_command == 'list':
        config_manager._display_mcp_servers()
    
    elif args.mcp_command == 'add':
        from .babayaga_config import MCPServerConfig
        
        # Parse environment variables
        env = {}
        if args.env:
            for env_var in args.env:
                if '=' in env_var:
                    key, value = env_var.split('=', 1)
                    env[key] = value
        
        # Add server
        config_manager.mcp_servers[args.name] = MCPServerConfig(
            name=args.name,
            command=args.command,
            args=args.args or [],
            env=env,
            cwd=args.cwd
        )
        
        config_manager._save_all_configs()
        console.print(f"[green]✅ Added MCP server: {args.name}[/green]")
    
    elif args.mcp_command == 'enable':
        if args.name in config_manager.mcp_servers:
            config_manager.mcp_servers[args.name].disabled = False
            config_manager._save_all_configs()
            console.print(f"[green]✅ Enabled MCP server: {args.name}[/green]")
        else:
            console.print(f"[red]MCP server not found: {args.name}[/red]")
    
    elif args.mcp_command == 'disable':
        if args.name in config_manager.mcp_servers:
            config_manager.mcp_servers[args.name].disabled = True
            config_manager._save_all_configs()
            console.print(f"[yellow]Disabled MCP server: {args.name}[/yellow]")
        else:
            console.print(f"[red]MCP server not found: {args.name}[/red]")

def handle_elite_commands(config_manager, args, console):
    """Handle elite settings commands."""
    
    if args.elite_command == 'threshold':
        config_manager.config['elite']['minimum_score_threshold'] = args.value
        config_manager._save_all_configs()
        console.print(f"[green]✅ Set minimum score threshold to: {args.value}[/green]")
    
    elif args.elite_command == 'agents':
        config_manager.config['elite']['max_parallel_agents'] = args.value
        config_manager._save_all_configs()
        console.print(f"[green]✅ Set max parallel agents to: {args.value}[/green]")

if __name__ == "__main__":
    main()
