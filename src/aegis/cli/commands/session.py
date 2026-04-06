"""CLI session management commands."""

from __future__ import annotations

import typer
from rich.console import Console

from aegis.cli.config import get_api_key, get_api_url

app = typer.Typer(help="Manage scanning sessions")
console = Console()


@app.command("create")
def create_session(
    user_id: str | None = typer.Option(None, "--user-id", "-u", help="User ID for session"),
) -> None:
    """Create a new scanning session."""
    import httpx

    api_url = get_api_url()
    api_key = get_api_key()

    if not api_key:
        console.print("[red]No API key configured. Run 'aegis init' first.[/red]")
        raise typer.Exit(1)

    try:
        response = httpx.post(
            f"{api_url}/v1/sessions",
            json={"user_id": user_id},
            headers={"X-API-Key": api_key},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        console.print(f"[green]Session created:[/green] {data['session_id']}")
    except Exception as exc:
        console.print(f"[red]Failed: {exc}[/red]")
        raise typer.Exit(1)


@app.command("get")
def get_session(session_id: str = typer.Argument(..., help="Session ID")) -> None:
    """Get session information."""
    import httpx

    api_url = get_api_url()
    api_key = get_api_key()

    if not api_key:
        console.print("[red]No API key configured. Run 'aegis init' first.[/red]")
        raise typer.Exit(1)

    try:
        response = httpx.get(
            f"{api_url}/v1/sessions/{session_id}",
            headers={"X-API-Key": api_key},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        console.print(f"[bold]Session:[/bold] {data['session_id']}")
        console.print(f"User ID: {data.get('user_id', 'N/A')}")
        console.print(f"Created: {data['created_at']}")
        console.print(f"Scan count: {data.get('scan_count', 0)}")
    except Exception as exc:
        console.print(f"[red]Failed: {exc}[/red]")
        raise typer.Exit(1)


@app.command("delete")
def delete_session(
    session_id: str = typer.Argument(..., help="Session ID"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a session."""
    if not confirm:
        typer.confirm(f"Delete session {session_id}?", abort=True)

    import httpx

    api_url = get_api_url()
    api_key = get_api_key()

    if not api_key:
        console.print("[red]No API key configured. Run 'aegis init' first.[/red]")
        raise typer.Exit(1)

    try:
        response = httpx.delete(
            f"{api_url}/v1/sessions/{session_id}",
            headers={"X-API-Key": api_key},
            timeout=10.0,
        )
        response.raise_for_status()
        console.print(f"[green]Session {session_id} deleted.[/green]")
    except Exception as exc:
        console.print(f"[red]Failed: {exc}[/red]")
        raise typer.Exit(1)
