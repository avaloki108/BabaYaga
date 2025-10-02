"""Example script demonstrating Medusa-style symbolic analysis.

This script shows how to use the native Medusa detectors for invariant
and property checking on smart contracts.
"""

import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from babayaga.native.native_engine import NativeAnalysisEngine


# Example vulnerable contract
VULNERABLE_CONTRACT = """
pragma solidity ^0.8.0;

contract VulnerableToken {
    uint256 public totalSupply;
    mapping(address => uint256) public balances;
    address public owner;
    
    constructor() {
        owner = msg.sender;
        totalSupply = 1000000;
    }
    
    // CONSERVATION VIOLATION: Missing totalSupply update
    function mint(address to, uint256 amount) public {
        balances[to] += amount;
        // BUG: totalSupply not updated!
    }
    
    // PERMISSION VIOLATION: Missing access control
    function setOwner(address newOwner) public {
        owner = newOwner;
        // BUG: Anyone can change owner!
    }
    
    // CRITICAL PERMISSION VIOLATION: Unprotected selfdestruct
    function destroy() public {
        selfdestruct(payable(owner));
        // BUG: Anyone can destroy the contract!
    }
    
    // PROPERTY: This invariant will be violated
    function echidna_supply_conservation() public view returns (bool) {
        // This property checks if supply is properly tracked
        return totalSupply >= sumOfBalances();
    }
    
    function sumOfBalances() private view returns (uint256) {
        // Simplified - in real contract would sum all balances
        return 0;
    }
    
    // LIVENESS ISSUE: Potential deadlock
    function restrictedWithdraw() public {
        require(balances[msg.sender] > 0);
        require(msg.sender == owner);
        require(owner != address(0));
        // Multiple requirements may make this hard to satisfy
    }
}
"""

# Example safe contract
SAFE_CONTRACT = """
pragma solidity ^0.8.0;

contract SafeToken {
    uint256 public totalSupply;
    mapping(address => uint256) public balances;
    address public owner;
    
    constructor() {
        owner = msg.sender;
        totalSupply = 1000000;
    }
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    
    // CORRECT: Both balance and supply updated
    function mint(address to, uint256 amount) public onlyOwner {
        require(to != address(0), "Invalid address");
        balances[to] += amount;
        totalSupply += amount;
    }
    
    // CORRECT: Access control in place
    function setOwner(address newOwner) public onlyOwner {
        require(newOwner != address(0), "Invalid address");
        owner = newOwner;
    }
    
    // CORRECT: Property should hold
    function invariant_supply_conservation() public view returns (bool) {
        return totalSupply >= 0;
    }
    
    // CORRECT: Safe withdraw
    function withdraw() public {
        uint256 balance = balances[msg.sender];
        require(balance > 0, "No balance");
        
        balances[msg.sender] = 0;
        payable(msg.sender).transfer(balance);
    }
}
"""


async def analyze_contract(console: Console, contract_code: str, name: str):
    """Analyze a contract and display results."""
    
    console.print(Panel(f"[bold cyan]Analyzing {name}[/bold cyan]"))
    
    # Create temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sol', delete=False) as f:
        f.write(contract_code)
        temp_file = f.name
    
    try:
        # Create analysis engine
        engine = NativeAnalysisEngine(console)
        
        # Analyze contract
        result = await engine.analyze_file(temp_file)
        
        findings = result['findings']
        
        # Display summary
        console.print(f"\n[yellow]Total findings: {len(findings)}[/yellow]")
        
        # Group findings by detector
        by_detector = {}
        for finding in findings:
            detector_id = finding['detector_id']
            if detector_id not in by_detector:
                by_detector[detector_id] = []
            by_detector[detector_id].append(finding)
        
        # Display findings by detector type
        medusa_detectors = {k: v for k, v in by_detector.items() if 'medusa' in k}
        
        if medusa_detectors:
            console.print("\n[bold green]Medusa Symbolic Analysis Findings:[/bold green]")
            
            for detector_id, detector_findings in medusa_detectors.items():
                detector_name = detector_id.replace('native-medusa-', '').title()
                console.print(f"\n[cyan]{detector_name} ({len(detector_findings)} findings):[/cyan]")
                
                # Create table for this detector's findings
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Title", style="yellow", width=40)
                table.add_column("Severity", width=12)
                table.add_column("Line", width=8)
                
                for finding in detector_findings[:5]:  # Show first 5
                    table.add_row(
                        finding['title'][:37] + "..." if len(finding['title']) > 40 else finding['title'],
                        f"[{_get_severity_color(finding['severity'])}]{finding['severity']}[/]",
                        str(finding.get('line_number', '-'))
                    )
                
                console.print(table)
                
                if len(detector_findings) > 5:
                    console.print(f"[dim]... and {len(detector_findings) - 5} more findings[/dim]")
        
        # Display detailed example finding
        if findings:
            console.print("\n[bold]Example Finding Detail:[/bold]")
            example = findings[0]
            console.print(f"  [cyan]Title:[/cyan] {example['title']}")
            console.print(f"  [cyan]Description:[/cyan] {example['description']}")
            console.print(f"  [cyan]Severity:[/cyan] [{_get_severity_color(example['severity'])}]{example['severity']}[/]")
            console.print(f"  [cyan]Remediation:[/cyan] {example.get('remediation', 'N/A')}")
        
        return result
        
    finally:
        import os
        os.unlink(temp_file)


def _get_severity_color(severity: str) -> str:
    """Get color for severity level."""
    colors = {
        'Critical': 'red bold',
        'High': 'red',
        'Medium': 'yellow',
        'Low': 'blue',
        'Info': 'cyan'
    }
    return colors.get(severity, 'white')


async def main():
    """Main function."""
    console = Console()
    
    console.print(Panel.fit(
        "[bold cyan]Medusa-Style Symbolic Analysis Demo[/bold cyan]\n"
        "Native implementation of Medusa's invariant and property checking",
        border_style="cyan"
    ))
    
    # Analyze vulnerable contract
    console.print("\n" + "="*70)
    await analyze_contract(console, VULNERABLE_CONTRACT, "Vulnerable Contract")
    
    # Analyze safe contract
    console.print("\n" + "="*70)
    await analyze_contract(console, SAFE_CONTRACT, "Safe Contract")
    
    # Summary
    console.print("\n" + "="*70)
    console.print(Panel(
        "[bold green]Analysis Complete![/bold green]\n\n"
        "The Medusa-style symbolic analysis detectors checked for:\n"
        "  • [cyan]Conservation invariants[/cyan] - Balance/supply tracking\n"
        "  • [cyan]Permission invariants[/cyan] - Access control issues\n"
        "  • [cyan]Liveness invariants[/cyan] - Deadlocks and unreachable code\n"
        "  • [cyan]Property violations[/cyan] - Custom invariant violations\n\n"
        "For more information, see: babayaga/native/README.md",
        border_style="green"
    ))


if __name__ == "__main__":
    asyncio.run(main())
