"""Version checking for BabaYaga."""
import httpx
from rich.console import Console
from ... import __version__

async def check_for_updates(console: Console):
    """Check for updates to the BabaYaga package."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://pypi.org/pypi/babayaga/json")
            if response.status_code == 200:
                latest_version = response.json()["info"]["version"]
                if latest_version > __version__:
                    console.print(f"[yellow]A new version of BabaYaga is available: {latest_version}[/yellow]")
                    console.print("[yellow]Upgrade with: pip install --upgrade babayaga[/yellow]")
    except Exception:
        pass  # Ignore errors

