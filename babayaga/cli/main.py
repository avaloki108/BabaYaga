#!/usr/bin/env python3
"""BabaYaga CLI Main - Entry point module for the BabaYaga command line interface."""

import asyncio
import sys
import argparse
from pathlib import Path

# Import from parent package
from ..client import BabaYagaClient


def create_parser():
    """Create the command line argument parser."""
    
    parser = argparse.ArgumentParser(
        prog='babayaga',
        description='BabaYaga - The Legendary Web3 Security Auditor',
        epilog='With a fucking pencil... and some smart contracts'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='BabaYaga v4.0 - Elite Web3 Vulnerability Research System'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Interactive mode (default)
    interactive_parser = subparsers.add_parser(
        'interactive',
        help='Start interactive BabaYaga session'
    )
    
    # Audit command
    audit_parser = subparsers.add_parser(
        'audit',
        help='Execute comprehensive elite audit'
    )
    audit_parser.add_argument(
        'target',
        help='Target contract, directory, or repository to audit'
    )
    audit_parser.add_argument(
        '--stealth',
        action='store_true',
        help='Enable stealth mode'
    )
    audit_parser.add_argument(
        '--threshold',
        type=int,
        default=200,
        help='Minimum score threshold for findings (default: 200)'
    )
    
    # Quick scan command
    quick_parser = subparsers.add_parser(
        'quick',
        help='Execute quick vulnerability scan'
    )
    quick_parser.add_argument(
        'target',
        help='Target contract, directory, or repository to scan'
    )
    
    # Hunt command
    hunt_parser = subparsers.add_parser(
        'hunt',
        help='Deploy elite vulnerability hunters'
    )
    hunt_parser.add_argument(
        'target',
        help='Target contract, directory, or repository to hunt'
    )
    hunt_parser.add_argument(
        '--agents',
        type=int,
        default=10,
        help='Number of hunter agents to deploy (default: 10)'
    )
    
    return parser


async def async_main():
    """Async main CLI entry point."""
    
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        client = BabaYagaClient()
        
        if args.command == 'audit':
            # Direct audit execution
            config = {
                'target': args.target,
                'mode': 'comprehensive',
                'stealth_mode': args.stealth,
                'minimum_score_threshold': args.threshold,
                'enable_elite_agents': True,
                'enable_ai_enhancement': True,
                'persistence_mode': True
            }
            
            await client._execute_audit(args.target)
            
        elif args.command == 'quick':
            # Direct quick scan execution
            await client._execute_quick_scan(args.target)
            
        elif args.command == 'hunt':
            # Direct elite hunt execution
            await client._execute_elite_hunt(args.target)
            
        else:
            # Default to interactive mode
            await client.start()
            
    except KeyboardInterrupt:
        print("\n💀 BabaYaga interrupted. Returning to the shadows...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


def app():
    """
    Callable entry point for the BabaYaga CLI.
    
    This function serves as the main entry point referenced in pyproject.toml
    as 'babayaga.cli.main:app'.
    """
    asyncio.run(async_main())


if __name__ == "__main__":
    app()
