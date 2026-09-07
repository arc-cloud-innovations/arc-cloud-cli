"""The 'explain' command for ARC CLOUD CLI."""
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from arc_cloud.rules.registry import RuleRegistry

console = Console()
err_console = Console(stderr=True)


def explain_command(
    rule_id: Optional[str] = typer.Argument(
        None,
        help="The Rule ID to explain (e.g. ARC001). If omitted, lists all available rules.",
    ),
    list_rules: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List all available rules and descriptions.",
    ),
) -> None:
    """Explain a specific ARC CLOUD rule or list all registered rules."""
    registry = RuleRegistry()

    if not rule_id or list_rules:
        # Display list of rules
        table = Table(title="ARC CLOUD Static Analysis Rules", box=None, padding=(0, 2))
        table.add_column("Rule ID", style="bold cyan")
        table.add_column("Category", style="yellow")
        table.add_column("Default Severity", style="magenta")
        table.add_column("Title", style="white")

        for r in registry.get_all():
            table.add_row(r.rule_id, r.category.value, r.default_severity.value, r.title)

        console.print()
        console.print(table)
        console.print()
        console.print("Run [bold cyan]arc explain <RULE_ID>[/bold cyan] to see in-depth remediation guidance.")
        return

    rule = registry.get(rule_id)
    if not rule:
        err_console.print(f"[bold red]✗ Error:[/bold red] Unknown rule ID '{rule_id}'.")
        err_console.print("Available rules: " + ", ".join(r.rule_id for r in registry.get_all()))
        raise typer.Exit(code=2)

    console.print()
    console.rule(f"[bold cyan]ARC CLOUD Rule Explanation: {rule.rule_id}[/bold cyan]")
    console.print()

    # Rule metadata
    meta_table = Table.grid(padding=(0, 2))
    meta_table.add_column(style="bold white")
    meta_table.add_column()
    meta_table.add_row("Title:", f"[bold]{rule.title}[/bold]")
    meta_table.add_row("Category:", f"[yellow]{rule.category.value}[/yellow]")
    meta_table.add_row("Default Severity:", f"[magenta]{rule.default_severity.value}[/magenta]")
    console.print(Panel(meta_table, title="Rule Details", border_style="cyan"))
    console.print()

    # Description & Why It Matters
    console.print("[bold cyan]Description:[/bold cyan]")
    console.print(f"  {rule.description}\n")

    if rule.why_it_matters:
        console.print("[bold yellow]Why It Matters:[/bold yellow]")
        console.print(f"  {rule.why_it_matters}\n")

    # Recommendation
    console.print("[bold green]Recommendation & Remediation:[/bold green]")
    console.print(f"  {rule.recommendation}\n")

    # Examples
    if rule.example_bad:
        console.print("[bold red]Anti-Pattern Example:[/bold red]")
        console.print(Syntax(rule.example_bad, "python", theme="monokai", line_numbers=True))
        console.print()

    if rule.example_good:
        console.print("[bold green]Recommended Pattern Example:[/bold green]")
        console.print(Syntax(rule.example_good, "python", theme="monokai", line_numbers=True))
        console.print()
