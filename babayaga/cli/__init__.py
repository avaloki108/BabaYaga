"""CLI module for BabaYaga."""

from .main import app

def cli_entry_point():
    """Entry point for the CLI when installed as a package."""
    app()

__all__ = ['app', 'cli_entry_point']
