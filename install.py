#!/usr/bin/env python3
"""Enhanced installation script for BabaYaga with comprehensive setup."""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.prompt import Confirm

console = Console()

class BabaYagaInstaller:
    """Comprehensive installer for BabaYaga and its dependencies."""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.python_version = sys.version_info
        self.requirements_met = True
        
    def check_requirements(self):
        """Check system requirements."""
        
        console.print("[bold]🔍 Checking System Requirements[/bold]")
        
        req_table = Table(title="System Requirements")
        req_table.add_column("Requirement", style="cyan")
        req_table.add_column("Status", justify="center")
        req_table.add_column("Details", style="dim")
        
        # Python version check
        if self.python_version >= (3, 12):
            req_table.add_row("Python 3.12+", "[green]✅ PASS[/green]", f"Found {sys.version}")
        else:
            req_table.add_row("Python 3.12+", "[red]❌ FAIL[/red]", f"Found {sys.version}, but 3.12+ is required.")
            self.requirements_met = False
        
        # Node.js check
        node_version = self._check_command("node --version")
        if node_version:
            req_table.add_row("Node.js", "[green]✅ PASS[/green]", node_version.strip())
        else:
            req_table.add_row("Node.js", "[yellow]⚠️ MISSING[/yellow]", "Required for Hardhat integration.")
        
        # Docker check
        docker_version = self._check_command("docker --version")
        if docker_version:
            req_table.add_row("Docker", "[green]✅ PASS[/green]", docker_version.strip())
        else:
            req_table.add_row("Docker", "[yellow]⚠️ MISSING[/yellow]", "Optional for containerized deployment.")
        
        # Git check
        git_version = self._check_command("git --version")
        if git_version:
            req_table.add_row("Git", "[green]✅ PASS[/green]", git_version.strip())
        else:
            req_table.add_row("Git", "[red]❌ MISSING[/red]", "Required for repository analysis.")
            self.requirements_met = False
        
        console.print(req_table)
        
        if not self.requirements_met:
            console.print("\n[red]❌ Some requirements are not met. Please install missing dependencies and try again.[/red]")
            return False
        
        console.print("\n[green]✅ All requirements satisfied![/green]")
        return True
    
    def _check_command(self, command):
        """Check if a command exists and return its output."""
        try:
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                check=False,
                timeout=10
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
    
    def install_python_dependencies(self):
        """Install Python dependencies using uv or pip."""
        
        console.print("\n[bold]📦 Installing Python Dependencies[/bold]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Detecting package manager...", total=None)
            
            # Check for uv
            if self._check_command("uv --version"):
                progress.update(task, description="Installing with uv (recommended)...")
                install_cmd = ["uv", "pip", "install", "-e", ".[dev,test,security]"]
            else:
                progress.update(task, description="Installing with pip...")
                install_cmd = [sys.executable, "-m", "pip", "install", "-e", ".[dev,test,security]"]
            
            try:
                result = subprocess.run(
                    install_cmd,
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).parent,
                    check=False
                )
                
                if result.returncode == 0:
                    progress.update(task, completed=True, description="✅ Python dependencies installed.")
                    console.print("[green]✅ Python dependencies installed successfully.[/green]")
                    return True
                else:
                    progress.update(task, completed=True, description="❌ Python dependencies installation failed.")
                    console.print(f"[red]❌ Installation failed:\n{result.stderr}[/red]")
                    return False
                    
            except Exception as e:
                console.print(f"[red]❌ An unexpected error occurred: {e}[/red]")
                return False
    
    def install_security_tools(self):
        """Install security analysis tools like Foundry and Hardhat."""
        
        console.print("\n[bold]🛠️ Installing Additional Security Tools[/bold]")
        
        # Foundry installation
        if not self._check_command("forge --version"):
            if Confirm.ask("\nFoundry not found. Install Foundry?", default=True):
                self._install_foundry()
        else:
            console.print("[green]✅ Foundry is already installed.[/green]")
            
        # Hardhat installation (optional, if Node.js is present)
        if self._check_command("node --version"):
            if not self._check_command("hardhat --version"):
                 if Confirm.ask("\nHardhat not found. Install Hardhat globally?", default=True):
                    self._install_hardhat()
            else:
                console.print("[green]✅ Hardhat is already installed.[/green]")

    def _install_foundry(self):
        """Install Foundry using the official script."""
        console.print("Installing Foundry...")
        if self.system not in ["linux", "darwin"]:
            console.print("[yellow]⚠️ Automated Foundry installation is not supported on Windows.[/yellow]")
            console.print("Please install it manually from: https://getfoundry.sh")
            return

        if not self._check_command("curl --version"):
            console.print("[red]❌ `curl` is required to install Foundry. Please install it and try again.[/red]")
            return

        try:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                task = progress.add_task("Running Foundry installer...", total=None)
                
                # The official installer script handles `foundryup` itself.
                cmd = "curl -L https://foundry.paradigm.xyz | bash && source ~/.bashrc && foundryup"
                
                # Using shell=True is necessary for piping and subsequent commands.
                # Ensure security implications are understood for public scripts.
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)

                if result.returncode == 0 and "foundryup" in result.stdout:
                    progress.update(task, completed=True, description="✅ Foundry installed successfully.")
                    console.print("[green]✅ Foundry installed. You may need to restart your terminal to use the `forge` command.[/green]")
                else:
                    progress.update(task, completed=True, description="❌ Foundry installation failed.")
                    console.print(f"[red]❌ Foundry installation failed:\n{result.stderr}[/red]")
        except Exception as e:
            console.print(f"[red]❌ An error occurred during Foundry installation: {e}[/red]")

    def _install_hardhat(self):
        """Install Hardhat globally using npm."""
        console.print("Installing Hardhat...")
        if not self._check_command("npm --version"):
            console.print("[red]❌ `npm` is required to install Hardhat. Please install Node.js and npm, then try again.[/red]")
            return

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("npm install -g hardhat", total=None)
            try:
                result = subprocess.run(["npm", "install", "-g", "hardhat"], capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    progress.update(task, completed=True, description="✅ Hardhat installed successfully.")
                else:
                    progress.update(task, completed=True, description="❌ Hardhat installation failed.")
                    console.print(f"[red]❌ Hardhat installation failed:\n{result.stderr}[/red]")
            except Exception as e:
                console.print(f"[red]❌ An error occurred during Hardhat installation: {e}[/red]")

    def setup_ollama(self):
        """Setup Ollama for LLM integration."""
        
        console.print("\n[bold]🧠 Setting up Ollama (LLM Integration)[/bold]")
        
        if self._check_command("ollama --version"):
            console.print("[green]✅ Ollama is already installed.[/green]")
        else:
            console.print("Ollama not found. Attempting to install...")
            if self.system in ["linux", "darwin"]:
                if not self._check_command("curl --version"):
                    console.print("[red]❌ `curl` is required to install Ollama. Please install it and try again.[/red]")
                    return
                try:
                    cmd = "curl -fsSL https://ollama.ai/install.sh | sh"
                    subprocess.run(cmd, shell=True, check=True)
                    console.print("[green]✅ Ollama installed successfully.[/green]")
                    console.print("Please ensure the Ollama application is running before using BabaYaga.")
                except Exception as e:
                    console.print(f"[red]❌ Ollama installation failed: {e}[/red]")
                    console.print("Please install it manually from: https://ollama.ai/download")
                    return
            else:
                console.print("[yellow]⚠️ Please install Ollama manually on Windows from: https://ollama.ai/download[/yellow]")
                return
        
        if self._check_command("ollama --version") and Confirm.ask("\nDownload recommended AI models?", default=True):
            self._download_recommended_models()
    
    def _download_recommended_models(self):
        """Download recommended AI models."""
        
        recommended_models = [
            "qwen2.5-coder:7b",
            "llama3.1:8b",
            "codellama:7b"
        ]
        
        console.print("\n[bold]📥 Downloading Recommended Models[/bold] (this may take a while)...")
        
        for model in recommended_models:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                task = progress.add_task(f"Pulling {model}...", total=None)
                try:
                    result = subprocess.run(["ollama", "pull", model], capture_output=True, text=True, check=False, timeout=600)
                    if result.returncode == 0:
                        progress.update(task, completed=True, description=f"✅ {model} downloaded.")
                    else:
                        progress.update(task, completed=True, description=f"❌ Failed to download {model}.")
                        console.print(f"[yellow]Warning: Could not download {model}. You can pull it manually later.[/yellow]")
                except subprocess.TimeoutExpired:
                    progress.update(task, completed=True, description=f"❌ Timeout downloading {model}.")
                    console.print(f"[red]Error: Timeout while trying to download {model}.[/red]")
                except Exception as e:
                    console.print(f"[red]An error occurred while downloading {model}: {e}[/red]")
    
    def create_config(self):
        """Create initial configuration."""
        
        console.print("\n[bold]⚙️ Creating Default Configuration[/bold]")
        
        config_dir = Path.home() / ".babayaga"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.toml"
        
        if config_file.exists():
            if not Confirm.ask(f"Configuration file already exists at {config_file}. Overwrite?", default=False):
                console.print("[yellow]Skipping configuration creation.[/yellow]")
                return
        
        default_config = """[model]
default_model = "ollama/gpt-oss:20b"
temperature = 0.7
top_p = 0.9
max_tokens = 2000

[tools]
slither_enabled = true
mythril_enabled = true
foundry_enabled = true
hardhat_enabled = true # Set to false if you don't use Hardhat

[audit]
parallel_execution = true
detailed_reports = true
export_format = "json"

[output]
console_style = "rich"
log_level = "INFO"
"""
        try:
            config_file.write_text(default_config)
            console.print(f"[green]✅ Default configuration created at: {config_file}[/green]")
        except Exception as e:
            console.print(f"[red]❌ Failed to create configuration file: {e}[/red]")
    
    def run_installation(self):
        """Run the complete installation process."""
        
        banner = """
╦ ╦┌─┐┌┐ ╔═╗╔═╗┬ ┬┌┬┐┬┌┬┐╔╦╗╔═╗╔═╗
║║║├┤ ├┴┐╠═╣║ ║ ║ │││ │ ║║║║ ║╠═╝
╚╩╝└─┘└─┘╩ ╩╚═╝ ╚═╝─┴┘┴ ┴ ╩ ╩╚═╝╩  

Enhanced Smart Contract Security Auditing Platform
        """
        
        console.print(Panel(
            f"[bold cyan]{banner}[/bold cyan]\n\n[bold]🚀 Installation Wizard[/bold]",
            title="BabaYaga Installer",
            border_style="green"
        ))
        
        if not self.check_requirements():
            return
        
        if not self.install_python_dependencies():
            return

        self.install_security_tools()
        self.setup_ollama()
        self.create_config()
        
        console.print("\n" + "="*60)
        console.print(Panel(
            "[bold green]🎉 Installation Complete![/bold green]\n\n"
            "[bold]Next Steps:[/bold]\n"
            "1. Run `babayaga` to start the interactive client.\n"
            "2. Try an audit: `babayaga audit ./path/to/contract`\n"
            "3. Check system status: `babayaga status`\n\n"
            "[dim]For more commands, use: `babayaga --help`[/dim]",
            title="🛡️ BabaYaga is Ready",
            border_style="green"
        ))

def main():
    """Main installation entry point."""
    installer = BabaYagaInstaller()
    try:
        installer.run_installation()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Installation cancelled by user.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]An unexpected error occurred during installation: {e}[/bold red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
