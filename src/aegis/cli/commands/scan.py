"""CLI scan command - scan content for prompt injection."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aegis.cli.config import get_api_key, get_api_url
from aegis.core.constants import ContentType, RiskLevel

app = typer.Typer(help="Scan content for prompt injection")
console = Console()

RISK_COLORS: dict[str, str] = {
    RiskLevel.SAFE: "green",
    RiskLevel.LOW: "yellow",
    RiskLevel.MEDIUM: "orange3",
    RiskLevel.HIGH: "red",
    RiskLevel.CRITICAL: "bold red",
}


@app.callback(invoke_without_command=True)
def scan(
    content: Optional[str] = typer.Argument(None, help="Content to scan (or use --file)"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File to scan"),
    content_type: ContentType = typer.Option(ContentType.TEXT, "--type", "-t", help="Content type"),
    session_id: Optional[str] = typer.Option(None, "--session", "-s", help="Session ID"),
    sync: bool = typer.Option(True, "--sync/--async", help="Wait for result"),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    local: bool = typer.Option(False, "--local", "-l", help="Scan locally without API"),
) -> None:
    """Scan content for prompt injection attacks."""
    text = _get_content(content, file)
    if not text:
        console.print("[red]Error: provide content as argument or --file[/red]")
        raise typer.Exit(1)

    if local:
        _scan_local(text, content_type, session_id, output_json)
    else:
        _scan_api(text, content_type, session_id, sync, output_json)


def _get_content(content: str | None, file: Path | None) -> str:
    if file:
        try:
            if content_type_from_file(file) in (ContentType.PDF, ContentType.IMAGE):
                import base64
                return base64.b64encode(file.read_bytes()).decode()
            return file.read_text(encoding="utf-8")
        except Exception as exc:
            console.print(f"[red]Error reading file: {exc}[/red]")
            raise typer.Exit(1)
    if content:
        return content
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def content_type_from_file(path: Path) -> ContentType:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return ContentType.PDF
    if suffix in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"):
        return ContentType.IMAGE
    if suffix in (".html", ".htm"):
        return ContentType.HTML
    return ContentType.TEXT


def _scan_local(text: str, content_type: ContentType, session_id: str | None, output_json: bool) -> None:
    console.print("[dim]Running local scan...[/dim]")
    try:
        from aegis.agents.crew import AegisCrew
        from aegis.core.models import ScanRequest
        crew = AegisCrew(enable_memory=False)
        request = ScanRequest(content=text, content_type=content_type, session_id=session_id)
        result = crew.scan(request)
        _display_result(result.model_dump(mode="json"), output_json)
    except Exception as exc:
        console.print(f"[red]Local scan failed: {exc}[/red]")
        raise typer.Exit(1)


def _scan_api(text: str, content_type: ContentType, session_id: str | None, sync: bool, output_json: bool) -> None:
    import httpx

    api_url = get_api_url()
    api_key = get_api_key()

    if not api_key:
        console.print("[red]No API key configured. Run 'aegis init' first.[/red]")
        raise typer.Exit(1)

    payload = {
        "content": text,
        "content_type": content_type.value,
        "session_id": session_id,
        "sync": sync,
    }

    try:
        with console.status("[dim]Scanning...[/dim]"):
            response = httpx.post(
                f"{api_url}/v1/scan",
                json=payload,
                headers={"X-API-Key": api_key},
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

        if sync and data.get("result"):
            _display_result(data["result"], output_json)
        else:
            job_id = data["job_id"]
            console.print(f"[green]Job submitted:[/green] {job_id}")
            if not sync:
                console.print(f"[dim]Check status: aegis job {job_id}[/dim]")

    except httpx.HTTPStatusError as exc:
        console.print(f"[red]API error {exc.response.status_code}: {exc.response.text}[/red]")
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"[red]Scan failed: {exc}[/red]")
        raise typer.Exit(1)


def _display_result(result: dict, output_json: bool) -> None:
    if output_json:
        import json
        console.print(json.dumps(result, indent=2, default=str))
        return

    risk_level = result.get("risk_level", "safe")
    color = RISK_COLORS.get(risk_level, "white")
    is_injection = result.get("is_injection", False)
    score = result.get("risk_score", 0.0)
    confidence = result.get("confidence", 0.0)

    verdict_icon = "🚨" if is_injection else "✅"
    panel_text = (
        f"[bold {color}]{verdict_icon} {risk_level.upper()}[/bold {color}]\n\n"
        f"Score: [bold]{score:.3f}[/bold] | Confidence: [bold]{confidence:.3f}[/bold]\n"
        f"Injection detected: [bold {'red' if is_injection else 'green'}]{is_injection}[/bold]\n\n"
        f"{result.get('summary', '')}"
    )
    console.print(Panel(panel_text, title="[bold]Scan Result[/bold]", border_style=color))

    findings = result.get("findings", [])
    if findings:
        table = Table(title="Agent Findings", show_lines=True)
        table.add_column("Agent", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Signals", style="dim")
        for f in findings:
            agent_score = f.get("score", 0.0)
            score_color = "red" if agent_score >= 0.7 else "yellow" if agent_score >= 0.4 else "green"
            signals = ", ".join(f.get("signals", [])[:3])
            table.add_row(
                f.get("agent", "?"),
                f"[{score_color}]{agent_score:.3f}[/{score_color}]",
                signals or "[dim]none[/dim]",
            )
        console.print(table)
