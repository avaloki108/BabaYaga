"""Native analysis engine that orchestrates native detectors."""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from .detector_registry import get_registry, DetectorRegistry
from .base_detector import DetectorFinding
from .slither_detectors import ReentrancyDetector, TxOriginDetector, UncheckedCallDetector
from .securify2_detectors import (
    IntegerOverflowDetector, UninitializedStorageDetector, 
    MissingAccessControlDetector, TimestampDependenceDetector,
    UnsafeDelegatecallDetector, UnprotectedSelfdestructDetector,
    LockedEtherDetector
)


logger = logging.getLogger(__name__)


class NativeAnalysisEngine:
    """Engine for running native security analysis.
    
    This engine uses native detector implementations instead of
    external tool binaries, while tracking upstream tool versions
    for easy updates.
    """
    
    def __init__(self, console: Console):
        self.console = console
        self.registry = get_registry()
        self._initialize_detectors()
    
    def _initialize_detectors(self):
        """Register all available native detectors."""
        # Register Slither-based detectors
        self.registry.register(ReentrancyDetector)
        self.registry.register(TxOriginDetector)
        self.registry.register(UncheckedCallDetector)
        
        # Register Securify2-based detectors
        self.registry.register(IntegerOverflowDetector)
        self.registry.register(UninitializedStorageDetector)
        self.registry.register(MissingAccessControlDetector)
        self.registry.register(TimestampDependenceDetector)
        self.registry.register(UnsafeDelegatecallDetector)
        self.registry.register(UnprotectedSelfdestructDetector)
        self.registry.register(LockedEtherDetector)
        
        # Future: Register Mythril-based detectors
        # Future: Register Medusa-based detectors
        
        status = self.registry.get_detector_status()
        logger.info(f"Initialized native analysis engine with {status['total_detectors']} detectors")
    
    async def analyze_file(self, file_path: str, 
                          config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze a single Solidity file.
        
        Args:
            file_path: Path to the Solidity file
            config: Optional configuration for analysis
            
        Returns:
            Analysis results with findings
        """
        config = config or {}
        
        try:
            # Read source code
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # Run analysis
            findings = await self.registry.run_all_detectors(
                source_code, 
                file_path,
                only_enabled=config.get('only_enabled', True)
            )
            
            return {
                'file': file_path,
                'findings': [f.to_dict() for f in findings],
                'summary': self._create_summary(findings)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return {
                'file': file_path,
                'findings': [],
                'error': str(e)
            }
    
    async def analyze_project(self, target_path: str, 
                             config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze a project directory.
        
        Args:
            target_path: Path to the project directory
            config: Optional configuration for analysis
            
        Returns:
            Comprehensive analysis results
        """
        config = config or {}
        
        self.console.print("[bold green]🔬 Starting Native Analysis[/bold green]")
        self.console.print(f"[dim]Target: {target_path}[/dim]")
        
        # Find all Solidity files
        sol_files = self._find_solidity_files(target_path)
        
        if not sol_files:
            self.console.print("[yellow]⚠️ No Solidity files found[/yellow]")
            return {
                'target': target_path,
                'files': [],
                'findings': [],
                'summary': {}
            }
        
        self.console.print(f"[cyan]Found {len(sol_files)} Solidity files[/cyan]")
        
        # Analyze files with progress tracking
        all_findings = []
        file_results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            
            task = progress.add_task(
                "[green]Analyzing files...", 
                total=len(sol_files)
            )
            
            for sol_file in sol_files:
                progress.update(task, description=f"[green]Analyzing {Path(sol_file).name}...")
                
                result = await self.analyze_file(sol_file, config)
                file_results.append(result)
                all_findings.extend(result.get('findings', []))
                
                progress.advance(task)
        
        # Create comprehensive report
        report = {
            'target': target_path,
            'files_analyzed': len(sol_files),
            'file_results': file_results,
            'findings': all_findings,
            'summary': self._create_summary_from_dicts(all_findings),
            'detector_info': self._get_detector_info()
        }
        
        # Display summary
        self._display_summary(report)
        
        return report
    
    def _find_solidity_files(self, target_path: str) -> List[str]:
        """Find all Solidity files in target path."""
        path = Path(target_path)
        
        if path.is_file() and path.suffix == '.sol':
            return [str(path)]
        
        if path.is_dir():
            return [str(f) for f in path.rglob('*.sol')]
        
        return []
    
    def _create_summary(self, findings: List[DetectorFinding]) -> Dict[str, Any]:
        """Create summary statistics from findings."""
        severity_counts = {}
        category_counts = {}
        detector_counts = {}
        
        for finding in findings:
            # Count by severity
            severity = finding.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Count by category
            if finding.category:
                category = finding.category.value
                category_counts[category] = category_counts.get(category, 0) + 1
            
            # Count by detector
            detector_counts[finding.detector_id] = detector_counts.get(finding.detector_id, 0) + 1
        
        return {
            'total_findings': len(findings),
            'by_severity': severity_counts,
            'by_category': category_counts,
            'by_detector': detector_counts
        }
    
    def _create_summary_from_dicts(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create summary statistics from finding dictionaries."""
        severity_counts = {}
        category_counts = {}
        detector_counts = {}
        
        for finding in findings:
            # Count by severity
            severity = finding.get('severity', 'Unknown')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Count by category
            if finding.get('category'):
                category = finding['category']
                category_counts[category] = category_counts.get(category, 0) + 1
            
            # Count by detector
            detector_id = finding.get('detector_id', 'unknown')
            detector_counts[detector_id] = detector_counts.get(detector_id, 0) + 1
        
        return {
            'total_findings': len(findings),
            'by_severity': severity_counts,
            'by_category': category_counts,
            'by_detector': detector_counts
        }
    
    def _get_detector_info(self) -> Dict[str, Any]:
        """Get information about registered detectors."""
        return {
            'version_info': self.registry.get_version_info(),
            'status': self.registry.get_detector_status()
        }
    
    def _display_summary(self, report: Dict[str, Any]):
        """Display analysis summary to console."""
        summary = report['summary']
        
        self.console.print("\n[bold green]✅ Native Analysis Complete[/bold green]")
        self.console.print(f"[cyan]Files analyzed: {report['files_analyzed']}[/cyan]")
        self.console.print(f"[yellow]Total findings: {summary['total_findings']}[/yellow]")
        
        if summary.get('by_severity'):
            self.console.print("\n[bold]Findings by Severity:[/bold]")
            severity_order = ['Critical', 'High', 'Medium', 'Low', 'Info']
            for severity in severity_order:
                count = summary['by_severity'].get(severity, 0)
                if count > 0:
                    color = self._get_severity_color(severity)
                    self.console.print(f"  [{color}]{severity}: {count}[/{color}]")
    
    def _get_severity_color(self, severity: str) -> str:
        """Get color for severity level."""
        color_map = {
            'Critical': 'red bold',
            'High': 'red',
            'Medium': 'yellow',
            'Low': 'blue',
            'Info': 'cyan'
        }
        return color_map.get(severity, 'white')
    
    def export_version_manifest(self, output_path: str):
        """Export detector version manifest.
        
        This creates a JSON file tracking which upstream tool versions
        each detector is based on, making it easy to identify detectors
        that need updating.
        
        Args:
            output_path: Path to write manifest file
        """
        self.registry.export_version_manifest(Path(output_path))
        self.console.print(f"[green]✅ Version manifest exported to {output_path}[/green]")
