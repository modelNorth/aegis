"""CLI feedback command - submit feedback for scan results."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from aegis.cli.config import get_api_key, get_api_url
from aegis.core.constants import RiskLevel

app = typer.Typer(help="Submit feedback for scan results")
console = Console()


@app.callback(invoke_without_command=True)
def feedback(
    job_id: str = typer.Argument(..., help="Job ID to provide feedback for"),
    correct: bool = typer.Option(..., "--correct/--incorrect", help="Was the verdict correct?"),
    actual_risk: Optional[RiskLevel] = typer.Option(None, "--actual-risk", "-r", help="Actual risk level if wrong"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Optional notes"),
) -> None:
    """Submit feedback for a completed scan."""
    import httpx

    api_url = get_api_url()
    api_key = get_api_key()

    if not api_key:
        console.print("[red]No API key configured. Run 'aegis init' first.[/red]")
        raise typer.Exit(1)

    payload: dict = {
        "job_id": job_id,
        "is_correct": correct,
        "notes": notes,
    }
    if actual_risk:
        payload["actual_risk_level"] = actual_risk.value

    try:
        response = httpx.post(
            f"{api_url}/v1/feedback",
            json=payload,
            headers={"X-API-Key": api_key},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        console.print(f"[green]✓[/green] {data.get('message', 'Feedback recorded')}")
        console.print(f"Feedback ID: [cyan]{data.get('feedback_id')}[/cyan]")
    except Exception as exc:
        console.print(f"[red]Failed: {exc}[/red]")
        raise typer.Exit(1)
