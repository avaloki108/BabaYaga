"""Native Mythril module using symbolic execution without subprocess calls.

This module provides Mythril-like analysis without requiring the external binary,
using native Python implementations with Z3 for symbolic execution.
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.progress import Progress, TaskID

from babayaga.native.native_engine import NativeAnalysisEngine


class NativeMythrilModule:
    """Native Mythril module using symbolic execution.
    
    This module provides symbolic execution analysis similar to Mythril
    but implemented entirely in Python without subprocess calls.
    """
    
    def __init__(self, console: Console):
        self.console = console
        self.engine = NativeAnalysisEngine(console)
        self._available = True
    
    def is_available(self) -> bool:
        """Check if native Mythril is available."""
        return self._available
    
    async def run_analysis(self, target: str, progress: Progress, 
                          task_id: TaskID) -> List[Dict[str, Any]]:
        """Run native symbolic execution analysis.
        
        Args:
            target: Path to Solidity file or directory
            progress: Rich progress bar
            task_id: Task ID for progress updates
            
        Returns:
            List of findings in standardized format
        """
        findings = []
        
        try:
            progress.update(task_id, description="[yellow]🧠 Starting native symbolic execution...")
            
            # Prepare Solidity file
            sol_file = self._prepare_solidity_file(target)
            if not sol_file:
                progress.update(task_id, description="[yellow]⚠️ No Solidity files found")
                return findings
            
            progress.update(task_id, description="[yellow]🧠 Running symbolic analysis...")
            
            # Run native analysis with Mythril detectors
            config = {
                'only_enabled': True,
                'preferred_tools': ['mythril']  # Prioritize Mythril detectors
            }
            
            result = await self.engine.analyze_file(sol_file, config)
            
            # Convert findings to standardized format
            for finding_dict in result.get('findings', []):
                # Only include Mythril-based detectors
                if finding_dict.get('detector_id', '').startswith('native-mythril-'):
                    standardized = self._standardize_finding(finding_dict)
                    findings.append(standardized)
            
            progress.update(task_id, 
                          description=f"[green]✅ Native symbolic execution found {len(findings)} issues")
            
        except Exception as e:
            progress.update(task_id, description=f"[red]❌ Analysis error: {str(e)[:30]}...")
            self.console.print(f"[red]Native Mythril error: {e}[/red]")
        
        return findings
    
    async def run_quick_analysis(self, target: str) -> List[Dict[str, Any]]:
        """Run quick native symbolic analysis without progress updates.
        
        Args:
            target: Path to Solidity file or directory
            
        Returns:
            List of findings
        """
        sol_file = self._prepare_solidity_file(target)
        if not sol_file:
            return []
        
        try:
            config = {
                'only_enabled': True,
                'preferred_tools': ['mythril']
            }
            
            result = await self.engine.analyze_file(sol_file, config)
            
            findings = []
            for finding_dict in result.get('findings', []):
                if finding_dict.get('detector_id', '').startswith('native-mythril-'):
                    standardized = self._standardize_finding(finding_dict)
                    findings.append(standardized)
            
            return findings
            
        except Exception:
            return []
    
    def _prepare_solidity_file(self, target: str) -> Optional[str]:
        """Prepare Solidity file for analysis."""
        target_path = Path(target)
        
        if target_path.is_file() and target_path.suffix == '.sol':
            return str(target_path)
        
        if target_path.is_dir():
            sol_files = list(target_path.rglob('*.sol'))
            if sol_files:
                return str(sol_files[0])
        
        return None
    
    def _standardize_finding(self, finding_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert native finding to Mythril-compatible format.
        
        Args:
            finding_dict: Finding dictionary from native engine
            
        Returns:
            Standardized finding dictionary
        """
        return {
            'tool': 'mythril-native',
            'check': finding_dict.get('swc_id', finding_dict.get('detector_id', 'unknown')),
            'description': finding_dict.get('description', ''),
            'impact': finding_dict.get('severity', 'Medium'),
            'confidence': self._format_confidence(finding_dict.get('confidence', 0.8)),
            'elements': [],
            'markdown': finding_dict.get('description', ''),
            'swc_id': finding_dict.get('swc_id', ''),
            'title': finding_dict.get('title', ''),
            'filename': finding_dict.get('file_path', ''),
            'lineno': finding_dict.get('line_number', 0),
            'function': finding_dict.get('function_name', ''),
            'code': finding_dict.get('code_snippet', ''),
            'remediation': finding_dict.get('remediation', ''),
            'category': finding_dict.get('category', '')
        }
    
    def _format_confidence(self, confidence: float) -> str:
        """Convert confidence float to string category."""
        if confidence >= 0.9:
            return 'High'
        elif confidence >= 0.7:
            return 'Medium'
        else:
            return 'Low'
    
    def get_supported_detectors(self) -> List[str]:
        """Get list of supported vulnerability detectors."""
        return [
            'Integer Overflow (SWC-101)',
            'Integer Underflow (SWC-101)',
            'Reentrancy (SWC-107)',
            'Unchecked Call Return Value (SWC-104)',
            'Unprotected Ether Withdrawal (SWC-105)',
            'Unprotected Selfdestruct (SWC-106)',
            'Authorization through tx.origin (SWC-115)'
        ]
