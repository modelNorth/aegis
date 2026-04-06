"""Aegis CLI entry point."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from aegis.cli.commands import feedback, init, scan, session
from aegis.version import __version__

app = typer.Typer(
    name="aegis",
    help="🛡️  Aegis - Content Security with AI agents",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()

app.add_typer(init.app, name="init")
app.add_typer(scan.app, name="scan")
app.add_typer(session.app, name="session")
app.add_typer(feedback.app, name="feedback")


@app.command("serve")
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code changes"),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of worker processes"),
) -> None:
    """Start the Aegis API server."""
    import uvicorn

    console.print(f"[bold blue]🛡️  Starting Aegis API v{__version__}[/bold blue]")
    console.print(f"   Listening on [cyan]http://{host}:{port}[/cyan]")

    uvicorn.run(
        "aegis.api.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers if not reload else 1,
        log_level="info",
    )


@app.command("worker")
def run_worker() -> None:
    """Start the background job worker."""
    import asyncio

    console.print("[bold blue]🛡️  Starting Aegis Worker[/bold blue]")
    from aegis.queue.worker import run_worker as _run_worker
    asyncio.run(_run_worker())


@app.command("version")
def version() -> None:
    """Show Aegis version."""
    console.print(f"aegis-guard v{__version__}")


@app.command("job")
def get_job(job_id: str = typer.Argument(..., help="Job ID to check")) -> None:
    """Get the status and result of a scan job."""
    import httpx
    from aegis.cli.config import get_api_key, get_api_url
    from aegis.cli.commands.scan import _display_result

    api_url = get_api_url()
    api_key = get_api_key()

    if not api_key:
        console.print("[red]No API key configured. Run 'aegis init' first.[/red]")
        raise typer.Exit(1)

    try:
        response = httpx.get(
            f"{api_url}/v1/scan/{job_id}",
            headers={"X-API-Key": api_key},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        status = data.get("status", "unknown")
        console.print(f"Job [cyan]{job_id}[/cyan]: [bold]{status}[/bold]")

        if data.get("result"):
            _display_result(data["result"], False)
        elif data.get("error"):
            console.print(f"[red]Error: {data['error']}[/red]")
    except Exception as exc:
        console.print(f"[red]Failed: {exc}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
