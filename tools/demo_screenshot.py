"""Demo screenshot generator — renders simulated CLI output using Rich.

Run this script to see exactly what the toolkit looks like in the terminal.
Used to generate the README screenshot without an API key.
"""

import json
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import print as rprint

console = Console(width=90)

brief = json.loads(
    Path("examples/meridian_bank/outputs/01_account_brief.json").read_text()
)


def demo_account_intel():
    console.print()
    console.print(
        Panel(
            "[bold cyan]Account Intelligence[/bold cyan] — RAG + ChromaDB + OpenAI\n"
            "[dim]Retrieving industry context from vector store...[/dim]",
            style="cyan",
        )
    )
    time.sleep(0.4)

    console.print(
        Panel(
            f"[bold cyan]Account Brief — {brief['company']}[/bold cyan]\n"
            f"[dim]Industry: {brief['industry']} | AI Maturity: {brief['ai_maturity']}[/dim]",
            style="cyan",
        )
    )

    table = Table(title="Top AI Opportunities", show_lines=True, width=88)
    table.add_column("Use Case", style="bold white", min_width=28)
    table.add_column("Business Impact", min_width=26)
    table.add_column("Complexity", justify="center", min_width=10)
    table.add_column("Time to Value", justify="center", min_width=12)

    colors = {"Low": "green", "Medium": "yellow", "High": "red"}
    for opp in brief["ai_opportunities"]:
        c = colors.get(opp["complexity"], "white")
        table.add_row(
            opp["use_case"],
            opp["business_impact"][:55] + "…" if len(opp["business_impact"]) > 55 else opp["business_impact"],
            f"[{c}]{opp['complexity']}[/{c}]",
            opp["time_to_value"],
        )
    console.print(table)

    console.print(
        f"\n[green]✓[/green] Account Brief saved to [bold]output/meridian_bank_account.json[/bold]"
    )


def demo_eval():
    console.print()
    eval_result = json.loads(
        Path("examples/meridian_bank/outputs/04_eval_account_brief.json").read_text()
    )
    scores = eval_result["scores"]
    grade = eval_result["overall_grade"]
    overall = eval_result["overall_score"]

    console.print(
        Panel(
            f"[bold cyan]Grade: {grade}  |  Score: {overall}/10[/bold cyan]\n"
            "[dim]Production ready: ✓ Yes[/dim]",
            title="Eval — account-intel",
            style="cyan",
        )
    )

    table = Table(title="Dimension Scores", show_lines=True, width=88)
    table.add_column("Dimension", style="bold", min_width=22)
    table.add_column("Score", justify="center", min_width=10)
    table.add_column("Justification")

    justifications = eval_result["justifications"]
    dim_colors = {"completeness": "green", "accuracy": "cyan", "actionability": "green", "hallucination_risk": "yellow"}
    for dim, score in scores.items():
        color = "green" if score >= 7 else "yellow" if score >= 5 else "red"
        table.add_row(
            dim.replace("_", " ").title(),
            f"[{color}]{score}/10[/{color}]",
            justifications.get(dim, "")[:60] + "…" if len(justifications.get(dim, "")) > 60 else justifications.get(dim, ""),
        )
    console.print(table)
    console.print(f"\n[bold]Top strength:[/bold]    {eval_result['top_strength'][:70]}…")
    console.print(f"[bold]Top improvement:[/bold] {eval_result['top_improvement'][:70]}…")


def demo_metrics():
    console.print()
    table = Table(title="SE Toolkit — Observability Dashboard", show_lines=True, width=88)
    table.add_column("Module", style="bold", min_width=22)
    table.add_column("Runs", justify="right", min_width=6)
    table.add_column("Avg Latency", justify="right", min_width=12)
    table.add_column("Total Tokens", justify="right", min_width=14)
    table.add_column("Total Cost (USD)", justify="right", min_width=16)
    table.add_column("Errors", justify="right", min_width=8)

    rows = [
        ("solution-architect", "3", "42,180ms", "28,440", "$0.0284", "[green]0[/green]"),
        ("account-intel",      "8", " 6,320ms", "19,200", "$0.0096", "[green]0[/green]"),
        ("rfp-analyzer",       "2", "18,740ms", "31,100", "$0.0156", "[green]0[/green]"),
        ("proposal-writer",    "2", "24,300ms", "22,600", "$0.0113", "[green]0[/green]"),
        ("discovery",          "5", "12,600ms", "14,800", "$0.0074", "[red]1[/red]"),
        ("evals",              "8", " 4,100ms", " 9,600", "$0.0048", "[green]0[/green]"),
    ]
    for r in rows:
        table.add_row(*r)
    console.print(table)
    console.print("\n[bold]Total cost across all runs:[/bold] $0.0771 USD")


console.print()
console.rule("[bold cyan]$ python main.py account-intel 'Meridian Bank' --industry 'Financial Services'[/bold cyan]")
demo_account_intel()

console.print()
console.rule("[bold cyan]$ python main.py eval --module account-intel --input output/account.json[/bold cyan]")
demo_eval()

console.print()
console.rule("[bold cyan]$ python main.py metrics[/bold cyan]")
demo_metrics()
console.print()
