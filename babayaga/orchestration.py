"""
Enhanced orchestration layer for BabaYaga Web3 security auditing.

This module coordinates the entire audit workflow, integrating traditional tools
with advanced AI analysis for comprehensive security assessment.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from rich.console import Console
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .analysis_engine import AnalysisEngine
from .agents.elite_agents import EliteAgentSystem
from .llm.enhanced_client import EnhancedLLMClient, LLMResponse
from .core.adapters import Finding
from .config.settings import BabaYagaConfig
from .modules.slither_module import SlitherModule
from .modules.mythril_module import MythrilModule
from .modules.foundry_module import FoundryModule
from .engines.advanced_engine import AdvancedSecurityEngine
from .engines.fuzzing_engine import FuzzingEngine
from .engines.static_engine import StaticAnalysisEngine
from .agents.orchestrator import MultiAgentOrchestrator

class EnhancedOrchestrationLayer:
    """
    Enhanced orchestration layer that coordinates multiple analysis engines:
    - Advanced Security Engine (Mythril Enhanced, Securify2, Custom)
    - Fuzzing Engine (Echidna, Medusa, fuzz-utils)
    - Static Analysis Engine (Slither, Securify2, Solhint, Custom)
    - Multi-Agent System (Vulnerability Detection, Exploit Scenarios, Fix Recommendations)
    - LLM Enhancement (AI-powered analysis and recommendations)
    """
    
    def __init__(self, console: Console):
        self.console = console
        self.logger = logging.getLogger(__name__)
        
        # Initialize engines
        self.advanced_engine = AdvancedSecurityEngine(console)
        self.fuzzing_engine = FuzzingEngine(console)
        self.static_engine = StaticAnalysisEngine(console)
        
        # Initialize multi-agent system
        self.agent_orchestrator = MultiAgentOrchestrator(console)
        
        # Initialize LLM client
        self.llm_client = EnhancedLLMClient(console)
        
        # Analysis history
        self.analysis_history = []
        self.current_analysis = None
        
    async def start_audit(self, config: Dict[str, Any]) -> Panel:
        """
        Start comprehensive security audit using all available engines.
        
        Args:
            config: Audit configuration containing target and options
            
        Returns:
            Rich Panel with audit results
        """
        
        target = config.get('target', '')
        if not target:
            return Panel("[red]❌ No target specified for audit[/red]", title="Error")
        
        # Validate target
        if not self._validate_target(target):
            return Panel(f"[red]❌ Invalid target: {target}[/red]", title="Error")
        
        # Start comprehensive analysis
        start_time = time.time()
        
        try:
            # Create analysis session
            analysis_session = {
                'id': f"audit_{int(start_time)}",
                'target': target,
                'start_time': start_time,
                'config': config,
                'status': 'running'
            }
            
            self.current_analysis = analysis_session
            
            # Run comprehensive analysis
            results = await self._run_comprehensive_analysis(target, config)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            analysis_session['execution_time'] = execution_time
            analysis_session['results'] = results
            analysis_session['status'] = 'completed'
            
            # Add to history
            self.analysis_history.append(analysis_session)
            
            # Generate comprehensive report panel
            return self._create_comprehensive_report_panel(results, execution_time)
            
        except Exception as e:
            self.logger.error(f"Audit failed: {e}")
            if self.current_analysis:
                self.current_analysis['status'] = 'failed'
                self.current_analysis['error'] = str(e)
            
            return Panel(
                f"[red]❌ Audit failed: {e}[/red]",
                title="[red]Audit Error[/red]",
                border_style="red"
            )
    
    async def quick_scan(self, target: str) -> Panel:
        """
        Run quick security scan focusing on critical vulnerabilities.
        
        Args:
            target: Target contract or project path
            
        Returns:
            Rich Panel with quick scan results
        """
        
        if not self._validate_target(target):
            return Panel(f"[red]❌ Invalid target: {target}[/red]", title="Error")
        
        start_time = time.time()
        
        try:
            # Quick scan configuration
            quick_config = {
                'target': target,
                'mode': 'quick',
                'slither_timeout': 60,
                'mythril_timeout': 120,
                'skip_fuzzing': True,
                'focus_critical': True
            }
            
            self.console.print("[yellow]⚡ Running quick security scan...[/yellow]")
            
            # Run static analysis only for quick scan
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                
                task = progress.add_task("Scanning for critical vulnerabilities...", total=None)
                
                # Run static analysis
                static_results = await self.static_engine.analyze_contracts(target, quick_config)
                
                # Filter for critical and high severity only
                critical_findings = [
                    f for f in static_results.get('findings', [])
                    if f.get('severity') in ['Critical', 'High']
                ]
                
                progress.update(task, description="✅ Quick scan complete")
            
            execution_time = time.time() - start_time
            
            # Create quick scan report
            return self._create_quick_scan_panel(critical_findings, execution_time)
            
        except Exception as e:
            self.logger.error(f"Quick scan failed: {e}")
            return Panel(
                f"[red]❌ Quick scan failed: {e}[/red]",
                title="[red]Quick Scan Error[/red]",
                border_style="red"
            )
    
    async def _run_comprehensive_analysis(self, target: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run comprehensive analysis using all engines."""
        
        results = {
            'target': target,
            'timestamp': time.time(),
            'engines_used': [],
            'summary': {},
            'findings': [],
            'recommendations': []
        }
        
        # Determine which engines to run
        engines_to_run = []
        
        if not config.get('skip_static', False):
            engines_to_run.append(('static', self.static_engine.analyze_contracts))
        
        if not config.get('skip_advanced', False):
            engines_to_run.append(('advanced', self.advanced_engine.analyze_contract))
        
        if not config.get('skip_fuzzing', False):
            engines_to_run.append(('fuzzing', self.fuzzing_engine.run_comprehensive_fuzzing))
        
        # Run engines in parallel where possible
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            
            # Create progress tasks
            task_ids = {}
            for engine_name, _ in engines_to_run:
                task_ids[engine_name] = progress.add_task(
                    f"Running {engine_name} analysis...", 
                    total=100
                )
            
            # Execute engines
            engine_results = {}
            
            for engine_name, engine_func in engines_to_run:
                try:
                    progress.update(task_ids[engine_name], advance=10)
                    
                    engine_result = await engine_func(target, config)
                    engine_results[engine_name] = engine_result
                    results['engines_used'].append(engine_name)
                    
                    progress.update(task_ids[engine_name], completed=100)
                    self.console.print(f"[green]✅ {engine_name.title()} analysis complete[/green]")
                    
                except Exception as e:
                    self.logger.error(f"Error in {engine_name} engine: {e}")
                    progress.update(task_ids[engine_name], completed=100)
                    self.console.print(f"[red]❌ {engine_name.title()} analysis failed: {e}[/red]")
        
        # Consolidate results
        await self._consolidate_engine_results(results, engine_results)
        
        # Run multi-agent enhancement if LLM is available
        if not config.get('skip_ai_enhancement', False):
            await self._enhance_with_multi_agent_system(results, config)
        
        return results
    
    async def _consolidate_engine_results(self, results: Dict[str, Any], engine_results: Dict[str, Any]):
        """Consolidate results from all engines."""
        
        all_findings = []
        total_execution_time = 0
        
        # Process static analysis results
        if 'static' in engine_results:
            static_data = engine_results['static']
            all_findings.extend(static_data.get('findings', []))
            results['static_analysis'] = static_data
        
        # Process advanced security results
        if 'advanced' in engine_results:
            advanced_data = engine_results['advanced']
            all_findings.extend(advanced_data.get('findings', []))
            results['advanced_security'] = advanced_data
        
        # Process fuzzing results
        if 'fuzzing' in engine_results:
            fuzzing_data = engine_results['fuzzing']
            results['fuzzing'] = fuzzing_data
            
            # Convert fuzzing failures to findings format
            for tool_result in fuzzing_data.get('tool_results', []):
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
                    all_findings.append(finding)
        
        # Remove duplicates and sort findings
        unique_findings = self._deduplicate_findings(all_findings)
        results['findings'] = unique_findings
        
        # Calculate summary statistics
        results['summary'] = self._calculate_summary_statistics(results, engine_results)
    
    async def _enhance_with_multi_agent_system(self, results: Dict[str, Any], config: Dict[str, Any]):
        """Enhance results using multi-agent system."""
        
        try:
            self.console.print("[yellow]🤖 Enhancing analysis with AI agents...[/yellow]")
            
            # Run multi-agent analysis
            agent_results = await self.agent_orchestrator.analyze_findings(
                results['findings'], 
                results.get('target', ''),
                config
            )
            
            # Integrate agent results
            results['agent_analysis'] = agent_results
            
            # Enhance findings with agent insights
            for finding in results['findings']:
                finding_id = finding.get('id', '')
                
                # Add exploit scenarios
                if finding_id in agent_results.get('exploit_scenarios', {}):
                    finding['exploit_scenario'] = agent_results['exploit_scenarios'][finding_id]
                
                # Add remediation suggestions
                if finding_id in agent_results.get('remediation_suggestions', {}):
                    finding['remediation'] = agent_results['remediation_suggestions'][finding_id]
                
                # Update severity if AI suggests different assessment
                if finding_id in agent_results.get('severity_assessments', {}):
                    ai_severity = agent_results['severity_assessments'][finding_id]
                    if ai_severity.get('confidence', 0) > 0.8:
                        finding['ai_severity'] = ai_severity['severity']
                        finding['ai_confidence'] = ai_severity['confidence']
            
            # Add overall recommendations
            results['recommendations'].extend(agent_results.get('recommendations', []))
            
            self.console.print("[green]✅ AI enhancement complete[/green]")
            
        except Exception as e:
            self.logger.error(f"AI enhancement failed: {e}")
            self.console.print(f"[yellow]⚠️ AI enhancement failed: {e}[/yellow]")
    
    def _deduplicate_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate findings based on similarity."""
        
        unique_findings = []
        
        for finding in findings:
            is_duplicate = False
            
            for existing in unique_findings:
                # Check for duplicates based on title, severity, and location
                if (finding.get('title', '') == existing.get('title', '') and
                    finding.get('severity', '') == existing.get('severity', '') and
                    finding.get('line_number') == existing.get('line_number') and
                    finding.get('file_path', '') == existing.get('file_path', '')):
                    
                    # Merge tools information
                    existing_tools = existing.get('tools', [])
                    if isinstance(existing_tools, str):
                        existing_tools = [existing_tools]
                    
                    new_tool = finding.get('tool', '')
                    if new_tool and new_tool not in existing_tools:
                        existing_tools.append(new_tool)
                        existing['tools'] = existing_tools
                    
                    # Use higher confidence
                    if finding.get('confidence', 0) > existing.get('confidence', 0):
                        existing['confidence'] = finding.get('confidence', 0)
                    
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                # Ensure tools is a list
                if 'tool' in finding:
                    finding['tools'] = [finding['tool']]
                unique_findings.append(finding)
        
        # Sort by severity and confidence
        severity_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3, 'Info': 4}
        
        unique_findings.sort(key=lambda f: (
            severity_order.get(f.get('severity', 'Medium'), 5),
            -f.get('confidence', 0)
        ))
        
        return unique_findings
    
    def _calculate_summary_statistics(self, results: Dict[str, Any], engine_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive summary statistics."""
        
        findings = results.get('findings', [])
        
        # Severity distribution
        severity_counts = {}
        for finding in findings:
            severity = finding.get('severity', 'Unknown')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Tool distribution
        tool_counts = {}
        for finding in findings:
            tools = finding.get('tools', [])
            if isinstance(tools, str):
                tools = [tools]
            for tool in tools:
                tool_counts[tool] = tool_counts.get(tool, 0) + 1
        
        # Category distribution
        category_counts = {}
        for finding in findings:
            category = finding.get('category', 'Unknown')
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Calculate risk score
        risk_score = self._calculate_overall_risk_score(findings)
        
        # Get fuzzing statistics
        fuzzing_stats = {}
        if 'fuzzing' in engine_results:
            fuzzing_data = engine_results['fuzzing']
            fuzzing_summary = fuzzing_data.get('summary', {})
            fuzzing_stats = {
                'properties_tested': fuzzing_summary.get('total_properties_tested', 0),
                'properties_failed': fuzzing_summary.get('total_properties_failed', 0),
                'success_rate': fuzzing_summary.get('success_rate', 100),
                'coverage': fuzzing_summary.get('average_coverage', 0)
            }
        
        # Get static analysis statistics
        static_stats = {}
        if 'static' in engine_results:
            static_data = engine_results['static']
            static_summary = static_data.get('summary', {})
            static_stats = {
                'quality_score': static_summary.get('quality_score', 100),
                'quality_grade': static_summary.get('quality_grade', 'A'),
                'lines_of_code': static_data.get('metrics', {}).get('total_lines_of_code', 0)
            }
        
        return {
            'total_findings': len(findings),
            'severity_distribution': severity_counts,
            'tool_distribution': tool_counts,
            'category_distribution': category_counts,
            'risk_score': risk_score,
            'risk_level': self._get_risk_level(risk_score),
            'fuzzing_statistics': fuzzing_stats,
            'static_analysis_statistics': static_stats,
            'engines_used': results.get('engines_used', [])
        }
    
    def _calculate_overall_risk_score(self, findings: List[Dict[str, Any]]) -> int:
        """Calculate overall risk score (0-100)."""
        
        if not findings:
            return 0
        
        severity_weights = {
            'Critical': 25,
            'High': 15,
            'Medium': 8,
            'Low': 3,
            'Info': 1
        }
        
        total_score = 0
        for finding in findings:
            weight = severity_weights.get(finding.get('severity', 'Medium'), 5)
            confidence = finding.get('confidence', 0.7)
            total_score += weight * confidence
        
        # Normalize to 0-100 scale
        max_possible = len(findings) * 25  # All critical with 100% confidence
        normalized_score = min(100, int((total_score / max_possible) * 100)) if max_possible > 0 else 0
        
        return normalized_score
    
    def _get_risk_level(self, risk_score: int) -> str:
        """Get risk level based on score."""
        
        if risk_score >= 80:
            return 'CRITICAL'
        elif risk_score >= 60:
            return 'HIGH'
        elif risk_score >= 40:
            return 'MEDIUM'
        elif risk_score >= 20:
            return 'LOW'
        else:
            return 'MINIMAL'
    
    def _create_comprehensive_report_panel(self, results: Dict[str, Any], execution_time: float) -> Panel:
        """Create comprehensive audit report panel."""
        
        summary = results.get('summary', {})
        findings = results.get('findings', [])
        
        # Create title with risk level
        risk_level = summary.get('risk_level', 'UNKNOWN')
        risk_colors = {
            'CRITICAL': 'red',
            'HIGH': 'red',
            'MEDIUM': 'yellow',
            'LOW': 'green',
            'MINIMAL': 'green'
        }
        risk_color = risk_colors.get(risk_level, 'white')
        
        title = f"[bold {risk_color}]🛡️ Web3 Security Audit Report - {risk_level} RISK[/bold {risk_color}]"
        
        # Create summary table
        summary_table = Table(title="📊 Audit Summary")
        summary_table.add_column("Metric", style="cyan", width=20)
        summary_table.add_column("Value", justify="center", width=10)
        summary_table.add_column("Status", justify="center", width=10)
        
        # Add summary rows
        total_findings = summary.get('total_findings', 0)
        severity_dist = summary.get('severity_distribution', {})
        
        summary_table.add_row("Total Findings", str(total_findings), "📋")
        summary_table.add_row("Critical", str(severity_dist.get('Critical', 0)), "🔴" if severity_dist.get('Critical', 0) > 0 else "✅")
        summary_table.add_row("High", str(severity_dist.get('High', 0)), "🟡" if severity_dist.get('High', 0) > 0 else "✅")
        summary_table.add_row("Medium", str(severity_dist.get('Medium', 0)), "🟠" if severity_dist.get('Medium', 0) > 0 else "✅")
        summary_table.add_row("Low", str(severity_dist.get('Low', 0)), "🟢")
        summary_table.add_row("Risk Score", str(summary.get('risk_score', 0)), risk_level)
        summary_table.add_row("Execution Time", f"{execution_time:.1f}s", "⏱️")
        
        # Create findings table (top 10)
        findings_table = Table(title="🔍 Top Security Findings")
        findings_table.add_column("Severity", width=10)
        findings_table.add_column("Tool", width=12)
        findings_table.add_column("Finding", width=40)
        findings_table.add_column("Confidence", justify="center", width=12)
        
        # Add top findings
        for finding in findings[:10]:
            severity = finding.get('severity', 'Unknown')
            tools = finding.get('tools', [])
            if isinstance(tools, list):
                tool_str = ', '.join(tools[:2])  # Show first 2 tools
            else:
                tool_str = str(tools)
            
            title = finding.get('title', 'Unknown')
            if len(title) > 35:
                title = title[:32] + "..."
            
            confidence = finding.get('confidence', 0)
            confidence_str = f"{confidence:.2f}" if isinstance(confidence, (int, float)) else str(confidence)
            
            findings_table.add_row(severity, tool_str, title, confidence_str)
        
        # Create engines status table
        engines_table = Table(title="🔧 Analysis Engines")
        engines_table.add_column("Engine", style="cyan")
        engines_table.add_column("Status", justify="center")
        engines_table.add_column("Findings", justify="center")
        
        engines_used = summary.get('engines_used', [])
        
        engines_table.add_row("Static Analysis", "✅" if 'static' in engines_used else "⏭️", 
                             str(len([f for f in findings if 'slither' in f.get('tools', []) or 'securify2' in f.get('tools', [])])))
        engines_table.add_row("Advanced Security", "✅" if 'advanced' in engines_used else "⏭️",
                             str(len([f for f in findings if 'mythril' in f.get('tools', []) or 'custom' in f.get('tools', [])])))
        engines_table.add_row("Fuzzing", "✅" if 'fuzzing' in engines_used else "⏭️",
                             str(len([f for f in findings if f.get('category') == 'fuzzing'])))
        
        # Create recommendations
        recommendations = results.get('recommendations', [])
        if not recommendations:
            if total_findings == 0:
                recommendations = ["✅ No security issues detected!", "🎯 Consider adding more comprehensive tests."]
            else:
                recommendations = ["🔍 Review all findings carefully", "🛠️ Implement recommended fixes"]
        
        recommendations_text = "\n".join([f"• {rec}" for rec in recommendations[:5]])
        
        # Combine all sections
        content = f"""
{summary_table}

{findings_table}

{engines_table}

[bold]🎯 Key Recommendations:[/bold]
{recommendations_text}

[dim]Analysis completed with {len(engines_used)} engines in {execution_time:.1f} seconds[/dim]
        """
        
        return Panel(
            content,
            title=title,
            border_style=risk_color,
            padding=(1, 2)
        )
    
    def _create_quick_scan_panel(self, findings: List[Dict[str, Any]], execution_time: float) -> Panel:
        """Create quick scan report panel."""
        
        critical_count = len([f for f in findings if f.get('severity') == 'Critical'])
        high_count = len([f for f in findings if f.get('severity') == 'High'])
        
        if critical_count > 0:
            title = "[bold red]⚡ Quick Scan - CRITICAL ISSUES FOUND[/bold red]"
            border_style = "red"
        elif high_count > 0:
            title = "[bold yellow]⚡ Quick Scan - HIGH SEVERITY ISSUES[/bold yellow]"
            border_style = "yellow"
        else:
            title = "[bold green]⚡ Quick Scan - NO CRITICAL ISSUES[/bold green]"
            border_style = "green"
        
        if not findings:
            content = """
[green]✅ No critical or high severity vulnerabilities detected in quick scan![/green]

[bold]Next Steps:[/bold]
• Run full comprehensive audit for complete analysis
• Consider adding property-based testing
• Review code for best practices
            """
        else:
            # Create findings table
            findings_table = Table()
            findings_table.add_column("Severity", width=10)
            findings_table.add_column("Finding", width=50)
            findings_table.add_column("Tool", width=15)
            
            for finding in findings[:10]:  # Show top 10
                severity = finding.get('severity', 'Unknown')
                title = finding.get('title', 'Unknown')
                if len(title) > 45:
                    title = title[:42] + "..."
                tool = finding.get('tool', 'Unknown')
                
                findings_table.add_row(severity, title, tool)
            
            content = f"""
[bold red]🚨 {critical_count} Critical and {high_count} High severity issues found![/bold red]

{findings_table}

[bold]Immediate Actions Required:[/bold]
• Address critical vulnerabilities immediately
• Review high severity issues
• Run comprehensive audit for full analysis
            """
        
        content += f"\n\n[dim]Quick scan completed in {execution_time:.1f} seconds[/dim]"
        
        return Panel(
            content,
            title=title,
            border_style=border_style,
            padding=(1, 2)
        )
    
    def _validate_target(self, target: str) -> bool:
        """Validate audit target."""
        
        # Check if it's a URL
        if target.startswith(('http://', 'https://')):
            return True
        
        # Check if it's a file or directory
        if os.path.exists(target):
            return True
        
        # Check if it looks like a relative path
        if '/' in target or '\\' in target:
            return False
        
        return False
    
    async def get_tool_status(self) -> Dict[str, bool]:
        """Get status of all analysis tools."""
        
        return {
            'slither': self.static_engine.tools_available.get('slither', False),
            'mythril': self.advanced_engine.tools_available.get('mythril', False),
            'securify2': self.advanced_engine.tools_available.get('securify2', False),
            'echidna': self.fuzzing_engine.tools_available.get('echidna', False),
            'medusa': self.fuzzing_engine.tools_available.get('medusa', False),
            'foundry': self.fuzzing_engine.tools_available.get('foundry', False),
            'fuzz_utils': self.fuzzing_engine.tools_available.get('fuzz_utils', False),
            'solhint': self.static_engine.tools_available.get('solhint', False)
        }
    
    def get_analysis_history(self) -> List[Dict[str, Any]]:
        """Get analysis history."""
        return self.analysis_history[-10:]  # Return last 10 analyses
    
    def export_results(self, format_type: str = 'json') -> str:
        """Export analysis results in specified format."""
        
        if not self.current_analysis:
            return "No analysis results available"
        
        results = self.current_analysis.get('results', {})
        
        if format_type.lower() == 'json':
            return json.dumps(results, indent=2, default=str)
        elif format_type.lower() == 'markdown':
            return self._generate_markdown_report(results)
        else:
            return "Unsupported format"
    
    def _generate_markdown_report(self, results: Dict[str, Any]) -> str:
        """Generate markdown report."""
        
        summary = results.get('summary', {})
        findings = results.get('findings', [])
        
        report = f"""# Web3 Security Audit Report
        
## Summary
- **Total Findings**: {summary.get('total_findings', 0)}
- **Risk Level**: {summary.get('risk_level', 'Unknown')}
- **Risk Score**: {summary.get('risk_score', 0)}/100

## Severity Distribution
"""
        
        severity_dist = summary.get('severity_distribution', {})
        for severity, count in severity_dist.items():
            report += f"- **{severity}**: {count}\n"
        
        report += "\n## Findings\n\n"
        
        for i, finding in enumerate(findings, 1):
            report += f"### {i}. {finding.get('title', 'Unknown')}\n"
            report += f"- **Severity**: {finding.get('severity', 'Unknown')}\n"
            report += f"- **Tool**: {', '.join(finding.get('tools', []))}\n"
            report += f"- **Description**: {finding.get('description', 'No description')}\n"
            
            if finding.get('remediation'):
                report += f"- **Remediation**: {finding.get('remediation')}\n"
            
            report += "\n"
        
        return report
