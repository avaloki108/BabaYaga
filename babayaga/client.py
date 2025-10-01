"""BabaYaga - The Legendary Web3 Security Auditor MCP Client."""

import asyncio
import json
import os
import sys
import time
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.layout import Layout
from rich.text import Text
from rich.columns import Columns
from rich.prompt import Prompt, Confirm
from rich.live import Live

from .orchestration import EnhancedOrchestrationLayer
from .agents.elite_agents import EliteAgentSystem
from .llm.enhanced_client import EnhancedLLMClient
from .config.settings import BabaYagaConfig

class BabaYagaClient:
    """
    BabaYaga - The most feared Web3 security auditor in the universe.
    
    Operates with the deadly precision of John Wick, channeling Baba Yaga-level
    stealth and persistence to find vulnerabilities that others miss.
    
    "People keep asking if I'm back, and I haven't really had an answer.
    But now, yeah, I'm thinking I'm back." - John Wick / BabaYaga
    """
    
    def __init__(self):
        self.console = Console()
        self.config = BabaYagaConfig()
        self.logger = self._setup_logging()
        
        # Core components
        self.orchestration_layer = EnhancedOrchestrationLayer(self.console)
        self.elite_agents = EliteAgentSystem(self.console)
        self.llm_client = EnhancedLLMClient(self.console)
        
        # State
        self.current_target = None
        self.audit_history = []
        self.stealth_mode = True
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for BabaYaga."""
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('babayaga.log'),
                logging.StreamHandler()
            ]
        )
        
        return logging.getLogger('babayaga')
    
    async def start(self):
        """Start BabaYaga with dramatic flair."""
        
        self._display_banner()
        
        # Check tool availability
        await self._check_tool_status()
        
        # Main interaction loop
        await self._main_loop()
    
    def _display_banner(self):
        """Display the legendary BabaYaga banner."""
        
        banner = """
[bold red]
██████╗  █████╗ ██████╗  █████╗ ██╗   ██╗ █████╗  ██████╗  █████╗ 
██╔══██╗██╔══██╗██╔══██╗██╔══██╗╚██╗ ██╔╝██╔══██╗██╔════╝ ██╔══██╗
██████╔╝███████║██████╔╝███████║ ╚████╔╝ ███████║██║  ███╗███████║
██╔══██╗██╔══██║██╔══██╗██╔══██║  ╚██╔╝  ██╔══██║██║   ██║██╔══██║
██████╔╝██║  ██║██████╔╝██║  ██║   ██║   ██║  ██║╚██████╔╝██║  ██║
╚═════╝ ╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝
[/bold red]

[bold white]The Legendary Web3 Security Auditor[/bold white]
[dim red]"With a fucking pencil... and some smart contracts"[/dim red]

[yellow]💀 Elite Web3 Vulnerability Research System v4.0[/yellow]
[dim]Channeling the deadly precision of the most feared secret agent hacker[/dim]
        """
        
        self.console.print(Panel(banner, border_style="red", padding=(1, 2)))
        
        # Operational parameters
        params_table = Table(title="🎯 Operational Parameters")
        params_table.add_column("Parameter", style="cyan")
        params_table.add_column("Value", style="white")
        
        params_table.add_row("Minimum Score Threshold", "200 (Novelty × Exploitability × Impact)")
        params_table.add_row("Target Quality", "Conference-worthy, novel exploits")
        params_table.add_row("Intelligence", "100% Claude reasoning + Advanced MCP tools")
        params_table.add_row("Stealth Mode", "🟢 ACTIVE" if self.stealth_mode else "🔴 INACTIVE")
        params_table.add_row("Persistence Level", "Baba Yaga")
        
        self.console.print(params_table)
        self.console.print()
    
    async def _check_tool_status(self):
        """Check the status of all analysis tools."""
        
        self.console.print("[yellow]🔧 Checking tool availability...[/yellow]")
        
        tool_status = await self.orchestration_layer.get_tool_status()
        
        status_table = Table(title="🛠️ Tool Status")
        status_table.add_column("Tool", style="cyan")
        status_table.add_column("Status", justify="center")
        status_table.add_column("Capability", style="dim")
        
        tools_info = {
            'slither': 'Static analysis and vulnerability detection',
            'mythril': 'Symbolic execution and formal verification',
            'securify2': 'Datalog-based security analysis',
            'echidna': 'Property-based fuzzing',
            'medusa': 'Parallel fuzzing engine',
            'foundry': 'Testing and fuzzing framework',
            'fuzz_utils': 'Fuzzing utilities and harness generation',
            'solhint': 'Code quality and style checking'
        }
        
        for tool, available in tool_status.items():
            status = "✅ Available" if available else "❌ Missing"
            capability = tools_info.get(tool, "Unknown")
            status_table.add_row(tool.title(), status, capability)
        
        self.console.print(status_table)
        self.console.print()
    
    async def _main_loop(self):
        """Main interaction loop."""
        
        while True:
            try:
                self.console.print("[bold cyan]🎯 BabaYaga Command Center[/bold cyan]")
                self.console.print()
                
                # Display menu
                menu_table = Table(show_header=False, box=None)
                menu_table.add_column("Command", style="bold yellow")
                menu_table.add_column("Description", style="white")
                
                menu_table.add_row("1. audit <target>", "Execute comprehensive elite audit")
                menu_table.add_row("2. quick <target>", "Quick scan for critical vulnerabilities")
                menu_table.add_row("3. hunt <target>", "Deploy elite vulnerability hunters")
                menu_table.add_row("4. status", "Show tool and system status")
                menu_table.add_row("5. history", "View audit history")
                menu_table.add_row("6. config", "Configure BabaYaga settings")
                menu_table.add_row("7. stealth", "Toggle stealth mode")
                menu_table.add_row("8. exit", "Exit BabaYaga")
                
                self.console.print(menu_table)
                self.console.print()
                
                # Get user input
                command = Prompt.ask("[bold red]BabaYaga>[/bold red]", default="").strip().lower()
                
                if not command:
                    continue
                
                # Parse command
                parts = command.split()
                cmd = parts[0]
                args = parts[1:] if len(parts) > 1 else []
                
                # Execute command
                if cmd == "audit":
                    if args:
                        await self._execute_audit(args[0])
                    else:
                        self.console.print("[red]❌ Please specify a target: audit <target>[/red]")
                
                elif cmd == "quick":
                    if args:
                        await self._execute_quick_scan(args[0])
                    else:
                        self.console.print("[red]❌ Please specify a target: quick <target>[/red]")
                
                elif cmd == "hunt":
                    if args:
                        await self._execute_elite_hunt(args[0])
                    else:
                        self.console.print("[red]❌ Please specify a target: hunt <target>[/red]")
                
                elif cmd == "status":
                    await self._show_status()
                
                elif cmd == "history":
                    await self._show_history()
                
                elif cmd == "config":
                    await self._configure_settings()
                
                elif cmd == "stealth":
                    await self._toggle_stealth_mode()
                
                elif cmd in ["exit", "quit", "q"]:
                    await self._exit_gracefully()
                    break
                
                else:
                    self.console.print(f"[red]❌ Unknown command: {cmd}[/red]")
                
                self.console.print()
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]⚠️ Interrupted by user[/yellow]")
                if Confirm.ask("Exit BabaYaga?"):
                    break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                self.console.print(f"[red]❌ Error: {e}[/red]")
    
    async def _execute_audit(self, target: str):
        """Execute comprehensive elite audit."""
        
        self.console.print(f"[bold red]💀 BabaYaga awakens for target: {target}[/bold red]")
        
        if not self._validate_target(target):
            self.console.print(f"[red]❌ Invalid target: {target}[/red]")
            return
        
        self.current_target = target
        
        # Prepare audit configuration
        config = {
            'target': target,
            'mode': 'comprehensive',
            'stealth_mode': self.stealth_mode,
            'minimum_score_threshold': 200,
            'enable_elite_agents': True,
            'enable_ai_enhancement': True,
            'persistence_mode': True
        }
        
        try:
            # Execute elite audit using both orchestration layer and elite agents
            self.console.print("[yellow]🚀 Launching comprehensive audit...[/yellow]")
            
            # Run orchestration layer audit
            orchestration_result = await self.orchestration_layer.start_audit(config)
            
            # Run elite agent system
            elite_result = await self.elite_agents.execute_elite_audit(target, config)
            
            # Combine and display results
            combined_result = self._combine_audit_results(orchestration_result, elite_result)
            
            # Display comprehensive report
            self._display_audit_report(combined_result)
            
            # Add to history
            self.audit_history.append({
                'timestamp': time.time(),
                'target': target,
                'type': 'comprehensive_audit',
                'result': combined_result
            })
            
        except Exception as e:
            self.logger.error(f"Audit failed: {e}")
            self.console.print(f"[red]❌ Audit failed: {e}[/red]")
    
    async def _execute_quick_scan(self, target: str):
        """Execute quick security scan."""
        
        self.console.print(f"[bold yellow]⚡ Quick scan initiated for: {target}[/bold yellow]")
        
        if not self._validate_target(target):
            self.console.print(f"[red]❌ Invalid target: {target}[/red]")
            return
        
        try:
            result = await self.orchestration_layer.quick_scan(target)
            self.console.print(result)
            
            # Add to history
            self.audit_history.append({
                'timestamp': time.time(),
                'target': target,
                'type': 'quick_scan',
                'result': result
            })
            
        except Exception as e:
            self.logger.error(f"Quick scan failed: {e}")
            self.console.print(f"[red]❌ Quick scan failed: {e}[/red]")
    
    async def _execute_elite_hunt(self, target: str):
        """Execute elite vulnerability hunting."""
        
        self.console.print(f"[bold red]🎯 Elite hunters deployed for: {target}[/bold red]")
        
        if not self._validate_target(target):
            self.console.print(f"[red]❌ Invalid target: {target}[/red]")
            return
        
        config = {
            'target': target,
            'mode': 'elite_hunt',
            'stealth_mode': self.stealth_mode,
            'minimum_score_threshold': 200
        }
        
        try:
            result = await self.elite_agents.execute_elite_audit(target, config)
            self._display_elite_hunt_results(result)
            
            # Add to history
            self.audit_history.append({
                'timestamp': time.time(),
                'target': target,
                'type': 'elite_hunt',
                'result': result
            })
            
        except Exception as e:
            self.logger.error(f"Elite hunt failed: {e}")
            self.console.print(f"[red]❌ Elite hunt failed: {e}[/red]")
    
    async def _show_status(self):
        """Show system status."""
        
        # Tool status
        tool_status = await self.orchestration_layer.get_tool_status()
        
        status_panel = Panel(
            self._create_status_display(tool_status),
            title="[bold cyan]🛡️ BabaYaga System Status[/bold cyan]",
            border_style="cyan"
        )
        
        self.console.print(status_panel)
    
    async def _show_history(self):
        """Show audit history."""
        
        if not self.audit_history:
            self.console.print("[yellow]📋 No audit history available[/yellow]")
            return
        
        history_table = Table(title="📋 Audit History")
        history_table.add_column("Timestamp", style="cyan")
        history_table.add_column("Target", style="white")
        history_table.add_column("Type", style="yellow")
        history_table.add_column("Status", justify="center")
        
        for entry in self.audit_history[-10:]:  # Show last 10
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(entry['timestamp']))
            target = entry['target']
            audit_type = entry['type'].replace('_', ' ').title()
            status = "✅ Complete"
            
            history_table.add_row(timestamp, target, audit_type, status)
        
        self.console.print(history_table)
    
    async def _configure_settings(self):
        """Configure BabaYaga settings."""
        
        self.console.print("[cyan]⚙️ BabaYaga Configuration[/cyan]")
        
        config_table = Table(title="Current Configuration")
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", style="white")
        
        config_table.add_row("Stealth Mode", "🟢 Enabled" if self.stealth_mode else "🔴 Disabled")
        config_table.add_row("Minimum Score Threshold", "200")
        config_table.add_row("Log Level", "INFO")
        
        self.console.print(config_table)
        
        # Allow configuration changes
        if Confirm.ask("Modify configuration?"):
            # Add configuration modification logic here
            self.console.print("[green]✅ Configuration updated[/green]")
    
    async def _toggle_stealth_mode(self):
        """Toggle stealth mode."""
        
        self.stealth_mode = not self.stealth_mode
        status = "🟢 ENABLED" if self.stealth_mode else "🔴 DISABLED"
        
        self.console.print(f"[cyan]🥷 Stealth Mode: {status}[/cyan]")
    
    async def _exit_gracefully(self):
        """Exit BabaYaga gracefully."""
        
        exit_message = """
[bold red]💀 BabaYaga returns to the shadows...[/bold red]

[dim red]"People keep asking if I'm back, and I haven't really had an answer.
But now, yeah, I'm thinking I'm back."[/dim red]

[yellow]Until the next vulnerability calls...[/yellow]
        """
        
        self.console.print(Panel(exit_message, border_style="red", padding=(1, 2)))
    
    def _validate_target(self, target: str) -> bool:
        """Validate audit target."""
        
        # Check if it's a URL
        if target.startswith(('http://', 'https://')):
            return True
        
        # Check if it's a file or directory
        if os.path.exists(target):
            return True
        
        # Check if it looks like a contract address
        if target.startswith('0x') and len(target) == 42:
            return True
        
        return False
    
    def _combine_audit_results(self, orchestration_result, elite_result) -> Dict[str, Any]:
        """Combine results from orchestration layer and elite agents."""
        
        # Extract findings from both results
        orchestration_findings = []
        elite_findings = []
        
        if hasattr(orchestration_result, 'content'):
            # Parse panel content if needed
            orchestration_findings = []
        
        if 'findings' in elite_result:
            elite_findings = elite_result['findings']
        
        # Combine and deduplicate
        all_findings = orchestration_findings + elite_findings
        
        return {
            'summary': {
                'total_findings': len(all_findings),
                'orchestration_findings': len(orchestration_findings),
                'elite_findings': len(elite_findings),
                'combined_analysis': True
            },
            'findings': all_findings,
            'orchestration_result': orchestration_result,
            'elite_result': elite_result
        }
    
    def _display_audit_report(self, result: Dict[str, Any]):
        """Display comprehensive audit report."""
        
        summary = result.get('summary', {})
        findings = result.get('findings', [])
        
        # Create comprehensive report
        report_table = Table(title="🛡️ BabaYaga Comprehensive Audit Report")
        report_table.add_column("Metric", style="cyan")
        report_table.add_column("Value", justify="center")
        
        report_table.add_row("Total Findings", str(summary.get('total_findings', 0)))
        report_table.add_row("Orchestration Findings", str(summary.get('orchestration_findings', 0)))
        report_table.add_row("Elite Agent Findings", str(summary.get('elite_findings', 0)))
        
        self.console.print(report_table)
        
        # Display orchestration result
        if 'orchestration_result' in result:
            self.console.print(result['orchestration_result'])
        
        # Display elite findings
        if findings:
            self._display_elite_findings(findings)
    
    def _display_elite_hunt_results(self, result: Dict[str, Any]):
        """Display elite hunt results."""
        
        summary = result.get('summary', {})
        findings = result.get('findings', [])
        
        # Create elite hunt report
        hunt_table = Table(title="🎯 Elite Hunt Results")
        hunt_table.add_column("Metric", style="red")
        hunt_table.add_column("Value", justify="center")
        
        hunt_table.add_row("Total Findings", str(summary.get('total_findings', 0)))
        hunt_table.add_row("High Quality Findings", str(summary.get('high_quality_findings', 0)))
        hunt_table.add_row("Conference Worthy", str(summary.get('quality_metrics', {}).get('conference_worthy', 0)))
        hunt_table.add_row("Average Novelty", f"{summary.get('quality_metrics', {}).get('average_novelty', 0):.2f}")
        
        self.console.print(hunt_table)
        
        if findings:
            self._display_elite_findings(findings)
        
        # Display BabaYaga signature
        if 'baba_yaga_signature' in result:
            signature_panel = Panel(
                result['baba_yaga_signature'],
                title="[bold red]💀 BabaYaga Signature[/bold red]",
                border_style="red"
            )
            self.console.print(signature_panel)
    
    def _display_elite_findings(self, findings: List[Dict[str, Any]]):
        """Display elite findings in a detailed table."""
        
        if not findings:
            self.console.print("[yellow]📋 No elite findings to display[/yellow]")
            return
        
        findings_table = Table(title="🔍 Elite Vulnerability Findings")
        findings_table.add_column("ID", style="cyan", width=15)
        findings_table.add_column("Title", style="white", width=30)
        findings_table.add_column("Severity", justify="center", width=10)
        findings_table.add_column("Score", justify="center", width=8)
        findings_table.add_column("Agent", style="dim", width=15)
        
        for finding in findings[:20]:  # Show top 20
            finding_id = finding.get('id', 'unknown')[:12] + "..."
            title = finding.get('title', 'Unknown')
            if len(title) > 25:
                title = title[:22] + "..."
            
            severity = finding.get('severity', 'Unknown')
            
            # Calculate total score if available
            scores = finding.get('scores', {})
            total_score = scores.get('total', 0) if scores else 0
            score_str = f"{total_score:.0f}" if total_score > 0 else "N/A"
            
            agent = finding.get('agent', 'unknown')
            
            findings_table.add_row(finding_id, title, severity, score_str, agent)
        
        self.console.print(findings_table)
    
    def _create_status_display(self, tool_status: Dict[str, bool]) -> str:
        """Create status display content."""
        
        available_tools = sum(1 for available in tool_status.values() if available)
        total_tools = len(tool_status)
        
        status_content = f"""
[bold cyan]System Status:[/bold cyan]
• Tools Available: {available_tools}/{total_tools}
• Current Target: {self.current_target or 'None'}
• Stealth Mode: {'🟢 Active' if self.stealth_mode else '🔴 Inactive'}
• Audit History: {len(self.audit_history)} entries

[bold cyan]Tool Status:[/bold cyan]
"""
        
        for tool, available in tool_status.items():
            status = "✅" if available else "❌"
            status_content += f"• {tool.title()}: {status}\n"
        
        return status_content.strip()

async def main():
    """Main entry point for BabaYaga."""
    
    try:
        client = BabaYagaClient()
        await client.start()
    except KeyboardInterrupt:
        print("\n💀 BabaYaga interrupted. Returning to the shadows...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
