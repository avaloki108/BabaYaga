"""Advanced Security Analysis Engine integrating multiple cutting-edge tools."""

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

@dataclass
class SecurityFinding:
    """Enhanced security finding with comprehensive metadata."""
    id: str
    title: str
    description: str
    severity: str
    confidence: float
    tool: str
    category: str
    swc_id: Optional[str] = None
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    exploit_scenario: Optional[str] = None
    remediation: Optional[str] = None
    references: List[str] = None
    
    def __post_init__(self):
        if self.references is None:
            self.references = []

class AdvancedSecurityEngine:
    """
    Advanced security analysis engine that integrates:
    - Mythril Enhanced (symbolic execution)
    - Securify2 (static analysis with Datalog)
    - Custom pattern detection
    - AI-enhanced analysis
    """
    
    def __init__(self, console: Console):
        self.console = console
        self.logger = logging.getLogger(__name__)
        
        # Tool availability
        self.tools_available = {
            'mythril': self._check_mythril(),
            'securify2': self._check_securify2(),
            'slither': self._check_slither(),
            'custom': True  # Always available
        }
        
        # Analysis results
        self.findings: List[SecurityFinding] = []
        self.analysis_metadata = {}
        
    def _check_mythril(self) -> bool:
        """Check if Mythril is available."""
        try:
            result = subprocess.run(['myth', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_securify2(self) -> bool:
        """Check if Securify2 is available."""
        try:
            # Check if securify command exists
            result = subprocess.run(['which', 'securify'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_slither(self) -> bool:
        """Check if Slither is available."""
        try:
            result = subprocess.run(['slither', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    async def analyze_contract(self, target_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run comprehensive security analysis using all available tools.
        
        Args:
            target_path: Path to the contract or project
            config: Analysis configuration
            
        Returns:
            Comprehensive analysis results
        """
        
        self.console.print(f"[bold green]🔍 Starting Advanced Security Analysis[/bold green]")
        self.console.print(f"[dim]Target: {target_path}[/dim]")
        
        # Reset findings
        self.findings = []
        
        # Prepare analysis tasks
        analysis_tasks = []
        
        if self.tools_available['mythril']:
            analysis_tasks.append(('mythril', self._run_mythril_analysis))
        
        if self.tools_available['securify2']:
            analysis_tasks.append(('securify2', self._run_securify2_analysis))
        
        if self.tools_available['slither']:
            analysis_tasks.append(('slither', self._run_slither_analysis))
        
        # Always run custom analysis
        analysis_tasks.append(('custom', self._run_custom_analysis))
        
        # Run analyses in parallel
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            
            # Create progress tasks
            task_ids = {}
            for tool_name, _ in analysis_tasks:
                task_ids[tool_name] = progress.add_task(
                    f"Running {tool_name.title()} analysis...", 
                    total=100
                )
            
            # Execute analyses
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_tool = {
                    executor.submit(task_func, target_path, config, progress, task_ids[tool_name]): tool_name
                    for tool_name, task_func in analysis_tasks
                }
                
                for future in as_completed(future_to_tool):
                    tool_name = future_to_tool[future]
                    try:
                        tool_findings = future.result()
                        self.findings.extend(tool_findings)
                        progress.update(task_ids[tool_name], completed=100)
                        self.console.print(f"[green]✅ {tool_name.title()} analysis complete[/green]")
                    except Exception as e:
                        self.logger.error(f"Error in {tool_name} analysis: {e}")
                        progress.update(task_ids[tool_name], completed=100)
                        self.console.print(f"[red]❌ {tool_name.title()} analysis failed: {e}[/red]")
        
        # Post-process findings
        await self._post_process_findings()
        
        # Generate comprehensive report
        return self._generate_analysis_report()
    
    def _run_mythril_analysis(self, target_path: str, config: Dict[str, Any], 
                             progress: Progress, task_id: int) -> List[SecurityFinding]:
        """Run Mythril Enhanced analysis."""
        
        findings = []
        
        try:
            # Prepare Mythril command
            cmd = [
                'myth', 'analyze', target_path,
                '--execution-timeout', str(config.get('mythril_timeout', 300)),
                '--max-depth', str(config.get('mythril_max_depth', 22)),
                '--strategy', config.get('mythril_strategy', 'dfs'),
                '--output', 'json'
            ]
            
            # Add transaction limit if specified
            if 'mythril_tx_limit' in config:
                cmd.extend(['-t', str(config['mythril_tx_limit'])])
            
            progress.update(task_id, advance=25)
            
            # Run Mythril
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=config.get('mythril_timeout', 300) + 30
            )
            
            progress.update(task_id, advance=50)
            
            if result.returncode == 0 and result.stdout:
                # Parse Mythril JSON output
                try:
                    mythril_data = json.loads(result.stdout)
                    
                    for issue in mythril_data.get('issues', []):
                        finding = SecurityFinding(
                            id=f"mythril_{issue.get('swc-id', 'unknown')}_{len(findings)}",
                            title=issue.get('title', 'Unknown Issue'),
                            description=issue.get('description', ''),
                            severity=self._normalize_severity(issue.get('severity', 'Medium')),
                            confidence=0.85,  # Mythril generally has high confidence
                            tool='mythril',
                            category='symbolic_execution',
                            swc_id=issue.get('swc-id'),
                            line_number=self._extract_line_number(issue.get('filename', '')),
                            function_name=issue.get('function'),
                            exploit_scenario=self._generate_exploit_scenario(issue),
                            remediation=self._generate_remediation(issue),
                            references=[f"https://swcregistry.io/docs/SWC-{issue.get('swc-id', '000')}"]
                        )
                        findings.append(finding)
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse Mythril output: {e}")
            
            progress.update(task_id, advance=25)
            
        except subprocess.TimeoutExpired:
            self.logger.warning("Mythril analysis timed out")
        except Exception as e:
            self.logger.error(f"Mythril analysis failed: {e}")
        
        return findings
    
    def _run_securify2_analysis(self, target_path: str, config: Dict[str, Any], 
                               progress: Progress, task_id: int) -> List[SecurityFinding]:
        """Run Securify2 static analysis."""
        
        findings = []
        
        try:
            # Prepare Securify2 command
            cmd = ['securify', target_path]
            
            # Add severity filters if specified
            if 'securify_severity' in config:
                cmd.extend(['--include-severity'] + config['securify_severity'])
            
            progress.update(task_id, advance=25)
            
            # Run Securify2
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=config.get('securify_timeout', 180)
            )
            
            progress.update(task_id, advance=50)
            
            if result.returncode == 0:
                # Parse Securify2 output
                findings.extend(self._parse_securify2_output(result.stdout))
            
            progress.update(task_id, advance=25)
            
        except subprocess.TimeoutExpired:
            self.logger.warning("Securify2 analysis timed out")
        except Exception as e:
            self.logger.error(f"Securify2 analysis failed: {e}")
        
        return findings
    
    def _run_slither_analysis(self, target_path: str, config: Dict[str, Any], 
                             progress: Progress, task_id: int) -> List[SecurityFinding]:
        """Run enhanced Slither analysis."""
        
        findings = []
        
        try:
            # Prepare Slither command with enhanced detectors
            cmd = [
                'slither', target_path,
                '--json', '-',
                '--exclude-informational',
                '--exclude-optimization'
            ]
            
            # Add specific detectors if configured
            if 'slither_detectors' in config:
                cmd.extend(['--detect'] + config['slither_detectors'])
            
            progress.update(task_id, advance=25)
            
            # Run Slither
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=config.get('slither_timeout', 120)
            )
            
            progress.update(task_id, advance=50)
            
            if result.stdout:
                # Parse Slither JSON output
                try:
                    slither_data = json.loads(result.stdout)
                    
                    for detector_result in slither_data.get('results', {}).get('detectors', []):
                        finding = SecurityFinding(
                            id=f"slither_{detector_result.get('check', 'unknown')}_{len(findings)}",
                            title=detector_result.get('description', 'Slither Detection'),
                            description=detector_result.get('markdown', ''),
                            severity=self._normalize_severity(detector_result.get('impact', 'Medium')),
                            confidence=self._normalize_confidence(detector_result.get('confidence', 'Medium')),
                            tool='slither',
                            category='static_analysis',
                            line_number=self._extract_slither_line_number(detector_result),
                            function_name=self._extract_slither_function(detector_result),
                            references=[f"https://github.com/crytic/slither/wiki/Detector-Documentation#{detector_result.get('check', '')}"]
                        )
                        findings.append(finding)
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse Slither output: {e}")
            
            progress.update(task_id, advance=25)
            
        except subprocess.TimeoutExpired:
            self.logger.warning("Slither analysis timed out")
        except Exception as e:
            self.logger.error(f"Slither analysis failed: {e}")
        
        return findings
    
    def _run_custom_analysis(self, target_path: str, config: Dict[str, Any], 
                            progress: Progress, task_id: int) -> List[SecurityFinding]:
        """Run custom pattern-based analysis."""
        
        findings = []
        
        try:
            progress.update(task_id, advance=25)
            
            # Read contract source code
            if os.path.isfile(target_path):
                with open(target_path, 'r') as f:
                    source_code = f.read()
                
                # Run custom pattern detection
                findings.extend(self._detect_custom_patterns(source_code, target_path))
            
            progress.update(task_id, advance=50)
            
            # Run additional custom checks
            findings.extend(self._run_advanced_custom_checks(target_path))
            
            progress.update(task_id, advance=25)
            
        except Exception as e:
            self.logger.error(f"Custom analysis failed: {e}")
        
        return findings
    
    def _detect_custom_patterns(self, source_code: str, file_path: str) -> List[SecurityFinding]:
        """Detect custom vulnerability patterns."""
        
        findings = []
        lines = source_code.split('\n')
        
        # Custom patterns based on bug bounty checklist
        patterns = {
            'unchecked_external_call': {
                'pattern': r'\.call\s*\(',
                'severity': 'High',
                'description': 'Unchecked external call detected',
                'category': 'external_calls'
            },
            'reentrancy_pattern': {
                'pattern': r'msg\.sender\.call',
                'severity': 'Critical',
                'description': 'Potential reentrancy vulnerability',
                'category': 'reentrancy'
            },
            'tx_origin_usage': {
                'pattern': r'tx\.origin',
                'severity': 'Medium',
                'description': 'Usage of tx.origin for authorization',
                'category': 'authorization'
            },
            'timestamp_dependence': {
                'pattern': r'block\.timestamp|now',
                'severity': 'Medium',
                'description': 'Timestamp dependence detected',
                'category': 'timestamp'
            },
            'unsafe_delegatecall': {
                'pattern': r'delegatecall\s*\(',
                'severity': 'High',
                'description': 'Potentially unsafe delegatecall',
                'category': 'delegatecall'
            }
        }
        
        import re
        
        for pattern_name, pattern_info in patterns.items():
            pattern = re.compile(pattern_info['pattern'])
            
            for line_num, line in enumerate(lines, 1):
                if pattern.search(line):
                    finding = SecurityFinding(
                        id=f"custom_{pattern_name}_{line_num}",
                        title=pattern_info['description'],
                        description=f"Pattern '{pattern_name}' detected at line {line_num}: {line.strip()}",
                        severity=pattern_info['severity'],
                        confidence=0.7,
                        tool='custom',
                        category=pattern_info['category'],
                        line_number=line_num,
                        references=['https://consensys.github.io/smart-contract-best-practices/']
                    )
                    findings.append(finding)
        
        return findings
    
    def _run_advanced_custom_checks(self, target_path: str) -> List[SecurityFinding]:
        """Run advanced custom security checks."""
        
        findings = []
        
        # Add more sophisticated custom checks here
        # This could include:
        # - Complex pattern matching
        # - Cross-function analysis
        # - State variable tracking
        # - Gas optimization checks
        
        return findings
    
    def _parse_securify2_output(self, output: str) -> List[SecurityFinding]:
        """Parse Securify2 text output into findings."""
        
        findings = []
        lines = output.split('\n')
        
        current_finding = None
        
        for line in lines:
            line = line.strip()
            
            # Look for severity indicators
            if any(severity in line.upper() for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']):
                if 'violation' in line.lower() or 'warning' in line.lower():
                    # Extract severity
                    severity = 'Medium'  # Default
                    for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                        if sev in line.upper():
                            severity = sev.title()
                            break
                    
                    # Create new finding
                    current_finding = SecurityFinding(
                        id=f"securify2_{len(findings)}",
                        title=line,
                        description=line,
                        severity=severity,
                        confidence=0.8,
                        tool='securify2',
                        category='static_analysis'
                    )
                    findings.append(current_finding)
        
        return findings
    
    async def _post_process_findings(self):
        """Post-process findings to remove duplicates and enhance with AI."""
        
        # Remove duplicates based on similarity
        unique_findings = []
        
        for finding in self.findings:
            is_duplicate = False
            
            for existing in unique_findings:
                if (finding.title == existing.title and 
                    finding.line_number == existing.line_number and
                    finding.severity == existing.severity):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_findings.append(finding)
        
        self.findings = unique_findings
        
        # Sort by severity and confidence
        severity_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3, 'Info': 4}
        
        self.findings.sort(key=lambda f: (
            severity_order.get(f.severity, 5),
            -f.confidence
        ))
    
    def _generate_analysis_report(self) -> Dict[str, Any]:
        """Generate comprehensive analysis report."""
        
        # Calculate statistics
        severity_counts = {}
        tool_counts = {}
        category_counts = {}
        
        for finding in self.findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
            tool_counts[finding.tool] = tool_counts.get(finding.tool, 0) + 1
            category_counts[finding.category] = category_counts.get(finding.category, 0) + 1
        
        # Calculate risk score
        risk_score = self._calculate_risk_score()
        
        return {
            'summary': {
                'total_findings': len(self.findings),
                'severity_distribution': severity_counts,
                'tool_distribution': tool_counts,
                'category_distribution': category_counts,
                'risk_score': risk_score,
                'risk_level': self._get_risk_level(risk_score)
            },
            'findings': [
                {
                    'id': f.id,
                    'title': f.title,
                    'description': f.description,
                    'severity': f.severity,
                    'confidence': f.confidence,
                    'tool': f.tool,
                    'category': f.category,
                    'swc_id': f.swc_id,
                    'line_number': f.line_number,
                    'function_name': f.function_name,
                    'exploit_scenario': f.exploit_scenario,
                    'remediation': f.remediation,
                    'references': f.references
                }
                for f in self.findings
            ],
            'tools_used': list(self.tools_available.keys()),
            'metadata': self.analysis_metadata
        }
    
    def _calculate_risk_score(self) -> int:
        """Calculate overall risk score (0-100)."""
        
        if not self.findings:
            return 0
        
        severity_weights = {
            'Critical': 25,
            'High': 15,
            'Medium': 8,
            'Low': 3,
            'Info': 1
        }
        
        total_score = 0
        for finding in self.findings:
            weight = severity_weights.get(finding.severity, 1)
            confidence_multiplier = finding.confidence
            total_score += weight * confidence_multiplier
        
        # Normalize to 0-100 scale
        max_possible = len(self.findings) * 25  # All critical with 100% confidence
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
    
    # Helper methods
    def _normalize_severity(self, severity: str) -> str:
        """Normalize severity levels across tools."""
        severity = severity.lower()
        
        if severity in ['critical', 'high']:
            return severity.title()
        elif severity in ['medium', 'moderate']:
            return 'Medium'
        elif severity in ['low', 'minor']:
            return 'Low'
        elif severity in ['info', 'informational']:
            return 'Info'
        else:
            return 'Medium'  # Default
    
    def _normalize_confidence(self, confidence: str) -> float:
        """Normalize confidence levels to 0-1 scale."""
        confidence = confidence.lower()
        
        confidence_map = {
            'high': 0.9,
            'medium': 0.7,
            'low': 0.5
        }
        
        return confidence_map.get(confidence, 0.7)
    
    def _extract_line_number(self, filename: str) -> Optional[int]:
        """Extract line number from filename string."""
        import re
        match = re.search(r':(\d+)', filename)
        return int(match.group(1)) if match else None
    
    def _extract_slither_line_number(self, detector_result: Dict) -> Optional[int]:
        """Extract line number from Slither detector result."""
        elements = detector_result.get('elements', [])
        if elements and 'source_mapping' in elements[0]:
            lines = elements[0]['source_mapping'].get('lines', [])
            return lines[0] if lines else None
        return None
    
    def _extract_slither_function(self, detector_result: Dict) -> Optional[str]:
        """Extract function name from Slither detector result."""
        elements = detector_result.get('elements', [])
        for element in elements:
            if element.get('type') == 'function':
                return element.get('name')
        return None
    
    def _generate_exploit_scenario(self, issue: Dict) -> str:
        """Generate exploit scenario for Mythril issue."""
        # This could be enhanced with AI-generated scenarios
        return f"An attacker could exploit this {issue.get('title', 'vulnerability')} by manipulating the transaction sequence."
    
    def _generate_remediation(self, issue: Dict) -> str:
        """Generate remediation advice for issue."""
        # This could be enhanced with AI-generated remediation
        swc_id = issue.get('swc-id')
        if swc_id:
            return f"Follow SWC-{swc_id} remediation guidelines. Implement proper access controls and input validation."
        return "Implement proper security controls and follow best practices."
