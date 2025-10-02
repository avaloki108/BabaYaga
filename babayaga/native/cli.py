"""Command-line interface for native analysis engine."""

import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .native_engine import NativeAnalysisEngine
from .detector_registry import get_registry


console = Console()


async def analyze_command(target: str, output: str = None):
    """Run native analysis on target."""
    engine = NativeAnalysisEngine(console)
    
    console.print(f"\n[bold blue]BabaYaga Native Analysis[/bold blue]")
    console.print(f"[dim]Target: {target}[/dim]\n")
    
    # Run analysis
    result = await engine.analyze_project(target)
    
    # Display results
    if result['findings']:
        console.print("\n[bold red]🔍 Security Findings:[/bold red]\n")
        
        for finding_dict in result['findings'][:10]:  # Show first 10
            severity_color = {
                'Critical': 'red bold',
                'High': 'red',
                'Medium': 'yellow',
                'Low': 'blue',
                'Info': 'cyan'
            }.get(finding_dict['severity'], 'white')
            
            console.print(Panel(
                f"[bold]{finding_dict['title']}[/bold]\n\n"
                f"{finding_dict['description']}\n\n"
                f"[dim]File: {finding_dict['file_path']}:{finding_dict.get('line_number', '?')}[/dim]\n"
                f"[dim]Detector: {finding_dict['detector_id']}[/dim]",
                title=f"[{severity_color}]{finding_dict['severity']}[/{severity_color}]",
                border_style=severity_color
            ))
        
        if len(result['findings']) > 10:
            console.print(f"\n[dim]... and {len(result['findings']) - 10} more findings[/dim]")
    else:
        console.print("\n[green]✅ No issues found![/green]")
    
    # Export if requested
    if output:
        import json
        with open(output, 'w') as f:
            json.dump(result, f, indent=2)
        console.print(f"\n[green]Results exported to {output}[/green]")


def list_detectors_command():
    """List all available native detectors."""
    registry = get_registry()
    engine = NativeAnalysisEngine(console)
    
    detectors = registry.get_all_detectors()
    version_info = registry.get_version_info()
    
    console.print("\n[bold blue]Available Native Detectors[/bold blue]\n")
    
    # Create table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Detector ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Source Tool", style="yellow")
    table.add_column("Version", style="green")
    table.add_column("Severity", style="red")
    table.add_column("Enabled", style="blue")
    
    for detector in detectors:
        metadata = detector.metadata
        enabled = "✓" if metadata.enabled_by_default else "✗"
        
        table.add_row(
            metadata.detector_id,
            metadata.name,
            metadata.source_tool,
            metadata.source_version,
            metadata.severity.value,
            enabled
        )
    
    console.print(table)
    
    # Show summary by tool
    status = registry.get_detector_status()
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Total detectors: {status['total_detectors']}")
    console.print(f"  Enabled: {status['enabled_detectors']}")
    console.print(f"  By tool:")
    for tool, count in status['by_tool'].items():
        console.print(f"    {tool}: {count}")


def version_info_command():
    """Display version information for all detectors."""
    registry = get_registry()
    engine = NativeAnalysisEngine(console)
    
    version_info = registry.get_version_info()
    
    console.print("\n[bold blue]Native Detector Version Information[/bold blue]\n")
    
    # Group by source tool
    by_tool = {}
    for detector_id, info in version_info.items():
        tool = info['source_tool']
        if tool not in by_tool:
            by_tool[tool] = []
        by_tool[tool].append((detector_id, info))
    
    for tool, detectors in sorted(by_tool.items()):
        console.print(f"\n[bold yellow]{tool.upper()}[/bold yellow]")
        console.print(f"[dim]Based on {tool} version {detectors[0][1]['source_version']}[/dim]")
        
        table = Table(show_header=True, header_style="bold")
        table.add_column("Native Detector", style="cyan")
        table.add_column("Upstream ID", style="white")
        table.add_column("Last Updated", style="green")
        
        for detector_id, info in detectors:
            table.add_row(
                detector_id,
                info['source_detector_id'],
                info['last_updated']
            )
        
        console.print(table)


def export_manifest_command(output: str):
    """Export detector version manifest."""
    registry = get_registry()
    engine = NativeAnalysisEngine(console)
    
    engine.export_version_manifest(output)
    console.print(f"[green]✅ Manifest exported successfully[/green]")


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        console.print("[bold red]Usage:[/bold red]")
        console.print("  babayaga-native analyze <target> [--output <file>]")
        console.print("  babayaga-native list-detectors")
        console.print("  babayaga-native version-info")
        console.print("  babayaga-native export-manifest <output>")
        return
    
    command = sys.argv[1]
    
    try:
        if command == "analyze":
            if len(sys.argv) < 3:
                console.print("[red]Error: target path required[/red]")
                return
            
            target = sys.argv[2]
            output = None
            
            if len(sys.argv) > 3 and sys.argv[3] == "--output":
                output = sys.argv[4] if len(sys.argv) > 4 else None
            
            asyncio.run(analyze_command(target, output))
        
        elif command == "list-detectors":
            list_detectors_command()
        
        elif command == "version-info":
            version_info_command()
        
        elif command == "export-manifest":
            if len(sys.argv) < 3:
                console.print("[red]Error: output path required[/red]")
                return
            
            output = sys.argv[2]
            export_manifest_command(output)
        
        else:
            console.print(f"[red]Unknown command: {command}[/red]")
    
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
