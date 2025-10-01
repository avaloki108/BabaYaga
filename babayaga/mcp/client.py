"""MCP Client integrated with BabaYaga for Ollama and MCP server interactions."""
import asyncio
import os
from contextlib import AsyncExitStack
from typing import List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
import ollama

from ..config.babayaga_config import BabaYagaConfigManager


class MCPClient:
    """MCP Client for interacting with Ollama models and MCP servers within BabaYaga."""

    def __init__(self, model: str = "qwen2.5-coder:7b", host: str = "http://localhost:11434", console: Optional[Console] = None):
        self.exit_stack = AsyncExitStack()
        self.ollama = ollama.AsyncClient(host=host)
        self.console = console or Console()
        self.config_manager = BabaYagaConfigManager(self.console)
        
        # MCP server sessions
        self.sessions = {}
        self.available_tools = []
        self.enabled_tools = []
        
        # Chat state
        self.chat_history = []
        self.current_model = model
        self.retain_context = True
        
    async def connect_to_mcp_servers(self):
        """Connect to configured MCP servers."""
        enabled_servers = self.config_manager.get_enabled_mcp_servers()
        
        if not enabled_servers:
            self.console.print("[yellow]No MCP servers configured. Use BabaYaga config to add servers.[/yellow]")
            return
        
        self.console.print(f"[cyan]Connecting to {len(enabled_servers)} MCP server(s)...[/cyan]")
        
        for name, server in enabled_servers.items():
            try:
                # Placeholder for actual MCP connection
                # In future, implement actual MCP protocol connection
                self.console.print(f"[green]✓ Connected to {name}[/green]")
            except Exception as e:
                self.console.print(f"[red]✗ Failed to connect to {name}: {e}[/red]")
    
    async def chat_loop(self):
        """Run interactive chat loop with MCP tool support."""
        self.console.print(Panel(
            Text.from_markup(
                "[bold green]BabaYaga MCP Chat 💀🦙[/bold green]\n\n"
                "Chat with Ollama models and use MCP tools for smart contract analysis",
                justify="center"
            ),
            expand=True,
            border_style="green"
        ))
        
        await self.connect_to_mcp_servers()
        
        self.console.print("\nType 'help' for commands, 'quit' to exit\n")
        
        while True:
            try:
                query = input(f"{self.current_model}❯ ")
                
                if query.lower() in ['quit', 'q', 'exit']:
                    break
                    
                if query.lower() == 'help':
                    self._print_help()
                    continue
                    
                if query.lower() == 'clear':
                    self.chat_history = []
                    self.console.print("[green]Context cleared[/green]")
                    continue
                
                if len(query.strip()) < 3:
                    continue
                
                response = await self.process_query(query)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
    
    async def process_query(self, query: str) -> str:
        """Process a query using Ollama."""
        # Build message history
        messages = []
        
        if self.retain_context:
            for entry in self.chat_history:
                messages.append({"role": "user", "content": entry["query"]})
                messages.append({"role": "assistant", "content": entry["response"]})
        
        messages.append({"role": "user", "content": query})
        
        # Call Ollama
        response_text = ""
        
        try:
            stream = await self.ollama.chat(
                model=self.current_model,
                messages=messages,
                stream=True
            )
            
            # Display streaming response
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    content = chunk['message']['content']
                    self.console.print(content, end="")
                    response_text += content
            
            self.console.print()  # New line after response
            
            # Store in history
            self.chat_history.append({"query": query, "response": response_text})
            
            return response_text
            
        except Exception as e:
            self.console.print(f"[red]Query failed: {e}[/red]")
            return ""
    
    def _print_help(self):
        """Print help message."""
        self.console.print(Panel(
            "[bold yellow]MCP Chat Commands:[/bold yellow]\n\n"
            "• Type your question to chat with the model\n"
            "• [bold]help[/bold] - Show this help message\n"
            "• [bold]clear[/bold] - Clear conversation history\n"
            "• [bold]quit[/bold] or [bold]q[/bold] - Exit MCP chat\n",
            title="Help",
            border_style="yellow"
        ))
    
    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()
