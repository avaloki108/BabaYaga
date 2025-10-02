"""Hybrid Slither module that can use native or external implementations.

This module provides a unified interface that can use either:
1. Native Python detector implementations
2. External Slither binary
3. Both (for validation/comparison)
"""

import json
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.progress import Progress, TaskID
import toml

from .slither_module import SlitherModule
from ..native.native_engine import NativeAnalysisEngine


class HybridSlitherModule:
    """Hybrid Slither module supporting native and external implementations."""
    
    def __init__(self, console: Console, config_path: Optional[str] = None):
        self.console = console
        self.external_module = SlitherModule(console)
        self.native_engine = NativeAnalysisEngine(console)
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        self.use_native = self.config.get('slither', {}).get('use_native', True)
        self.fallback_to_binary = self.config.get('slither', {}).get('fallback_to_binary', True)
        self.hybrid_mode = self.config.get('native_analysis', {}).get('hybrid_mode', False)
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load native analysis configuration."""
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return toml.load(f)
        
        # Try default config path
        default_path = Path(__file__).parent.parent / 'config' / 'native_config.toml'
        if default_path.exists():
            with open(default_path, 'r') as f:
                return toml.load(f)
        
        # Return default configuration
        return {
            'native_analysis': {'enabled': True, 'prefer_native': True, 'hybrid_mode': False},
            'slither': {'use_native': True, 'fallback_to_binary': True}
        }
    
    def is_available(self) -> bool:
        """Check if analysis is available (native or external)."""
        if self.use_native:
            # Native is always available
            return True
        return self.external_module.is_available()
    
    async def install_slither(self) -> bool:
        """Install Slither (only needed for external binary mode)."""
        if self.use_native and not self.fallback_to_binary:
            # Native only, no installation needed
            self.console.print("[green]✅ Native Slither detectors available[/green]")
            return True
        return await self.external_module.install_slither()
    
    async def run_analysis(self, target: str, progress: Progress, task_id: TaskID) -> List[Dict[str, Any]]:
        """Run Slither analysis using native, external, or both implementations."""
        findings = []
        
        # Determine which implementations to run
        run_native = self.use_native
        run_external = (not self.use_native and self.external_module.is_available()) or self.hybrid_mode
        
        if self.hybrid_mode:
            progress.update(task_id, description="[blue]🔬 Running hybrid analysis...")
        
        # Run native analysis
        if run_native:
            try:
                progress.update(task_id, description="[green]🔬 Running native Slither detectors...")
                
                native_result = await self.native_engine.analyze_project(target, {
                    'only_enabled': True
                })
                
                # Convert native findings to standard format
                for finding_dict in native_result.get('findings', []):
                    # Map native finding format to module format
                    findings.append({
                        'tool': 'slither-native',
                        'check': finding_dict['detector_id'],
                        'description': finding_dict['description'],
                        'impact': finding_dict['severity'],
                        'confidence': finding_dict['confidence'],
                        'elements': [],
                        'markdown': finding_dict.get('code_snippet', ''),
                        'file': finding_dict['file_path'],
                        'line': finding_dict.get('line_number'),
                        'function': finding_dict.get('function_name'),
                        'remediation': finding_dict.get('remediation'),
                        'swc_id': finding_dict.get('swc_id'),
                        'category': finding_dict.get('category'),
                        'source': 'native'
                    })
                
                progress.update(task_id, 
                              description=f"[green]✅ Native analysis: {len(native_result.get('findings', []))} issues[/green]")
            
            except Exception as e:
                self.console.print(f"[yellow]⚠️ Native analysis failed: {e}[/yellow]")
                if self.fallback_to_binary:
                    run_external = True
        
        # Run external binary analysis
        if run_external:
            try:
                progress.update(task_id, description="[green]🔍 Running external Slither binary...")
                
                external_findings = await self.external_module.run_analysis(target, progress, task_id)
                
                # Mark as external source
                for finding in external_findings:
                    finding['source'] = 'external'
                
                findings.extend(external_findings)
                
            except Exception as e:
                self.console.print(f"[yellow]⚠️ External Slither failed: {e}[/yellow]")
        
        # In hybrid mode, compare results
        if self.hybrid_mode and run_native and run_external:
            self._compare_results(findings)
        
        return findings
    
    def _compare_results(self, findings: List[Dict[str, Any]]):
        """Compare native and external results for validation."""
        native_findings = [f for f in findings if f.get('source') == 'native']
        external_findings = [f for f in findings if f.get('source') == 'external']
        
        self.console.print(f"\n[bold cyan]Hybrid Mode Comparison:[/bold cyan]")
        self.console.print(f"  Native detectors:   {len(native_findings)} findings")
        self.console.print(f"  External binary:    {len(external_findings)} findings")
        
        # Simple comparison by issue type
        native_checks = set(f['check'] for f in native_findings)
        external_checks = set(f['check'] for f in external_findings)
        
        if native_checks == external_checks:
            self.console.print(f"  [green]✓ Issue types match[/green]")
        else:
            only_native = native_checks - external_checks
            only_external = external_checks - native_checks
            
            if only_native:
                self.console.print(f"  [yellow]⚠ Only in native: {only_native}[/yellow]")
            if only_external:
                self.console.print(f"  [yellow]⚠ Only in external: {only_external}[/yellow]")
    
    def get_available_detectors(self) -> List[str]:
        """Get list of available detectors (native and/or external)."""
        detectors = []
        
        if self.use_native:
            # Get native detectors
            native_detectors = self.native_engine.registry.get_detectors_by_tool('slither')
            detectors.extend([d.detector_id for d in native_detectors])
        
        if not self.use_native or self.hybrid_mode:
            # Get external detectors
            detectors.extend(self.external_module.get_available_detectors())
        
        return list(set(detectors))  # Remove duplicates
    
    def get_version_info(self) -> Dict[str, Any]:
        """Get version information for native and external implementations."""
        info = {}
        
        if self.use_native:
            info['native'] = self.native_engine.registry.get_version_info()
        
        if self.external_module.is_available():
            try:
                result = subprocess.run(
                    [self.external_module.slither_path, '--version'],
                    capture_output=True, text=True
                )
                info['external_version'] = result.stdout.strip() if result.returncode == 0 else 'unknown'
            except:
                info['external_version'] = 'unavailable'
        
        return info
