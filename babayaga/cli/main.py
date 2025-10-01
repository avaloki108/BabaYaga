#!/usr/bin/env python3
"""BabaYaga CLI - Unified interface supporting both typer commands and BabaYagaClient."""

import asyncio
import sys
import typer
from typing_extensions import Annotated
from pathlib import Path
from rich.console import Console

# Import the new Orchestrator class
from babayaga.orchestrator.main import Orchestrator

app = typer.Typer(
    name="babayaga",
    help="BabaYaga: Enhanced Smart Contract Security Auditing Platform",
    add_completion=False
)
console = Console()

@app.command()
def audit(
    path: Annotated[str, typer.Argument(help="Path to the smart contract or directory to audit.")],
    model: Annotated[str, typer.Option(help="The model to use for the audit.")] = "ollama/gpt-oss:20b",
    stealth: Annotated[bool, typer.Option(help="Enable stealth mode.")] = False,
    threshold: Annotated[int, typer.Option(help="Minimum score threshold for findings.")] = 200
):
    """
    Run a comprehensive security audit on a smart contract or directory.
    """
    async def run_audit():
        try:
            # Try to use BabaYagaClient if available
            from babayaga.client import BabaYagaClient
            client = BabaYagaClient()
            config = {
                'target': path,
                'mode': 'comprehensive',
                'stealth_mode': stealth,
                'minimum_score_threshold': threshold,
                'enable_elite_agents': True,
                'enable_ai_enhancement': True,
                'persistence_mode': True
            }
            await client._execute_audit(path)
        except ImportError:
            console.print("[yellow]BabaYagaClient not available, using basic audit[/yellow]")
            console.print(f"🔍 Starting standard audit on [cyan]{path}[/cyan] with model [cyan]{model}[/cyan]...")
            console.print("Standard audit functionality is not yet fully implemented.")
    
    asyncio.run(run_audit())

@app.command()
def elite_hunt(
    path: Annotated[str, typer.Argument(help="Path to the target directory for the elite hunt.")],
    config: Annotated[str, typer.Option(help="Path to the TOML configuration file.")] = "config.toml"
):
    """
    Launch the Elite Hunt: a phased, multi-agent security analysis with Ollama oversight.
    """
    async def run_elite_hunt():
        try:
            orchestrator = Orchestrator(target_dir=path, config_path=config)
            await orchestrator.run()
        except Exception as e:
            console.print(f"[bold red]Failed to start elite hunt: {e}[/bold red]")
            import traceback
            traceback.print_exc()
    
    asyncio.run(run_elite_hunt())

@app.command()
def quick(
    path: Annotated[str, typer.Argument(help="Path to scan.")]
):
    """
    Execute quick vulnerability scan.
    """
    async def run_quick():
        try:
            from babayaga.client import BabaYagaClient
            client = BabaYagaClient()
            await client._execute_quick_scan(path)
        except ImportError:
            console.print("[yellow]Quick scan requires BabaYagaClient[/yellow]")
        except Exception as e:
            console.print(f"[red]Quick scan failed: {e}[/red]")
    
    asyncio.run(run_quick())

@app.command()
def hunt(
    path: Annotated[str, typer.Argument(help="Path to hunt.")],
    agents: Annotated[int, typer.Option(help="Number of hunter agents to deploy.")] = 10
):
    """
    Deploy elite vulnerability hunters.
    """
    async def run_hunt():
        try:
            from babayaga.client import BabaYagaClient
            client = BabaYagaClient()
            await client._execute_elite_hunt(path)
        except ImportError:
            console.print("[yellow]Elite hunt requires BabaYagaClient[/yellow]")
        except Exception as e:
            console.print(f"[red]Elite hunt failed: {e}[/red]")
    
    asyncio.run(run_hunt())

@app.command()
def mcp(
    model: Annotated[str, typer.Option(help="Ollama model to use.")] = "ollama/gpt-oss:20b"
):
    """
    Start MCP chat mode - interact with Ollama and MCP servers.
    """
    async def run_mcp():
        from babayaga.mcp.client import MCPClient
        client = MCPClient(model=model, console=console)
        try:
            await client.chat_loop()
        finally:
            await client.cleanup()
    
    try:
        asyncio.run(run_mcp())
    except KeyboardInterrupt:
        console.print("\n[yellow]MCP chat ended[/yellow]")

@app.command()
def interactive():
    """
    Start interactive BabaYaga session.
    """
    async def run_interactive():
        try:
            from babayaga.client import BabaYagaClient
            client = BabaYagaClient()
            await client.start()
        except ImportError:
            console.print("[yellow]Interactive mode requires BabaYagaClient[/yellow]")
        except Exception as e:
            console.print(f"[red]Interactive mode failed: {e}[/red]")
    
    asyncio.run(run_interactive())

@app.command()
def status():
    """
    Check the status of BabaYaga and its dependencies.
    """
    console.print("Checking system status...")
    console.print("Status check functionality is not yet implemented.")

if __name__ == "__main__":
    app()
