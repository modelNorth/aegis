"""CLI init command - configure Aegis connection settings."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.prompt import Prompt

from aegis.cli.config import get_api_key, get_api_url, save_cli_config

app = typer.Typer(help="Initialize Aegis CLI configuration")
console = Console()


@app.callback(invoke_without_command=True)
def init(
    api_url: str | None = typer.Option(None, "--api-url", "-u", help="Aegis API URL"),
    api_key: str | None = typer.Option(None, "--api-key", "-k", help="API key"),
    non_interactive: bool = typer.Option(False, "--non-interactive", "-n", help="Skip prompts"),
) -> None:
    """Initialize Aegis CLI with API URL and key."""
    console.print("[bold blue]🛡️  Aegis CLI Configuration[/bold blue]")
    console.print()

    current_url = get_api_url()
    current_key = get_api_key()

    if non_interactive:
        final_url = api_url or current_url
        final_key = api_key or current_key or ""
    else:
        final_url = api_url or Prompt.ask(
            "API URL",
            default=current_url,
            console=console,
        )
        final_key = api_key or Prompt.ask(
            "API Key",
            default=current_key or "",
            password=True,
            console=console,
        )

    config = {"api_url": final_url, "api_key": final_key}
    save_cli_config(config)

    console.print()
    console.print(f"[green]✓[/green] Configuration saved")
    console.print(f"  API URL: [cyan]{final_url}[/cyan]")
    console.print(f"  API Key: [cyan]{'*' * 8 + final_key[-4:] if len(final_key) > 4 else '(not set)'}[/cyan]")

    if final_url and final_key:
        console.print()
        console.print("[dim]Testing connection...[/dim]")
        try:
            import httpx
            response = httpx.get(f"{final_url}/health", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                console.print(f"[green]✓ Connected[/green] - Aegis v{data.get('version', '?')}")
            else:
                console.print(f"[yellow]⚠ Server returned {response.status_code}[/yellow]")
        except Exception as exc:
            console.print(f"[yellow]⚠ Could not connect: {exc}[/yellow]")
