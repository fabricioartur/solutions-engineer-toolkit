"""Solutions Engineer Toolkit — unified CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from tools.config import Config, ToolkitError

console = Console()


def _load_config() -> Config:
    try:
        return Config.load()
    except ToolkitError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        sys.exit(1)


def _write_output(data: dict | str, output_path: Path | None, label: str) -> None:
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = data if isinstance(data, str) else json.dumps(data, indent=2, ensure_ascii=False)
        output_path.write_text(content, encoding="utf-8")
        console.print(f"\n[green]✓[/green] {label} saved to [bold]{output_path}[/bold]")
    else:
        content = data if isinstance(data, str) else json.dumps(data, indent=2, ensure_ascii=False)
        console.print(content)


@click.group()
def cli() -> None:
    """Solutions Engineer Toolkit — AI-powered tools for enterprise pre-sales."""


@cli.command("account-intel")
@click.argument("company")
@click.option("--industry", default="Technology", show_default=True, help="Customer industry.")
@click.option("--output", default=None, type=click.Path(), help="Save output to file.")
def account_intel(company: str, industry: str, output: str | None) -> None:
    """Research a company and generate a pre-meeting account brief.

    Uses RAG + ChromaDB to enrich analysis with industry knowledge.

    \b
    Example:
      python main.py account-intel "Itaú Unibanco" --industry "Financial Services"
    """
    from tools.account_intelligence.agent import run

    config = _load_config()

    with console.status(f"[cyan]Researching {company} with RAG + OpenAI...[/cyan]"):
        result = run(company=company, industry=industry, config=config)

    console.print(Panel(
        f"[bold cyan]Account Brief — {company}[/bold cyan]\n"
        f"[dim]Industry: {industry} | AI Maturity: {result.get('ai_maturity', 'N/A')}[/dim]",
        style="cyan",
    ))

    table = Table(title="Top AI Opportunities", show_lines=True)
    table.add_column("Use Case", style="bold")
    table.add_column("Business Impact")
    table.add_column("Complexity")
    table.add_column("Time to Value")
    for opp in result.get("ai_opportunities", [])[:5]:
        table.add_row(
            opp.get("use_case", ""),
            opp.get("business_impact", ""),
            opp.get("complexity", ""),
            opp.get("time_to_value", ""),
        )
    console.print(table)

    out = Path(output) if output else None
    _write_output(result, out, "Account Brief")


@cli.command("discovery")
@click.option("--context", required=True, help="Brief customer context to start the session.")
@click.option("--output", default=None, type=click.Path(), help="Save summary to file.")
def discovery(context: str, output: str | None) -> None:
    """Run an interactive AI-powered discovery session.

    Uses LangGraph to maintain conversation state and adapt questions
    based on previous answers.

    \b
    Example:
      python main.py discovery --context "Bank with 50k employees evaluating AI"
    """
    from tools.discovery_agent.agent import run

    config = _load_config()

    console.print(Panel(
        "[bold cyan]Discovery Agent[/bold cyan] — powered by LangGraph\n"
        "[dim]Answer each question. The agent adapts based on your responses.[/dim]",
        style="cyan",
    ))

    result = run(context=context, config=config)

    console.print(Panel("[bold green]Discovery Complete[/bold green]", style="green"))

    out = Path(output) if output else None
    _write_output(result, out, "Discovery Summary")


@cli.command("rfp-analyze")
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option("--output", default=None, type=click.Path(), help="Save analysis to file.")
def rfp_analyze(pdf_path: str, output: str | None) -> None:
    """Analyze an RFP/RFI document using OpenAI Agents SDK with tool use.

    \b
    Example:
      python main.py rfp-analyze input/rfp.pdf --output output/rfp_analysis.json
    """
    from tools.rfp_analyzer.agent import run

    config = _load_config()

    with console.status("[cyan]Analyzing RFP with OpenAI Agents SDK + tool use...[/cyan]"):
        result = run(pdf_path=pdf_path, config=config)

    go_no_go = result.get("go_no_go", {})
    recommendation = go_no_go.get("recommendation", "N/A") if isinstance(go_no_go, dict) else "N/A"
    color = {"GO": "green", "CONDITIONAL GO": "yellow", "NO-GO": "red"}.get(recommendation, "white")

    console.print(Panel(
        f"[bold {color}]Recommendation: {recommendation}[/bold {color}]",
        title="RFP Analysis Complete",
        style=color,
    ))

    out = Path(output) if output else None
    _write_output(result, out, "RFP Analysis")


@cli.command("architect")
@click.option("--requirements", required=True, help="Customer requirements (text or file path).")
@click.option("--context", default="", help="Additional account context.")
@click.option("--output", default=None, type=click.Path(), help="Save recommendation to file.")
def architect(requirements: str, context: str, output: str | None) -> None:
    """Design a solution architecture using a CrewAI multi-agent crew.

    Three specialized agents collaborate: Researcher → Architect → Reviewer.

    \b
    Example:
      python main.py architect --requirements "RAG pipeline for 10M documents" \\
                               --context "Financial services, SOC2 required"
    """
    from tools.solution_architect.agent import run

    config = _load_config()

    req_text = requirements
    if Path(requirements).exists():
        req_text = Path(requirements).read_text(encoding="utf-8")

    console.print(Panel(
        "[bold cyan]Solution Architect Crew[/bold cyan]\n"
        "[dim]Researcher → Architect → Reviewer (CrewAI sequential process)[/dim]",
        style="cyan",
    ))

    with console.status("[cyan]Running CrewAI multi-agent crew...[/cyan]"):
        result = run(requirements=req_text, account_context=context, config=config)

    out = Path(output) if output else None
    _write_output(result, out, "Architecture Recommendation")


@cli.command("proposal")
@click.option("--account-brief", required=True, type=click.Path(exists=True), help="account-intel output JSON.")
@click.option("--discovery", "discovery_file", required=True, type=click.Path(exists=True), help="discovery output JSON.")
@click.option("--architecture", required=True, type=click.Path(exists=True), help="architect output JSON.")
@click.option("--go-no-go", "go_no_go_file", default=None, type=click.Path(), help="rfp-analyze output JSON (optional).")
@click.option("--output", default="output/proposal.md", type=click.Path(), help="Output file path.")
def proposal(
    account_brief: str,
    discovery_file: str,
    architecture: str,
    go_no_go_file: str | None,
    output: str,
) -> None:
    """Generate a full customer proposal using LangChain prompt chaining.

    Consolidates outputs from account-intel, discovery, architect, and
    optionally rfp-analyze into a polished Markdown proposal.

    \b
    Example:
      python main.py proposal \\
        --account-brief output/account.json \\
        --discovery output/discovery.json \\
        --architecture output/architecture.json \\
        --output output/proposal.md
    """
    from tools.proposal_writer.agent import run, to_markdown

    config = _load_config()

    brief = json.loads(Path(account_brief).read_text(encoding="utf-8"))
    disc = json.loads(Path(discovery_file).read_text(encoding="utf-8"))
    arch = json.loads(Path(architecture).read_text(encoding="utf-8"))
    gng = json.loads(Path(go_no_go_file).read_text(encoding="utf-8")) if go_no_go_file else {}

    console.print(Panel(
        "[bold cyan]Proposal Writer[/bold cyan]\n"
        "[dim]LangChain prompt chaining — 5 sections generated in sequence[/dim]",
        style="cyan",
    ))

    with console.status("[cyan]Generating proposal with LangChain...[/cyan]"):
        result = run(
            account_brief=brief,
            discovery_summary=disc,
            architecture=arch,
            go_no_go=gng,
            config=config,
        )

    md = to_markdown(result)
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")

    console.print(Panel(
        f"[bold green]✓ Proposal generated[/bold green]\n[dim]{out}[/dim]",
        style="green",
    ))
    console.print(Markdown(md[:2000] + "\n\n*[truncated — see full file]*"))


if __name__ == "__main__":
    cli()
