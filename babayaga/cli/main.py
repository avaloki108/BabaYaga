import typer
from typing_extensions import Annotated
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
    model: Annotated[str, typer.Option(help="The model to use for the audit.")] = "qwen2.5-coder:7b"
):
    """
    Run a standard security audit on a smart contract or directory.
    """
    console.print(f"🔍 Starting standard audit on [cyan]{path}[/cyan] with model [cyan]{model}[/cyan]...")
    # This is where the old audit logic would go.
    console.print("Standard audit functionality is not yet implemented.")

@app.command()
def elite_hunt(
    path: Annotated[str, typer.Argument(help="Path to the target directory for the elite hunt.")],
    config: Annotated[str, typer.Option(help="Path to the TOML configuration file.")] = "config.toml"
):
    """
    Launch the Elite Hunt: a phased, multi-agent security analysis.
    """
    import asyncio
    try:
        orchestrator = Orchestrator(target_dir=path, config_path=config)
        asyncio.run(orchestrator.run())
    except Exception as e:
        console.print(f"[bold red]Failed to start elite hunt: {e}[/bold red]")

@app.command()
def mcp(
    model: Annotated[str, typer.Option(help="Ollama model to use.")] = "qwen2.5-coder:7b"
):
    """
    Start MCP chat mode - interact with Ollama and MCP servers.
    """
    import asyncio
    from babayaga.mcp.client import MCPClient
    
    async def run_mcp():
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
def status():
    """
    Check the status of BabaYaga and its dependencies.
    """
    console.print("Checking system status...")
    # This is where dependency checks would go.
    console.print("Status check functionality is not yet implemented.")

if __name__ == "__main__":
    app()