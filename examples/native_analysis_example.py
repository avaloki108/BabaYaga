#!/usr/bin/env python3
"""
Example: Using Native Static Analysis

This example demonstrates how to use BabaYaga's native static analysis
engine to analyze smart contracts without requiring external tools.
"""

import asyncio
from rich.console import Console
from babayaga.native.native_engine import NativeAnalysisEngine
from babayaga.engines.static_engine import StaticAnalysisEngine

# Example vulnerable contract
VULNERABLE_CONTRACT = """
pragma solidity ^0.7.0;

contract VulnerableBank {
    mapping(address => uint256) public balances;
    address public owner;
    
    constructor() {
        owner = msg.sender;
    }
    
    // Vulnerability 1: Reentrancy
    function withdraw() public {
        uint256 amount = balances[msg.sender];
        msg.sender.call{value: amount}("");  // External call before state change
        balances[msg.sender] = 0;            // State change after call - reentrancy!
    }
    
    // Vulnerability 2: Integer overflow
    function deposit() public payable {
        balances[msg.sender] += msg.value;   // Can overflow in Solidity < 0.8.0
    }
    
    // Vulnerability 3: tx.origin
    function withdrawOwner() public {
        require(tx.origin == owner);          // Vulnerable to phishing attacks
        payable(msg.sender).transfer(address(this).balance);
    }
    
    // Vulnerability 4: Missing access control
    function transferOwnership(address newOwner) public {
        owner = newOwner;                     // Anyone can become owner!
    }
    
    // Vulnerability 5: Weak randomness
    function random() public view returns (uint256) {
        return uint256(blockhash(block.number - 1)) % 100;  // Predictable!
    }
    
    // Vulnerability 6: Timestamp dependence
    function isExpired(uint256 deadline) public view returns (bool) {
        return block.timestamp > deadline;    // Can be manipulated by miners
    }
}
"""


async def example_1_native_engine():
    """Example 1: Using NativeAnalysisEngine directly."""
    print("\n" + "="*60)
    print("Example 1: Native Analysis Engine")
    print("="*60 + "\n")
    
    console = Console()
    engine = NativeAnalysisEngine(console)
    
    # Write the vulnerable contract to a temp file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sol', delete=False) as f:
        f.write(VULNERABLE_CONTRACT)
        temp_file = f.name
    
    try:
        # Analyze the file
        result = await engine.analyze_file(temp_file)
        
        # Display results
        console.print(f"\n[bold]Analysis Results:[/bold]")
        console.print(f"File: {result['file']}")
        console.print(f"Total Findings: {result['summary']['total_findings']}")
        
        if result['findings']:
            console.print(f"\n[bold red]Vulnerabilities Found:[/bold red]\n")
            for finding in result['findings']:
                console.print(f"[yellow]● {finding['title']}[/yellow]")
                console.print(f"  Severity: {finding['severity']}")
                console.print(f"  Line: {finding['line_number']}")
                console.print(f"  Description: {finding['description'][:100]}...")
                console.print()
    
    finally:
        import os
        os.unlink(temp_file)


async def example_2_static_engine():
    """Example 2: Using StaticAnalysisEngine with native analysis."""
    print("\n" + "="*60)
    print("Example 2: Static Analysis Engine (Native Mode)")
    print("="*60 + "\n")
    
    console = Console()
    engine = StaticAnalysisEngine(console)
    
    # Write the vulnerable contract to a temp file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sol', delete=False) as f:
        f.write(VULNERABLE_CONTRACT)
        temp_file = f.name
    
    try:
        # Configure to use native analysis
        config = {
            'use_native_analysis': True,  # Use native detectors
        }
        
        # Analyze the contract
        result = await engine.analyze_contracts(temp_file, config)
        
        # Display summary
        console.print(f"\n[bold]Analysis Summary:[/bold]")
        summary = result['summary']
        console.print(f"Total Findings: {summary['total_findings']}")
        console.print(f"Quality Score: {summary['quality_score']}/100")
        console.print(f"Quality Grade: {summary['quality_grade']}")
        
        if summary['severity_distribution']:
            console.print(f"\n[bold]By Severity:[/bold]")
            for severity, count in summary['severity_distribution'].items():
                console.print(f"  {severity}: {count}")
        
        # Show recommendations
        if result.get('recommendations'):
            console.print(f"\n[bold cyan]Recommendations:[/bold cyan]")
            for rec in result['recommendations']:
                console.print(f"  {rec}")
    
    finally:
        import os
        os.unlink(temp_file)


async def example_3_detector_info():
    """Example 3: Getting detector information."""
    print("\n" + "="*60)
    print("Example 3: Detector Information")
    print("="*60 + "\n")
    
    console = Console()
    engine = NativeAnalysisEngine(console)
    
    # Get detector status
    status = engine.registry.get_detector_status()
    
    console.print(f"[bold]Registered Detectors:[/bold]")
    console.print(f"Total: {status['total_detectors']}")
    console.print(f"Enabled: {status['enabled_detectors']}")
    console.print(f"\nBy Tool:")
    for tool, count in status['by_tool'].items():
        console.print(f"  {tool}: {count} detectors")
    
    # Get version information
    console.print(f"\n[bold]Version Information:[/bold]")
    version_info = engine.registry.get_version_info()
    
    for detector_id, info in version_info.items():
        console.print(f"\n  {detector_id}:")
        console.print(f"    Source: {info['source_tool']} v{info['source_version']}")
        console.print(f"    Last Updated: {info['last_updated']}")


async def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("BabaYaga Native Static Analysis Examples")
    print("="*60)
    
    # Run examples
    await example_1_native_engine()
    await example_2_static_engine()
    await example_3_detector_info()
    
    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
