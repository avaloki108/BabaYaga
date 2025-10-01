from pathlib import Path
from enum import Enum, auto
from rich.console import Console

console = Console()

class ProjectType(Enum):
    FOUNDRY = "Foundry"
    HARDHAT = "Hardhat"
    UNKNOWN = "Unknown"

def detect_project_type(target_dir: Path) -> ProjectType:
    """
    Detects the project type (Foundry or Hardhat) based on characteristic files.

    Args:
        target_dir: The root directory of the project to inspect.

    Returns:
        The detected ProjectType.
    """
    console.print(f"🔎 Detecting project type in [cyan]{target_dir}[/cyan]...")

    # Check for Foundry
    if (target_dir / "foundry.toml").is_file():
        console.print("[bold green]✅ Foundry project detected.[/bold green]")
        return ProjectType.FOUNDRY

    # Check for Hardhat
    if (target_dir / "hardhat.config.js").is_file() or (target_dir / "hardhat.config.ts").is_file():
        console.print("[bold green]✅ Hardhat project detected.[/bold green]")
        return ProjectType.HARDHAT

    console.print("[yellow]⚠️ Unknown project type. Build step will be skipped.[/yellow]")
    return ProjectType.UNKNOWN