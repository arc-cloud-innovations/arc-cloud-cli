"""The 'version' command for ARC CLOUD CLI."""
import platform
import sys
from rich.console import Console
from rich.table import Table

from arc_cloud import __app_name__, __version__
from arc_cloud.engines import (
    CodeQualityEngine,
    SecurityEngine,
    DependencyEngine,
    ArchitectureEngine,
    TechnicalDebtEngine,
)

console = Console()


def version_command() -> None:
    """Show detailed ARC CLOUD platform and engine version information."""
    console.print()
    console.rule("[bold cyan]ARC CLOUD Platform Architecture[/bold cyan]")
    console.print()

    # Core metadata
    core_table = Table.grid(padding=(0, 2))
    core_table.add_column(style="bold white")
    core_table.add_column(style="cyan")
    core_table.add_row("CLI Version:", f"[bold green]{__version__}[/bold green]")
    core_table.add_row("Python Version:", sys.version.split()[0])
    core_table.add_row("Platform:", f"{platform.system()} {platform.release()} ({platform.machine()})")
    console.print(core_table)
    console.print()

    # Engine status
    engines_table = Table(title="Engineering Health Engines", box=None, padding=(0, 2))
    engines_table.add_column("Engine", style="bold white")
    engines_table.add_column("Version", style="dim")
    engines_table.add_column("Status", style="bold")

    engines = [
        (CodeQualityEngine.name, "1.0.0", "[green]Active (Local AST)[/green]"),
        (SecurityEngine.name, "0.1.0", "[dim]Planned (v0.2.0)[/dim]"),
        (DependencyEngine.name, "0.1.0", "[dim]Planned (v0.2.0)[/dim]"),
        (ArchitectureEngine.name, "0.1.0", "[dim]Planned (v0.3.0)[/dim]"),
        (TechnicalDebtEngine.name, "0.1.0", "[dim]Planned (v0.3.0)[/dim]"),
    ]

    for name, ver, status in engines:
        engines_table.add_row(name, ver, status)

    console.print(engines_table)
    console.print()
