import subprocess
from pathlib import Path
from rich.console import Console

from .detector import ProjectType

console = Console()

class ProjectBuilder:
    """Handles the build process for different project types."""

    def __init__(self, project_type: ProjectType, target_dir: Path):
        self.project_type = project_type
        self.target_dir = target_dir

    def build(self) -> bool:
        """
        Runs the appropriate build command for the project type.

        Returns:
            True if the build was successful, False otherwise.
        """
        if self.project_type == ProjectType.FOUNDRY:
            return self._run_command("forge build", "Foundry")
        elif self.project_type == ProjectType.HARDHAT:
            # Hardhat requires installing dependencies first
            console.print("⚙️ Installing npm dependencies for Hardhat project...")
            if not self._run_command("npm install", "Hardhat (npm install)"):
                return False
            return self._run_command("npx hardhat compile", "Hardhat (compile)")
        
        console.print("⚪ Build skipped for unknown project type.")
        return True # Return True as there's nothing to build

    def _run_command(self, command: str, build_name: str) -> bool:
        """A helper to run a shell command and stream its output."""
        console.print(f"🚀 Running build command: [bold magenta]{command}[/bold magenta]")
        try:
            # Using Popen to potentially stream output in the future
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=self.target_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8'
            )

            # Print output line by line
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    console.print(f"[dim]{build_name}:[/dim] {line.strip()}")
            
            process.wait()

            if process.returncode == 0:
                console.print(f"[bold green]✅ {build_name} build successful.[/bold green]")
                return True
            else:
                console.print(f"[bold red]❌ {build_name} build failed with exit code {process.returncode}.[/bold red]")
                return False

        except FileNotFoundError:
            console.print(f"[bold red]❌ Command not found: '{command.split()[0]}'. Is it installed and in your PATH?[/bold red]")
            return False
        except Exception as e:
            console.print(f"[bold red]❌ An unexpected error occurred during the {build_name} build: {e}[/bold red]")
            return False
