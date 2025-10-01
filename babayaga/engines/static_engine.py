"""Static Analysis Engine integrating multiple static analysis tools."""

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
import re

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

@dataclass
class StaticFinding:
    """Static analysis finding with comprehensive metadata."""
    id: str
    title: str
    description: str
    severity: str
    confidence: float
    tool: str
    category: str
    file_path: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    function_name: Optional[str] = None
    swc_id: Optional[str] = None
    cwe_id: Optional[str] = None
    code_snippet: Optional[str] = None
    remediation: Optional[str] = None
    references: List[str] = None
    
    def __post_init__(self):
        if self.references is None:
            self.references = []

class StaticAnalysisEngine:
    """
    Static analysis engine that integrates:
    - Slither (comprehensive static analysis)
    - Securify2 (Datalog-based analysis)
    - Custom pattern detection
    - Code quality analysis
    """
    
    def __init__(self, console: Console):
        self.console = console
        self.logger = logging.getLogger(__name__)
        
        # Tool availability
        self.tools_available = {
            'slither': self._check_slither(),
            'securify2': self._check_securify2(),
            'solhint': self._check_solhint(),
            'custom': True  # Always available
        }
        
        # Analysis results
        self.findings: List[StaticFinding] = []
        self.metrics = {}
        
    def _check_slither(self) -> bool:
        """Check if Slither is available."""
        try:
            result = subprocess.run(['slither', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_securify2(self) -> bool:
        """Check if Securify2 is available."""
        try:
            result = subprocess.run(['which', 'securify'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_solhint(self) -> bool:
        """Check if Solhint is available."""
        try:
            result = subprocess.run(['solhint', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    async def analyze_contracts(self, target_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run comprehensive static analysis using all available tools.
        
        Args:
            target_path: Path to the contract or project
            config: Analysis configuration
            
        Returns:
            Comprehensive static analysis results
        """
        
        self.console.print(f"[bold green]📊 Starting Static Analysis[/bold green]")
        self.console.print(f"[dim]Target: {target_path}[/dim]")
        
        # Reset findings
        self.findings = []
        self.metrics = {}
        
        # Prepare analysis tasks
        analysis_tasks = []
        
        if self.tools_available['slither']:
            analysis_tasks.append(('slither', self._run_slither_analysis))
        
        if self.tools_available['securify2']:
            analysis_tasks.append(('securify2', self._run_securify2_analysis))
        
        if self.tools_available['solhint']:
            analysis_tasks.append(('solhint', self._run_solhint_analysis))
        
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
        
        # Calculate code metrics
        await self._calculate_code_metrics(target_path)
        
        # Post-process findings
        await self._post_process_findings()
        
        # Generate comprehensive report
        return self._generate_static_analysis_report()
    
    def _run_slither_analysis(self, target_path: str, config: Dict[str, Any], 
                             progress: Progress, task_id: int) -> List[StaticFinding]:
        """Run comprehensive Slither analysis."""
        
        findings = []
        
        try:
            progress.update(task_id, advance=10)
            
            # Prepare Slither command with comprehensive detectors
            cmd = [
                'slither', target_path,
                '--json', '-',
                '--exclude-dependencies'
            ]
            
            # Add specific detectors if configured
            if 'slither_detectors' in config:
                cmd.extend(['--detect'] + config['slither_detectors'])
            else:
                # Use comprehensive detector set
                cmd.extend(['--detect', 'all'])
            
            # Exclude certain checks if configured
            if 'slither_exclude' in config:
                cmd.extend(['--exclude'] + config['slither_exclude'])
            
            progress.update(task_id, advance=20)
            
            # Run Slither
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=config.get('slither_timeout', 180)
            )
            
            progress.update(task_id, advance=50)
            
            if result.stdout:
                # Parse Slither JSON output
                try:
                    slither_data = json.loads(result.stdout)
                    
                    # Process detector results
                    for detector_result in slither_data.get('results', {}).get('detectors', []):
                        finding = self._create_slither_finding(detector_result)
                        if finding:
                            findings.append(finding)
                    
                    # Process optimization results
                    for optimization in slither_data.get('results', {}).get('optimizations', []):
                        finding = self._create_slither_optimization_finding(optimization)
                        if finding:
                            findings.append(finding)
                            
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse Slither output: {e}")
            
            progress.update(task_id, advance=20)
            
        except subprocess.TimeoutExpired:
            self.logger.warning("Slither analysis timed out")
        except Exception as e:
            self.logger.error(f"Slither analysis failed: {e}")
        
        return findings
    
    def _run_securify2_analysis(self, target_path: str, config: Dict[str, Any], 
                               progress: Progress, task_id: int) -> List[StaticFinding]:
        """Run Securify2 static analysis."""
        
        findings = []
        
        try:
            progress.update(task_id, advance=20)
            
            # Prepare Securify2 command
            cmd = ['securify', target_path]
            
            # Add severity filters if specified
            if 'securify_severity' in config:
                cmd.extend(['--include-severity'] + config['securify_severity'])
            
            progress.update(task_id, advance=20)
            
            # Run Securify2
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=config.get('securify_timeout', 180)
            )
            
            progress.update(task_id, advance=40)
            
            if result.returncode == 0:
                # Parse Securify2 output
                findings.extend(self._parse_securify2_output(result.stdout, target_path))
            
            progress.update(task_id, advance=20)
            
        except subprocess.TimeoutExpired:
            self.logger.warning("Securify2 analysis timed out")
        except Exception as e:
            self.logger.error(f"Securify2 analysis failed: {e}")
        
        return findings
    
    def _run_solhint_analysis(self, target_path: str, config: Dict[str, Any], 
                             progress: Progress, task_id: int) -> List[StaticFinding]:
        """Run Solhint code quality analysis."""
        
        findings = []
        
        try:
            progress.update(task_id, advance=20)
            
            # Prepare Solhint command
            cmd = [
                'solhint', 
                '--formatter', 'json',
                target_path if os.path.isfile(target_path) else f"{target_path}/**/*.sol"
            ]
            
            progress.update(task_id, advance=20)
            
            # Run Solhint
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=config.get('solhint_timeout', 60)
            )
            
            progress.update(task_id, advance=40)
            
            if result.stdout:
                # Parse Solhint JSON output
                try:
                    solhint_data = json.loads(result.stdout)
                    
                    for report in solhint_data:
                        for message in report.get('messages', []):
                            finding = self._create_solhint_finding(message, report.get('filePath', ''))
                            if finding:
                                findings.append(finding)
                                
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse Solhint output: {e}")
            
            progress.update(task_id, advance=20)
            
        except subprocess.TimeoutExpired:
            self.logger.warning("Solhint analysis timed out")
        except Exception as e:
            self.logger.error(f"Solhint analysis failed: {e}")
        
        return findings
    
    def _run_custom_analysis(self, target_path: str, config: Dict[str, Any], 
                            progress: Progress, task_id: int) -> List[StaticFinding]:
        """Run custom static analysis patterns."""
        
        findings = []
        
        try:
            progress.update(task_id, advance=25)
            
            # Analyze all Solidity files
            if os.path.isfile(target_path):
                files_to_analyze = [target_path]
            else:
                files_to_analyze = list(Path(target_path).rglob('*.sol'))
            
            progress.update(task_id, advance=25)
            
            for file_path in files_to_analyze:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source_code = f.read()
                    
                    # Run custom pattern detection
                    file_findings = self._detect_custom_patterns(source_code, str(file_path))
                    findings.extend(file_findings)
                    
                except Exception as e:
                    self.logger.error(f"Failed to analyze {file_path}: {e}")
            
            progress.update(task_id, advance=25)
            
            # Run advanced custom checks
            findings.extend(self._run_advanced_custom_checks(target_path))
            
            progress.update(task_id, advance=25)
            
        except Exception as e:
            self.logger.error(f"Custom analysis failed: {e}")
        
        return findings
    
    def _create_slither_finding(self, detector_result: Dict) -> Optional[StaticFinding]:
        """Create finding from Slither detector result."""
        
        try:
            # Extract basic information
            check = detector_result.get('check', 'unknown')
            description = detector_result.get('description', '')
            impact = detector_result.get('impact', 'Medium')
            confidence = detector_result.get('confidence', 'Medium')
            
            # Extract location information
            elements = detector_result.get('elements', [])
            file_path = ''
            line_number = None
            function_name = None
            
            for element in elements:
                if 'source_mapping' in element:
                    source_mapping = element['source_mapping']
                    if 'filename_absolute' in source_mapping:
                        file_path = source_mapping['filename_absolute']
                    if 'lines' in source_mapping and source_mapping['lines']:
                        line_number = source_mapping['lines'][0]
                
                if element.get('type') == 'function':
                    function_name = element.get('name')
            
            return StaticFinding(
                id=f"slither_{check}_{line_number or 0}",
                title=f"Slither: {check.replace('-', ' ').title()}",
                description=description,
                severity=self._normalize_severity(impact),
                confidence=self._normalize_confidence(confidence),
                tool='slither',
                category='static_analysis',
                file_path=file_path,
                line_number=line_number,
                function_name=function_name,
                references=[f"https://github.com/crytic/slither/wiki/Detector-Documentation#{check}"]
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create Slither finding: {e}")
            return None
    
    def _create_slither_optimization_finding(self, optimization: Dict) -> Optional[StaticFinding]:
        """Create finding from Slither optimization result."""
        
        try:
            return StaticFinding(
                id=f"slither_opt_{optimization.get('check', 'unknown')}",
                title=f"Optimization: {optimization.get('description', 'Unknown')}",
                description=optimization.get('markdown', ''),
                severity='Info',
                confidence=0.8,
                tool='slither',
                category='optimization',
                file_path=optimization.get('elements', [{}])[0].get('source_mapping', {}).get('filename_absolute', ''),
                references=['https://github.com/crytic/slither/wiki/Detector-Documentation']
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create Slither optimization finding: {e}")
            return None
    
    def _create_solhint_finding(self, message: Dict, file_path: str) -> Optional[StaticFinding]:
        """Create finding from Solhint message."""
        
        try:
            return StaticFinding(
                id=f"solhint_{message.get('ruleId', 'unknown')}_{message.get('line', 0)}",
                title=f"Code Quality: {message.get('message', 'Unknown issue')}",
                description=message.get('message', ''),
                severity=self._normalize_solhint_severity(message.get('severity', 1)),
                confidence=0.7,
                tool='solhint',
                category='code_quality',
                file_path=file_path,
                line_number=message.get('line'),
                column_number=message.get('column'),
                references=['https://github.com/protofire/solhint/blob/master/docs/rules.md']
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create Solhint finding: {e}")
            return None
    
    def _parse_securify2_output(self, output: str, target_path: str) -> List[StaticFinding]:
        """Parse Securify2 text output into findings."""
        
        findings = []
        lines = output.split('\n')
        
        current_finding = None
        
        for line in lines:
            line = line.strip()
            
            # Look for severity indicators and violations
            if any(severity in line.upper() for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']):
                if 'violation' in line.lower() or 'warning' in line.lower():
                    # Extract severity
                    severity = 'Medium'  # Default
                    for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                        if sev in line.upper():
                            severity = sev.title()
                            break
                    
                    # Extract pattern name if available
                    pattern_match = re.search(r'(\w+)\s+violation', line, re.IGNORECASE)
                    pattern_name = pattern_match.group(1) if pattern_match else 'Unknown'
                    
                    # Create new finding
                    finding = StaticFinding(
                        id=f"securify2_{pattern_name}_{len(findings)}",
                        title=f"Securify2: {pattern_name} Violation",
                        description=line,
                        severity=severity,
                        confidence=0.8,
                        tool='securify2',
                        category='static_analysis',
                        file_path=target_path,
                        references=['https://github.com/eth-sri/securify2']
                    )
                    findings.append(finding)
        
        return findings
    
    def _detect_custom_patterns(self, source_code: str, file_path: str) -> List[StaticFinding]:
        """Detect custom vulnerability patterns in source code."""
        
        findings = []
        lines = source_code.split('\n')
        
        # Enhanced custom patterns
        patterns = {
            # Security patterns
            'unchecked_external_call': {
                'pattern': r'\.call\s*\([^)]*\)\s*(?!\.require|;|\s*require)',
                'severity': 'High',
                'description': 'Unchecked external call - return value not verified',
                'category': 'external_calls'
            },
            'reentrancy_pattern': {
                'pattern': r'msg\.sender\.call|address\([^)]+\)\.call',
                'severity': 'Critical',
                'description': 'Potential reentrancy vulnerability',
                'category': 'reentrancy'
            },
            'tx_origin_usage': {
                'pattern': r'tx\.origin\s*==|tx\.origin\s*!=',
                'severity': 'Medium',
                'description': 'Usage of tx.origin for authorization is dangerous',
                'category': 'authorization'
            },
            'timestamp_dependence': {
                'pattern': r'block\.timestamp|now\s*[<>=]',
                'severity': 'Medium',
                'description': 'Timestamp dependence detected',
                'category': 'timestamp'
            },
            'unsafe_delegatecall': {
                'pattern': r'delegatecall\s*\(',
                'severity': 'High',
                'description': 'Potentially unsafe delegatecall',
                'category': 'delegatecall'
            },
            'unprotected_selfdestruct': {
                'pattern': r'selfdestruct\s*\(',
                'severity': 'Critical',
                'description': 'Potentially unprotected selfdestruct',
                'category': 'selfdestruct'
            },
            'integer_overflow': {
                'pattern': r'[+\-*/]\s*(?!SafeMath)',
                'severity': 'Medium',
                'description': 'Potential integer overflow without SafeMath',
                'category': 'arithmetic'
            },
            'weak_randomness': {
                'pattern': r'block\.(?:timestamp|difficulty|number|blockhash)',
                'severity': 'Medium',
                'description': 'Weak source of randomness',
                'category': 'randomness'
            },
            'uninitialized_storage': {
                'pattern': r'storage\s+\w+;',
                'severity': 'High',
                'description': 'Uninitialized storage pointer',
                'category': 'storage'
            },
            'deprecated_functions': {
                'pattern': r'\.send\s*\(|\.transfer\s*\(|throw\s*;',
                'severity': 'Medium',
                'description': 'Usage of deprecated functions',
                'category': 'deprecated'
            }
        }
        
        for pattern_name, pattern_info in patterns.items():
            pattern = re.compile(pattern_info['pattern'], re.IGNORECASE)
            
            for line_num, line in enumerate(lines, 1):
                matches = pattern.finditer(line)
                for match in matches:
                    finding = StaticFinding(
                        id=f"custom_{pattern_name}_{line_num}_{match.start()}",
                        title=pattern_info['description'],
                        description=f"Pattern '{pattern_name}' detected at line {line_num}: {line.strip()}",
                        severity=pattern_info['severity'],
                        confidence=0.7,
                        tool='custom',
                        category=pattern_info['category'],
                        file_path=file_path,
                        line_number=line_num,
                        column_number=match.start(),
                        code_snippet=line.strip(),
                        references=['https://consensys.github.io/smart-contract-best-practices/']
                    )
                    findings.append(finding)
        
        return findings
    
    def _run_advanced_custom_checks(self, target_path: str) -> List[StaticFinding]:
        """Run advanced custom security checks."""
        
        findings = []
        
        # Add more sophisticated custom checks here
        # This could include:
        # - Function complexity analysis
        # - State variable analysis
        # - Access control pattern detection
        # - Gas optimization opportunities
        
        return findings
    
    async def _calculate_code_metrics(self, target_path: str):
        """Calculate code quality metrics."""
        
        try:
            total_lines = 0
            total_functions = 0
            total_contracts = 0
            
            if os.path.isfile(target_path):
                files_to_analyze = [target_path]
            else:
                files_to_analyze = list(Path(target_path).rglob('*.sol'))
            
            for file_path in files_to_analyze:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Count lines (excluding empty lines and comments)
                    lines = [line.strip() for line in content.split('\n')]
                    code_lines = [line for line in lines if line and not line.startswith('//')]
                    total_lines += len(code_lines)
                    
                    # Count functions
                    function_matches = re.findall(r'function\s+\w+', content)
                    total_functions += len(function_matches)
                    
                    # Count contracts
                    contract_matches = re.findall(r'contract\s+\w+', content)
                    total_contracts += len(contract_matches)
                    
                except Exception as e:
                    self.logger.error(f"Failed to analyze metrics for {file_path}: {e}")
            
            self.metrics = {
                'total_lines_of_code': total_lines,
                'total_functions': total_functions,
                'total_contracts': total_contracts,
                'average_functions_per_contract': total_functions / total_contracts if total_contracts > 0 else 0,
                'files_analyzed': len(files_to_analyze)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate code metrics: {e}")
    
    async def _post_process_findings(self):
        """Post-process findings to remove duplicates and enhance analysis."""
        
        # Remove duplicates based on similarity
        unique_findings = []
        
        for finding in self.findings:
            is_duplicate = False
            
            for existing in unique_findings:
                if (finding.title == existing.title and 
                    finding.file_path == existing.file_path and
                    finding.line_number == existing.line_number):
                    # Merge information from duplicate
                    if finding.confidence > existing.confidence:
                        existing.confidence = finding.confidence
                    if finding.tool not in existing.references:
                        existing.references.append(f"Also detected by {finding.tool}")
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_findings.append(finding)
        
        self.findings = unique_findings
        
        # Sort by severity and confidence
        severity_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3, 'Info': 4}
        
        self.findings.sort(key=lambda f: (
            severity_order.get(f.severity, 5),
            -f.confidence,
            f.file_path,
            f.line_number or 0
        ))
    
    def _generate_static_analysis_report(self) -> Dict[str, Any]:
        """Generate comprehensive static analysis report."""
        
        # Calculate statistics
        severity_counts = {}
        tool_counts = {}
        category_counts = {}
        file_counts = {}
        
        for finding in self.findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
            tool_counts[finding.tool] = tool_counts.get(finding.tool, 0) + 1
            category_counts[finding.category] = category_counts.get(finding.category, 0) + 1
            
            file_name = os.path.basename(finding.file_path) if finding.file_path else 'unknown'
            file_counts[file_name] = file_counts.get(file_name, 0) + 1
        
        # Calculate quality score
        quality_score = self._calculate_quality_score()
        
        return {
            'summary': {
                'total_findings': len(self.findings),
                'severity_distribution': severity_counts,
                'tool_distribution': tool_counts,
                'category_distribution': category_counts,
                'file_distribution': file_counts,
                'quality_score': quality_score,
                'quality_grade': self._get_quality_grade(quality_score)
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
                    'file_path': f.file_path,
                    'line_number': f.line_number,
                    'column_number': f.column_number,
                    'function_name': f.function_name,
                    'swc_id': f.swc_id,
                    'cwe_id': f.cwe_id,
                    'code_snippet': f.code_snippet,
                    'remediation': f.remediation,
                    'references': f.references
                }
                for f in self.findings
            ],
            'metrics': self.metrics,
            'tools_used': [tool for tool, available in self.tools_available.items() if available],
            'recommendations': self._generate_recommendations()
        }
    
    def _calculate_quality_score(self) -> int:
        """Calculate code quality score (0-100)."""
        
        if not self.findings:
            return 100
        
        # Penalty weights for different severities
        severity_penalties = {
            'Critical': 20,
            'High': 10,
            'Medium': 5,
            'Low': 2,
            'Info': 1
        }
        
        total_penalty = 0
        for finding in self.findings:
            penalty = severity_penalties.get(finding.severity, 1)
            confidence_multiplier = finding.confidence
            total_penalty += penalty * confidence_multiplier
        
        # Calculate score based on lines of code
        lines_of_code = self.metrics.get('total_lines_of_code', 100)
        penalty_per_line = total_penalty / lines_of_code
        
        # Normalize to 0-100 scale (lower penalty = higher score)
        quality_score = max(0, 100 - int(penalty_per_line * 100))
        
        return quality_score
    
    def _get_quality_grade(self, quality_score: int) -> str:
        """Get quality grade based on score."""
        
        if quality_score >= 90:
            return 'A+'
        elif quality_score >= 80:
            return 'A'
        elif quality_score >= 70:
            return 'B'
        elif quality_score >= 60:
            return 'C'
        elif quality_score >= 50:
            return 'D'
        else:
            return 'F'
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on static analysis results."""
        
        recommendations = []
        
        # Check for critical issues
        critical_count = sum(1 for f in self.findings if f.severity == 'Critical')
        if critical_count > 0:
            recommendations.append(f"🚨 {critical_count} critical security issues found! Address immediately.")
        
        # Check for high severity issues
        high_count = sum(1 for f in self.findings if f.severity == 'High')
        if high_count > 0:
            recommendations.append(f"⚠️ {high_count} high severity issues require prompt attention.")
        
        # Check for code quality
        info_count = sum(1 for f in self.findings if f.severity == 'Info')
        if info_count > 10:
            recommendations.append(f"📝 {info_count} code quality improvements suggested.")
        
        # Check for specific categories
        category_counts = {}
        for finding in self.findings:
            category_counts[finding.category] = category_counts.get(finding.category, 0) + 1
        
        if category_counts.get('reentrancy', 0) > 0:
            recommendations.append("🔄 Reentrancy vulnerabilities detected. Implement checks-effects-interactions pattern.")
        
        if category_counts.get('external_calls', 0) > 0:
            recommendations.append("📞 Unchecked external calls found. Always verify return values.")
        
        if category_counts.get('authorization', 0) > 0:
            recommendations.append("🔐 Authorization issues detected. Review access control mechanisms.")
        
        # General recommendations
        if not recommendations:
            recommendations.append("✅ No major security issues detected!")
            recommendations.append("🎯 Consider adding more comprehensive tests and documentation.")
        
        return recommendations
    
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
    
    def _normalize_solhint_severity(self, severity: int) -> str:
        """Normalize Solhint severity levels."""
        
        severity_map = {
            1: 'Info',
            2: 'Medium',
            3: 'High'
        }
        
        return severity_map.get(severity, 'Medium')
