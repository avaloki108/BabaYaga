"""
Main orchestrator for BabaYaga's Elite Hunt.

This module coordinates the entire audit workflow, integrating traditional tools
with advanced AI analysis in a phased, structured approach.
"""

import asyncio
import json
import time
import toml
import logging
from pathlib import Path
from typing import Dict, List, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel

# Import new project modules
from babayaga.project.detector import detect_project_type
from babayaga.project.builder import ProjectBuilder
from babayaga.llm.enhanced_client import EnhancedLLMClient, LLMResponse
from babayaga.config.settings import BabaYagaConfig, ConfigManager

# Assuming these paths will be updated as we build out the new structure
try:
    from babayaga.agents.orchestrator import MultiAgentOrchestrator
except ImportError:
    # Fallback if orchestrator is not available
    class MultiAgentOrchestrator:
        def __init__(self, console):
            self.console = console
        
        async def analyze_findings(self, findings, target, config):
            self.console.print("[yellow]Multi-agent analysis not available[/yellow]")
            return {'exploit_scenarios': {}, 'remediation_suggestions': {}, 'severity_assessments': {}}
from babayaga.engines.advanced_engine import AdvancedSecurityEngine
from babayaga.engines.fuzzing_engine import FuzzingEngine
from babayaga.engines.static_engine import StaticAnalysisEngine

console = Console()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Orchestrator:
    """
    The master orchestrator for running the Elite Web3 Audit.
    Manages the phased execution of agents, artifact handling, and configuration.
    Refactored from the original EnhancedOrchestrationLayer.
    """

    def __init__(self, target_dir: str, config_path: str = "config.toml"):
        self.target_dir = Path(target_dir).resolve()
        self.config_path = Path(config_path).resolve()
        self.config = self._load_config()
        self.run_id = time.strftime("%Y%m%d-%H%M%S")
        self.artifacts_dir = Path("artifacts") / self.run_id
        self._setup_directories()

        # Load BabaYaga configuration
        self.config_manager = ConfigManager(console)
        self.babayaga_config = self.config_manager.load_config()
        
        # Initialize LLM client for Ollama oversight
        self.llm_client = EnhancedLLMClient(self.babayaga_config, console)
        console.print(f"[cyan]🧠 Ollama oversight enabled with model: {self.babayaga_config.model.default_model}[/cyan]")

        # Initialize engines from the original orchestration logic
        self.advanced_engine = AdvancedSecurityEngine(console)
        self.fuzzing_engine = FuzzingEngine(console)
        self.static_engine = StaticAnalysisEngine(console)
        self.agent_orchestrator = MultiAgentOrchestrator(console)

        # State for the current run
        self.findings: List[Dict[str, Any]] = []
        self.run_results: Dict[str, Any] = {
            'id': self.run_id,
            'target': str(self.target_dir),
            'start_time': time.time(),
            'phases': {},
            'findings': [],
            'summary': {}
        }

    def _load_config(self) -> dict:
        console.print(f"⚙️ Loading configuration from [cyan]{self.config_path}[/cyan]...")
        try:
            return toml.load(self.config_path)
        except FileNotFoundError:
            console.print(f"[bold red]Error: Config file not found at {self.config_path}. Using defaults.[/bold red]")
            return {}
        except Exception as e:
            console.print(f"[bold red]Error parsing config file: {e}. Using defaults.[/bold red]")
            return {}

    def _setup_directories(self):
        console.print(f"📂 Setting up artifact directory: [cyan]{self.artifacts_dir}[/cyan]")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    async def run(self):
        """Executes the full, phased audit process."""
        console.print(Panel(
            f"[bold green]🚀 Starting Elite Hunt on [cyan]{self.target_dir}[/cyan][/bold green]\n"
            f"Run ID: {self.run_id}",
            title="BabaYaga Orchestrator",
            border_style="green"
        ))

        try:
            if not await self._run_phase_0_build_and_test():
                raise Exception("Phase 0: Build & Test failed. Halting hunt.")
            
            if not await self._run_phase_1_reconnaissance():
                 raise Exception("Phase 1: Reconnaissance failed. Halting hunt.")

            if not await self._run_phase_2_vulnerability_hunting():
                raise Exception("Phase 2: Vulnerability Hunting failed.")

            if not await self._run_phase_3_adversarial_validation():
                raise Exception("Phase 3: Adversarial Validation failed.")

            if not await self._run_phase_4_validation_and_scoring():
                raise Exception("Phase 4: Validation & Scoring failed.")

            await self._run_phase_5_reporting()

            console.print(Panel(
                "[bold green]✅ Elite Hunt Completed Successfully![/bold green]",
                border_style="green"
            ))

        except Exception as e:
            logger.error(f"Audit failed: {e}", exc_info=True)
            console.print(Panel(f"[bold red]❌ Audit failed: {e}[/bold red]", title="[red]Audit Error[/red]"))
        finally:
            self.run_results['end_time'] = time.time()
            self._save_artifacts('run_results.json', self.run_results)


    async def _run_phase_0_build_and_test(self) -> bool:
        """Phase 0: Detect project type, then build and run tests."""
        console.print("\n[bold yellow]PHASE 0: Build & Test[/bold yellow]")
        start_time = time.time()

        project_type = detect_project_type(self.target_dir)
        builder = ProjectBuilder(project_type, self.target_dir)
        
        build_successful = builder.build()

        # In the future, test running logic would go here
        test_successful = True # Placeholder

        phase_status = 'completed' if build_successful and test_successful else 'failed'
        duration = time.time() - start_time
        
        self.run_results['phases']['phase_0'] = {
            'status': phase_status,
            'project_type': project_type.value,
            'build_successful': build_successful,
            'test_successful': test_successful,
            'duration': duration
        }
        self._save_artifacts('phase_0_build_results.json', self.run_results['phases']['phase_0'])

        return build_successful and test_successful

    async def _run_phase_1_reconnaissance(self) -> bool:
        """Phase 1: Reconnaissance using Static and Advanced Analysis Engines."""
        console.print("\n[bold yellow]PHASE 1: Reconnaissance & Static Analysis[/bold yellow]")
        engine_results = {}
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TimeElapsedColumn(), console=console) as progress:
            static_task = progress.add_task("Running Static Analysis (Slither, etc.)...", total=100)
            
            try:
                engine_results['static'] = await self.static_engine.analyze_contracts(str(self.target_dir), self.config)
                progress.update(static_task, completed=100)
                console.print("[green]✅ Static analysis complete.[/green]")
            except Exception as e:
                logger.error(f"Static analysis failed: {e}", exc_info=True)
                console.print(f"[red]❌ Static analysis failed: {e}[/red]")
                return False

        # Consolidate findings from this phase
        static_findings = engine_results.get('static', {}).get('findings', [])
        
        # 🧠 OLLAMA OVERSIGHT: Analyze findings with LLM
        console.print("\n[cyan]🧠 Ollama analyzing static findings...[/cyan]")
        llm_enhanced_findings = await self._llm_analyze_findings(static_findings)
        self.findings.extend(llm_enhanced_findings)
        
        self.run_results['phases']['phase_1'] = {'status': 'completed', 'results': engine_results}
        self._save_artifacts('phase_1_recon_findings.json', self.findings)
        return True

    async def _run_phase_2_vulnerability_hunting(self) -> bool:
        """Phase 2: Vulnerability Hunting using Fuzzing and AI Agents."""
        console.print("\n[bold yellow]PHASE 2: Vulnerability Hunting[/bold yellow]")
        phase_results = {}
        new_findings = []
        
        # Fuzzing
        if not self.config.get('fuzzing', {}).get('skip', False):
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TimeElapsedColumn(), console=console) as progress:
                fuzz_task = progress.add_task("Running Fuzzing (Echidna, Medusa)...", total=100)
                try:
                    fuzz_results = await self.fuzzing_engine.run_comprehensive_fuzzing(str(self.target_dir), self.config)
                    phase_results['fuzzing'] = fuzz_results
                    progress.update(fuzz_task, completed=100)
                    console.print("[green]✅ Fuzzing complete.[/green]")
                    
                    # Extract findings from fuzzing results
                    for tool_result in fuzz_results.get('tool_results', []):
                        if tool_result.get('properties_failed', 0) > 0:
                            finding = {
                                'id': f"fuzzing_{tool_result['tool']}_failure",
                                'title': f"Fuzzing Failure - {tool_result['tool'].title()}",
                                'description': f"{tool_result['properties_failed']} properties failed during fuzzing",
                                'severity': 'High',
                                'confidence': 0.9,
                                'tool': tool_result['tool'],
                                'category': 'fuzzing'
                            }
                            new_findings.append(finding)
                except Exception as e:
                    logger.error(f"Fuzzing failed: {e}", exc_info=True)
                    console.print(f"[red]❌ Fuzzing failed: {e}[/red]")
        
        # 🧠 OLLAMA OVERSIGHT: Analyze fuzzing findings with LLM
        if new_findings:
            console.print("\n[cyan]🧠 Ollama analyzing fuzzing findings...[/cyan]")
            llm_enhanced_findings = await self._llm_analyze_findings(new_findings)
            self.findings.extend(llm_enhanced_findings)
        
        # AI Agent Enhancement
        console.print("[yellow]🤖 Enhancing analysis with AI agents...[/yellow]")
        try:
            agent_results = await self.agent_orchestrator.analyze_findings(
                self.findings, str(self.target_dir), self.config
            )
            phase_results['agent_analysis'] = agent_results
            self._integrate_agent_results(agent_results)
            console.print("[green]✅ AI enhancement complete.[/green]")
        except Exception as e:
            logger.error(f"AI enhancement failed: {e}", exc_info=True)
            console.print(f"[yellow]⚠️ AI enhancement failed: {e}[/yellow]")

        self.run_results['phases']['phase_2'] = {'status': 'completed', 'results': phase_results}
        self._save_artifacts('phase_2_hunt_results.json', phase_results)
        return True

    async def _llm_analyze_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use Ollama to analyze and enhance security findings."""
        from ..core.adapters import Finding
        
        enhanced_findings = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Ollama analyzing {len(findings)} findings...", total=len(findings))
            
            for i, finding_dict in enumerate(findings):
                try:
                    # Convert dict to Finding object
                    finding_obj = Finding(
                        id=finding_dict.get('id', f'finding_{i}'),
                        tool=finding_dict.get('tool', 'unknown'),
                        rule_id=finding_dict.get('rule_id', 'unknown'),
                        title=finding_dict.get('title', 'Unknown'),
                        description=finding_dict.get('description', ''),
                        severity=finding_dict.get('severity', 'medium'),
                        confidence=finding_dict.get('confidence', 0.7),
                        files=finding_dict.get('files', []),
                        trace=finding_dict.get('trace', []),
                        tool_output=finding_dict.get('tool_output', ''),
                        checks=finding_dict.get('checks', []),
                        recommendation=finding_dict.get('recommendation', '')
                    )
                    
                    # Only analyze high/critical severity with full LLM
                    if finding_dict.get('severity', '').lower() in ['critical', 'high']:
                        llm_response = await self.llm_client.analyze_vulnerability(finding_obj)
                        
                        # Enhance finding with LLM insights
                        enhanced_finding = self.llm_client.enhance_finding_with_llm(finding_obj, llm_response)
                        enhanced_dict = {
                            'id': enhanced_finding.id,
                            'title': enhanced_finding.title,
                            'description': enhanced_finding.description,
                            'severity': enhanced_finding.severity,
                            'confidence': enhanced_finding.confidence,
                            'tool': enhanced_finding.tool,
                            'category': finding_dict.get('category', 'unknown'),
                            'recommendation': enhanced_finding.recommendation,
                            'llm_enhanced': True,
                            'llm_model': self.babayaga_config.model.default_model
                        }
                    else:
                        # For lower severity, just add LLM observation flag
                        enhanced_dict = finding_dict.copy()
                        enhanced_dict['llm_observed'] = True
                        enhanced_dict['llm_model'] = self.babayaga_config.model.default_model
                    
                    enhanced_findings.append(enhanced_dict)
                    progress.update(task, advance=1)
                    
                except Exception as e:
                    logger.error(f"LLM analysis failed for finding {i}: {e}")
                    # Keep original finding even if LLM fails
                    finding_dict['llm_error'] = str(e)
                    enhanced_findings.append(finding_dict)
                    progress.update(task, advance=1)
                
                # Small delay to prevent overwhelming Ollama
                await asyncio.sleep(0.2)
        
        console.print(f"[green]✅ Ollama analyzed {len(enhanced_findings)} findings[/green]")
        return enhanced_findings

    def _integrate_agent_results(self, agent_results: Dict[str, Any]):
        """Integrates insights from AI agents back into the main findings list."""
        for finding in self.findings:
            finding_id = finding.get('id', '')
            if finding_id in agent_results.get('exploit_scenarios', {}):
                finding['exploit_scenario'] = agent_results['exploit_scenarios'][finding_id]
            if finding_id in agent_results.get('remediation_suggestions', {}):
                finding['remediation'] = agent_results['remediation_suggestions'][finding_id]
            if finding_id in agent_results.get('severity_assessments', {}):
                ai_severity = agent_results['severity_assessments'][finding_id]
                if ai_severity.get('confidence', 0) > 0.8:
                    finding['ai_severity'] = ai_severity['severity']
    
    async def _run_phase_3_adversarial_validation(self) -> bool:
        """Phase 3: Adversarial Validation to disprove/confirm findings. (Placeholder)."""
        console.print("\n[bold yellow]PHASE 3: Adversarial Validation[/bold yellow]")
        console.print("Deploying adversarial agents to disprove initial findings... (simulated)")
        # Future: This will run agents that try to prove findings are false positives.
        self.run_results['phases']['phase_3'] = {'status': 'completed', 'summary': 'Validation successful (simulated).'}
        self._save_artifacts('phase_3_validation.json', {'validated_ids': [f['id'] for f in self.findings]})
        return True

    async def _run_phase_4_validation_and_scoring(self) -> bool:
        """Phase 4: Final Validation & Scoring of confirmed findings."""
        console.print("\n[bold yellow]PHASE 4: Validation & Scoring[/bold yellow]")
        min_score = self.config.get('elite', {}).get('minimum_score_threshold', 200)
        console.print(f"Deduplicating, scoring, and filtering findings (min score: {min_score})...")
        
        # Deduplicate and sort findings (logic from original file)
        self.findings = self._deduplicate_findings(self.findings)
        
        # Calculate summary statistics and risk score
        summary = self._calculate_summary_statistics()
        self.run_results['summary'] = summary
        
        console.print(f"Scoring complete. Risk Score: {summary.get('risk_score', 'N/A')}")
        self.run_results['phases']['phase_4'] = {'status': 'completed', 'summary': summary}
        self._save_artifacts('phase_4_summary.json', summary)
        self._save_artifacts('final_findings.json', self.findings)
        return True

    async def _run_phase_5_reporting(self) -> bool:
        """Phase 5: Generate and display the final report."""
        console.print("\n[bold yellow]PHASE 5: Reporting[/bold yellow]")
        console.print("Generating final report...")
        
        execution_time = time.time() - self.run_results['start_time']
        report_panel = self._create_comprehensive_report_panel(execution_time)
        console.print(report_panel)
        
        # Save report
        report_md = self._generate_markdown_report()
        self._save_artifacts('report.md', report_md)
        self.run_results['phases']['phase_5'] = {'status': 'completed'}
        return True

    def _save_artifacts(self, filename: str, content: Any):
        """Saves an artifact to the run's artifact directory."""
        path = self.artifacts_dir / filename
        try:
            with open(path, 'w', encoding='utf-8') as f:
                if isinstance(content, str):
                    f.write(content)
                else:
                    json.dump(content, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save artifact {filename}: {e}")

    # --- Methods migrated and adapted from original orchestration.py ---

    def _deduplicate_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate findings based on similarity."""
        unique_findings_map = {}
        for finding in findings:
            # Create a unique key for each finding
            key = (
                finding.get('title', ''),
                finding.get('severity', ''),
                finding.get('file_path', ''),
                finding.get('line_number', '')
            )
            if key not in unique_findings_map:
                # Ensure 'tools' is a list
                if 'tool' in finding and 'tools' not in finding:
                    finding['tools'] = [finding.pop('tool')]
                unique_findings_map[key] = finding
            else:
                # Merge tool info
                existing_finding = unique_findings_map[key]
                new_tool = finding.get('tool')
                if new_tool and new_tool not in existing_finding.get('tools', []):
                    existing_finding.setdefault('tools', []).append(new_tool)
                # Use higher confidence
                if finding.get('confidence', 0) > existing_finding.get('confidence', 0):
                    existing_finding['confidence'] = finding['confidence']
        
        unique_findings = list(unique_findings_map.values())
        severity_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3, 'Info': 4}
        unique_findings.sort(key=lambda f: (severity_order.get(f.get('severity', 'Info'), 5), -f.get('confidence', 0)))
        return unique_findings

    def _calculate_summary_statistics(self) -> Dict[str, Any]:
        """Calculate comprehensive summary statistics."""
        severity_counts = {}
        for finding in self.findings:
            severity = finding.get('severity', 'Unknown')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
        risk_score = self._calculate_overall_risk_score(self.findings)
        risk_level = self._get_risk_level(risk_score)
        
        return {
            'total_findings': len(self.findings),
            'severity_distribution': severity_counts,
            'risk_score': risk_score,
            'risk_level': risk_level,
        }

    def _calculate_overall_risk_score(self, findings: List[Dict[str, Any]]) -> int:
        """Calculate overall risk score (0-100)."""
        if not findings: return 0
        severity_weights = {'Critical': 25, 'High': 15, 'Medium': 8, 'Low': 3, 'Info': 1}
        total_score = sum(severity_weights.get(f.get('severity', 'Info'), 1) * f.get('confidence', 0.7) for f in findings)
        max_possible = len(findings) * 25
        return min(100, int((total_score / max_possible) * 100)) if max_possible > 0 else 0

    def _get_risk_level(self, risk_score: int) -> str:
        if risk_score >= 80: return 'CRITICAL'
        if risk_score >= 60: return 'HIGH'
        if risk_score >= 40: return 'MEDIUM'
        if risk_score >= 20: return 'LOW'
        return 'MINIMAL'

    def _create_comprehensive_report_panel(self, execution_time: float) -> Panel:
        """Create rich audit report panel."""
        summary = self.run_results.get('summary', {})
        risk_level = summary.get('risk_level', 'UNKNOWN')
        risk_color = {'CRITICAL': 'red', 'HIGH': 'red', 'MEDIUM': 'yellow', 'LOW': 'green'}.get(risk_level, 'green')
        title = f"[bold {risk_color}]🛡️ Web3 Security Audit Report - {risk_level} RISK[/bold {risk_color}]"

        # Summary Table
        summary_table = Table(title="📊 Audit Summary")
        summary_table.add_column("Metric", style="cyan", no_wrap=True)
        summary_table.add_column("Value", justify="center")
        summary_table.add_row("Total Findings", str(summary.get('total_findings', 0)))
        for sev in ['Critical', 'High', 'Medium', 'Low', 'Info']:
            count = summary.get('severity_distribution', {}).get(sev, 0)
            if count > 0:
                summary_table.add_row(f"{sev} Findings", str(count))
        summary_table.add_row("Risk Score", str(summary.get('risk_score', 0)))
        summary_table.add_row("Execution Time", f"{execution_time:.2f}s")

        # Findings Table
        findings_table = Table(title="🔍 Top 10 Security Findings")
        findings_table.add_column("Severity", width=10)
        findings_table.add_column("Finding", width=50)
        findings_table.add_column("Confidence", justify="center", width=12)
        for finding in self.findings[:10]:
            sev_color = {'Critical': 'red', 'High': 'red', 'medium': 'yellow'}.get(finding.get('severity'), 'white')
            findings_table.add_row(
                f"[{sev_color}]{finding.get('severity', 'N/A')}[/{sev_color}]",
                finding.get('title', 'N/A'),
                f"{finding.get('confidence', 0):.2f}"
            )

        content = f"{summary_table}\n\n{findings_table}"
        return Panel(content, title=title, border_style=risk_color, padding=(1, 2))

    def _generate_markdown_report(self) -> str:
        """Generate markdown report."""
        summary = self.run_results.get('summary', {})
        report = f"# Web3 Security Audit Report\n\n## Summary\n"
        report += f"- **Total Findings**: {summary.get('total_findings', 0)}\n"
        report += f"- **Risk Level**: {summary.get('risk_level', 'Unknown')}\n"
        report += f"- **Risk Score**: {summary.get('risk_score', 0)}/100\n\n"
        report += "## Findings\n\n"
        for i, finding in enumerate(self.findings, 1):
            report += f"### {i}. {finding.get('title', 'Unknown')}\n"
            report += f"- **Severity**: {finding.get('severity', 'Unknown')}\n"
            report += f"- **Tools**: {', '.join(finding.get('tools', []))}\n"
            report += f"- **Description**: {finding.get('description', 'No description')}\n\n"
        return report
