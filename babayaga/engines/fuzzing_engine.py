"""Advanced Fuzzing Engine integrating Echidna, Medusa, and fuzz-utils."""

import asyncio
import json
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import yaml

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table

@dataclass
class FuzzingResult:
    """Fuzzing result with comprehensive metadata."""
    tool: str
    status: str  # 'passed', 'failed', 'error', 'timeout'
    properties_tested: int
    properties_failed: int
    coverage_percentage: float
    execution_time: float
    gas_usage: Dict[str, int]
    failing_sequences: List[Dict[str, Any]]
    corpus_size: int
    error_message: Optional[str] = None

@dataclass
class PropertyTest:
    """Property test definition."""
    name: str
    description: str
    function_name: str
    expected_result: bool
    category: str

class FuzzingEngine:
    """
    Advanced fuzzing engine that integrates:
    - Echidna (Haskell-based property testing)
    - Medusa (Go-based parallel fuzzing)
    - Fuzz-utils (test generation and harness creation)
    - Custom property generation
    """
    
    def __init__(self, console: Console):
        self.console = console
        self.logger = logging.getLogger(__name__)
        
        # Tool availability
        self.tools_available = {
            'echidna': self._check_echidna(),
            'medusa': self._check_medusa(),
            'fuzz_utils': self._check_fuzz_utils(),
            'foundry': self._check_foundry()
        }
        
        # Fuzzing results
        self.results: List[FuzzingResult] = []
        self.generated_tests: List[str] = []
        
    def _check_echidna(self) -> bool:
        """Check if Echidna is available."""
        try:
            result = subprocess.run(['echidna', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_medusa(self) -> bool:
        """Check if Medusa is available."""
        try:
            result = subprocess.run(['medusa', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_fuzz_utils(self) -> bool:
        """Check if fuzz-utils is available."""
        try:
            result = subprocess.run(['fuzz-utils', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_foundry(self) -> bool:
        """Check if Foundry is available."""
        try:
            result = subprocess.run(['forge', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    async def run_comprehensive_fuzzing(self, target_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run comprehensive fuzzing campaign using all available tools.
        
        Args:
            target_path: Path to the contract or project
            config: Fuzzing configuration
            
        Returns:
            Comprehensive fuzzing results
        """
        
        self.console.print(f"[bold green]🎯 Starting Comprehensive Fuzzing Campaign[/bold green]")
        self.console.print(f"[dim]Target: {target_path}[/dim]")
        
        # Reset results
        self.results = []
        self.generated_tests = []
        
        # Create temporary working directory
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            
            # Copy target to working directory
            if os.path.isfile(target_path):
                target_file = work_dir / Path(target_path).name
                shutil.copy2(target_path, target_file)
                working_target = str(target_file)
            else:
                working_target = target_path
            
            # Generate fuzzing harnesses if needed
            await self._generate_fuzzing_harnesses(working_target, work_dir, config)
            
            # Prepare fuzzing tasks
            fuzzing_tasks = []
            
            if self.tools_available['echidna']:
                fuzzing_tasks.append(('echidna', self._run_echidna_fuzzing))
            
            if self.tools_available['medusa']:
                fuzzing_tasks.append(('medusa', self._run_medusa_fuzzing))
            
            # Run fuzzing campaigns in parallel
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
                console=self.console
            ) as progress:
                
                # Create progress tasks
                task_ids = {}
                for tool_name, _ in fuzzing_tasks:
                    task_ids[tool_name] = progress.add_task(
                        f"Running {tool_name.title()} fuzzing...", 
                        total=100
                    )
                
                # Execute fuzzing campaigns
                with ThreadPoolExecutor(max_workers=2) as executor:  # Limit to 2 for resource management
                    future_to_tool = {
                        executor.submit(task_func, working_target, work_dir, config, progress, task_ids[tool_name]): tool_name
                        for tool_name, task_func in fuzzing_tasks
                    }
                    
                    for future in as_completed(future_to_tool):
                        tool_name = future_to_tool[future]
                        try:
                            result = future.result()
                            self.results.append(result)
                            progress.update(task_ids[tool_name], completed=100)
                            self.console.print(f"[green]✅ {tool_name.title()} fuzzing complete[/green]")
                        except Exception as e:
                            self.logger.error(f"Error in {tool_name} fuzzing: {e}")
                            progress.update(task_ids[tool_name], completed=100)
                            self.console.print(f"[red]❌ {tool_name.title()} fuzzing failed: {e}[/red]")
            
            # Generate unit tests from corpus if available
            await self._generate_unit_tests_from_corpus(work_dir, config)
        
        # Generate comprehensive report
        return self._generate_fuzzing_report()
    
    async def _generate_fuzzing_harnesses(self, target_path: str, work_dir: Path, config: Dict[str, Any]):
        """Generate fuzzing harnesses using fuzz-utils."""
        
        if not self.tools_available['fuzz_utils']:
            return
        
        try:
            self.console.print("[yellow]🔧 Generating fuzzing harnesses...[/yellow]")
            
            # Extract contract name
            contract_name = Path(target_path).stem
            
            # Generate harness using fuzz-utils
            cmd = [
                'fuzz-utils', 'template', target_path,
                '--name', f'{contract_name}FuzzHarness',
                '--contracts', contract_name,
                '--output-dir', str(work_dir / 'fuzzing'),
                '--mode', config.get('harness_mode', 'actor')
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=work_dir
            )
            
            if result.returncode == 0:
                self.console.print("[green]✅ Fuzzing harnesses generated[/green]")
            else:
                self.logger.warning(f"Harness generation failed: {result.stderr}")
                
        except Exception as e:
            self.logger.error(f"Failed to generate harnesses: {e}")
    
    def _run_echidna_fuzzing(self, target_path: str, work_dir: Path, config: Dict[str, Any], 
                            progress: Progress, task_id: int) -> FuzzingResult:
        """Run Echidna fuzzing campaign."""
        
        try:
            progress.update(task_id, advance=10)
            
            # Create Echidna configuration
            echidna_config = self._create_echidna_config(config)
            config_file = work_dir / 'echidna.yaml'
            
            with open(config_file, 'w') as f:
                yaml.dump(echidna_config, f)
            
            progress.update(task_id, advance=20)
            
            # Prepare Echidna command
            cmd = [
                'echidna', target_path,
                '--config', str(config_file),
                '--format', 'json'
            ]
            
            # Add contract name if specified
            if 'contract_name' in config:
                cmd.extend(['--contract', config['contract_name']])
            
            progress.update(task_id, advance=10)
            
            # Run Echidna
            start_time = asyncio.get_event_loop().time()
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.get('echidna_timeout', 300),
                cwd=work_dir
            )
            
            end_time = asyncio.get_event_loop().time()
            execution_time = end_time - start_time
            
            progress.update(task_id, advance=40)
            
            # Parse results
            if result.stdout:
                try:
                    echidna_data = json.loads(result.stdout)
                    return self._parse_echidna_results(echidna_data, execution_time)
                except json.JSONDecodeError:
                    pass
            
            # Fallback parsing for text output
            return self._parse_echidna_text_output(result.stdout, result.stderr, execution_time)
            
        except subprocess.TimeoutExpired:
            return FuzzingResult(
                tool='echidna',
                status='timeout',
                properties_tested=0,
                properties_failed=0,
                coverage_percentage=0.0,
                execution_time=config.get('echidna_timeout', 300),
                gas_usage={},
                failing_sequences=[],
                corpus_size=0,
                error_message='Fuzzing timed out'
            )
        except Exception as e:
            return FuzzingResult(
                tool='echidna',
                status='error',
                properties_tested=0,
                properties_failed=0,
                coverage_percentage=0.0,
                execution_time=0.0,
                gas_usage={},
                failing_sequences=[],
                corpus_size=0,
                error_message=str(e)
            )
        finally:
            progress.update(task_id, advance=20)
    
    def _run_medusa_fuzzing(self, target_path: str, work_dir: Path, config: Dict[str, Any], 
                           progress: Progress, task_id: int) -> FuzzingResult:
        """Run Medusa fuzzing campaign."""
        
        try:
            progress.update(task_id, advance=10)
            
            # Create Medusa configuration
            medusa_config = self._create_medusa_config(config)
            config_file = work_dir / 'medusa.json'
            
            with open(config_file, 'w') as f:
                json.dump(medusa_config, f, indent=2)
            
            progress.update(task_id, advance=20)
            
            # Prepare Medusa command
            cmd = [
                'medusa', 'fuzz',
                '--target', target_path,
                '--config', str(config_file)
            ]
            
            progress.update(task_id, advance=10)
            
            # Run Medusa
            start_time = asyncio.get_event_loop().time()
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.get('medusa_timeout', 300),
                cwd=work_dir
            )
            
            end_time = asyncio.get_event_loop().time()
            execution_time = end_time - start_time
            
            progress.update(task_id, advance=40)
            
            # Parse results
            return self._parse_medusa_results(result.stdout, result.stderr, execution_time)
            
        except subprocess.TimeoutExpired:
            return FuzzingResult(
                tool='medusa',
                status='timeout',
                properties_tested=0,
                properties_failed=0,
                coverage_percentage=0.0,
                execution_time=config.get('medusa_timeout', 300),
                gas_usage={},
                failing_sequences=[],
                corpus_size=0,
                error_message='Fuzzing timed out'
            )
        except Exception as e:
            return FuzzingResult(
                tool='medusa',
                status='error',
                properties_tested=0,
                properties_failed=0,
                coverage_percentage=0.0,
                execution_time=0.0,
                gas_usage={},
                failing_sequences=[],
                corpus_size=0,
                error_message=str(e)
            )
        finally:
            progress.update(task_id, advance=20)
    
    async def _generate_unit_tests_from_corpus(self, work_dir: Path, config: Dict[str, Any]):
        """Generate unit tests from fuzzing corpus using fuzz-utils."""
        
        if not self.tools_available['fuzz_utils']:
            return
        
        try:
            # Look for corpus directories
            corpus_dirs = []
            
            # Check for Echidna corpus
            echidna_corpus = work_dir / 'corpus'
            if echidna_corpus.exists():
                corpus_dirs.append(('echidna', echidna_corpus))
            
            # Check for Medusa corpus
            medusa_corpus = work_dir / '.medusa' / 'corpus'
            if medusa_corpus.exists():
                corpus_dirs.append(('medusa', medusa_corpus))
            
            # Generate tests for each corpus
            for fuzzer_name, corpus_dir in corpus_dirs:
                try:
                    cmd = [
                        'fuzz-utils', 'generate', str(work_dir),
                        '--corpus-dir', str(corpus_dir),
                        '--fuzzer', fuzzer_name,
                        '--test-directory', str(work_dir / 'test'),
                        '--all-sequences'
                    ]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=60,
                        cwd=work_dir
                    )
                    
                    if result.returncode == 0:
                        # Find generated test files
                        test_dir = work_dir / 'test'
                        if test_dir.exists():
                            for test_file in test_dir.glob('*.sol'):
                                with open(test_file, 'r') as f:
                                    self.generated_tests.append(f.read())
                        
                        self.console.print(f"[green]✅ Generated unit tests from {fuzzer_name} corpus[/green]")
                    
                except Exception as e:
                    self.logger.error(f"Failed to generate tests from {fuzzer_name} corpus: {e}")
        
        except Exception as e:
            self.logger.error(f"Failed to generate unit tests: {e}")
    
    def _create_echidna_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create Echidna configuration."""
        
        return {
            'testLimit': config.get('echidna_test_limit', 50000),
            'timeout': config.get('echidna_timeout', 300),
            'shrinkLimit': config.get('echidna_shrink_limit', 5000),
            'seqLen': config.get('echidna_sequence_length', 100),
            'contractAddr': '0x00a329c0648769A73afAc7F9381E08FB43dBEA72',
            'deployer': '0x00a329c0648769a73afac7f9381e08fb43dbea70',
            'sender': ['0x00a329c0648769a73afac7f9381e08fb43dbea71',
                      '0x00a329c0648769a73afac7f9381e08fb43dbea72',
                      '0x00a329c0648769a73afac7f9381e08fb43dbea73'],
            'psender': '0x00a329c0648769a73afac7f9381e08fb43dbea71',
            'coverage': True,
            'corpusDir': 'corpus',
            'format': 'json',
            'quiet': False
        }
    
    def _create_medusa_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create Medusa configuration."""
        
        return {
            'fuzzing': {
                'workers': config.get('medusa_workers', 4),
                'timeout': config.get('medusa_timeout', 300),
                'testLimit': config.get('medusa_test_limit', 50000),
                'shrinkLimit': config.get('medusa_shrink_limit', 5000),
                'sequenceLength': config.get('medusa_sequence_length', 100),
                'coverageEnabled': True,
                'corpusDirectory': '.medusa/corpus'
            },
            'compilation': {
                'platform': 'crytic-compile'
            },
            'logging': {
                'level': 'info',
                'logDirectory': '.medusa/logs'
            }
        }
    
    def _parse_echidna_results(self, data: Dict[str, Any], execution_time: float) -> FuzzingResult:
        """Parse Echidna JSON results."""
        
        tests = data.get('tests', [])
        properties_tested = len(tests)
        properties_failed = sum(1 for test in tests if test.get('status') == 'solved')
        
        # Extract coverage if available
        coverage = data.get('coverage', {})
        coverage_percentage = coverage.get('percentage', 0.0) if coverage else 0.0
        
        # Extract failing sequences
        failing_sequences = []
        for test in tests:
            if test.get('status') == 'solved' and 'transactions' in test:
                failing_sequences.append({
                    'property': test.get('name', 'unknown'),
                    'transactions': test['transactions']
                })
        
        status = 'passed' if properties_failed == 0 else 'failed'
        
        return FuzzingResult(
            tool='echidna',
            status=status,
            properties_tested=properties_tested,
            properties_failed=properties_failed,
            coverage_percentage=coverage_percentage,
            execution_time=execution_time,
            gas_usage={},
            failing_sequences=failing_sequences,
            corpus_size=len(failing_sequences)
        )
    
    def _parse_echidna_text_output(self, stdout: str, stderr: str, execution_time: float) -> FuzzingResult:
        """Parse Echidna text output."""
        
        # Basic parsing for text output
        lines = stdout.split('\n') + stderr.split('\n')
        
        properties_tested = 0
        properties_failed = 0
        
        for line in lines:
            if 'echidna_' in line:
                properties_tested += 1
                if 'FAILED' in line or 'ASSERTION VIOLATION' in line:
                    properties_failed += 1
        
        status = 'passed' if properties_failed == 0 else 'failed'
        
        return FuzzingResult(
            tool='echidna',
            status=status,
            properties_tested=properties_tested,
            properties_failed=properties_failed,
            coverage_percentage=0.0,
            execution_time=execution_time,
            gas_usage={},
            failing_sequences=[],
            corpus_size=0
        )
    
    def _parse_medusa_results(self, stdout: str, stderr: str, execution_time: float) -> FuzzingResult:
        """Parse Medusa results."""
        
        # Parse Medusa output
        lines = stdout.split('\n') + stderr.split('\n')
        
        properties_tested = 0
        properties_failed = 0
        coverage_percentage = 0.0
        
        for line in lines:
            # Look for test results
            if 'PASSED' in line or 'FAILED' in line:
                properties_tested += 1
                if 'FAILED' in line:
                    properties_failed += 1
            
            # Look for coverage information
            if 'coverage' in line.lower() and '%' in line:
                import re
                match = re.search(r'(\d+(?:\.\d+)?)%', line)
                if match:
                    coverage_percentage = float(match.group(1))
        
        status = 'passed' if properties_failed == 0 else 'failed'
        
        return FuzzingResult(
            tool='medusa',
            status=status,
            properties_tested=properties_tested,
            properties_failed=properties_failed,
            coverage_percentage=coverage_percentage,
            execution_time=execution_time,
            gas_usage={},
            failing_sequences=[],
            corpus_size=0
        )
    
    def _generate_fuzzing_report(self) -> Dict[str, Any]:
        """Generate comprehensive fuzzing report."""
        
        # Calculate overall statistics
        total_properties = sum(r.properties_tested for r in self.results)
        total_failures = sum(r.properties_failed for r in self.results)
        avg_coverage = sum(r.coverage_percentage for r in self.results) / len(self.results) if self.results else 0
        total_execution_time = sum(r.execution_time for r in self.results)
        
        # Determine overall status
        overall_status = 'passed'
        if any(r.status == 'error' for r in self.results):
            overall_status = 'error'
        elif any(r.status == 'timeout' for r in self.results):
            overall_status = 'timeout'
        elif total_failures > 0:
            overall_status = 'failed'
        
        return {
            'summary': {
                'overall_status': overall_status,
                'total_properties_tested': total_properties,
                'total_properties_failed': total_failures,
                'success_rate': ((total_properties - total_failures) / total_properties * 100) if total_properties > 0 else 100,
                'average_coverage': avg_coverage,
                'total_execution_time': total_execution_time,
                'tools_used': [r.tool for r in self.results],
                'generated_tests_count': len(self.generated_tests)
            },
            'tool_results': [
                {
                    'tool': r.tool,
                    'status': r.status,
                    'properties_tested': r.properties_tested,
                    'properties_failed': r.properties_failed,
                    'coverage_percentage': r.coverage_percentage,
                    'execution_time': r.execution_time,
                    'gas_usage': r.gas_usage,
                    'failing_sequences_count': len(r.failing_sequences),
                    'corpus_size': r.corpus_size,
                    'error_message': r.error_message
                }
                for r in self.results
            ],
            'failing_sequences': [
                seq for result in self.results for seq in result.failing_sequences
            ],
            'generated_tests': self.generated_tests,
            'recommendations': self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on fuzzing results."""
        
        recommendations = []
        
        # Check for failures
        total_failures = sum(r.properties_failed for r in self.results)
        if total_failures > 0:
            recommendations.append("🚨 Property violations found! Review failing test cases immediately.")
            recommendations.append("🔍 Analyze failing transaction sequences to understand attack vectors.")
        
        # Check coverage
        avg_coverage = sum(r.coverage_percentage for r in self.results) / len(self.results) if self.results else 0
        if avg_coverage < 80:
            recommendations.append(f"📊 Low coverage ({avg_coverage:.1f}%). Consider adding more properties or extending fuzzing time.")
        
        # Check for timeouts
        if any(r.status == 'timeout' for r in self.results):
            recommendations.append("⏱️ Some fuzzing campaigns timed out. Consider increasing timeout or optimizing contracts.")
        
        # Check for errors
        if any(r.status == 'error' for r in self.results):
            recommendations.append("❌ Some fuzzing tools encountered errors. Check tool installation and configuration.")
        
        # General recommendations
        if not recommendations:
            recommendations.append("✅ All fuzzing campaigns completed successfully!")
            recommendations.append("🎯 Consider adding more complex invariants to increase test coverage.")
        
        return recommendations
