"""The 'scan' command for ARC CLOUD CLI."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from arc_cloud.blueprint.generator import BlueprintGenerator
from arc_cloud.blueprint.models import Blueprint
from arc_cloud.scanner.engine import ScannerEngine

console = Console()
err_console = Console(stderr=True)


def scan_command(
    path: Optional[str] = typer.Argument(
        None,
        help="Path to the software project to analyze (defaults to current working directory).",
        show_default=False,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output the normalized Software Blueprint as raw JSON to stdout.",
    ),
    output_file: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Save the normalized Software Blueprint JSON to a specified file.",
    ),
    max_files: int = typer.Option(
        20_000,
        "--max-files",
        help="Maximum number of files to inspect before stopping.",
    ),
    max_depth: int = typer.Option(
        20,
        "--max-depth",
        help="Maximum directory recursion depth to traverse.",
    ),
) -> None:
    """Analyze a software project statically and generate a Software Blueprint."""
    target_path = Path(path).resolve() if path else Path.cwd()

    # Pre-flight path validations
    if not target_path.exists():
        err_console.print(f"[bold red]✗ Error:[/bold red] Project path does not exist: '{target_path}'")
        raise typer.Exit(code=1)

    if not target_path.is_dir():
        err_console.print(f"[bold red]✗ Error:[/bold red] Project path is not a directory: '{target_path}'")
        raise typer.Exit(code=1)

    engine = ScannerEngine(max_files=max_files, max_depth=max_depth)

    try:
        blueprint = engine.scan(target_path)
    except PermissionError as exc:
        err_console.print(f"[bold red]✗ Permission Error:[/bold red] Unable to read project directory: {exc}")
        raise typer.Exit(code=1)
    except Exception as exc:
        err_console.print(f"[bold red]✗ Scan Failed:[/bold red] An unexpected error occurred: {exc}")
        raise typer.Exit(code=1)

    # Save to file if requested
    if output_file:
        try:
            saved_path = BlueprintGenerator.save_to_file(blueprint, output_file)
            if not json_output:
                console.print(f"[bold green]✓[/bold green] Blueprint written to [cyan]{output_file}[/cyan]\n")
        except Exception as exc:
            err_console.print(f"[bold red]✗ Error saving blueprint:[/bold red] {exc}")
            raise typer.Exit(code=1)

    # Handle raw JSON output
    if json_output:
        print(BlueprintGenerator.to_json(blueprint))
        return

    # Render professional Rich Terminal UI
    _render_rich_report(blueprint)


def _render_rich_report(blueprint: Blueprint) -> None:
    """Renders the Software X-Ray report using Rich."""
    console.print()
    console.rule("[bold cyan]ARC CLOUD SOFTWARE X-RAY[/bold cyan]", style="cyan")
    console.print()

    # 1. Project Summary
    summary_table = Table(box=None, show_header=False, padding=(0, 2))
    summary_table.add_column("Key", style="bold white", width=12)
    summary_table.add_column("Value", style="cyan")
    summary_table.add_row("Name:", f"[bold white]{blueprint.project.name}[/bold white]")
    summary_table.add_row("Type:", f"[bold green]{blueprint.project.type.value}[/bold green]")
    summary_table.add_row("Files:", f"{blueprint.scanner.files_scanned:,}")
    if blueprint.scanner.duration_seconds > 0:
        summary_table.add_row("Duration:", f"{blueprint.scanner.duration_seconds:.2f}s")
    console.print(Panel(summary_table, title="[bold]Project Summary[/bold]", border_style="dim"))

    # 2. Languages & Frameworks Side-by-Side or Sequential
    lang_table = Table(title="Languages", title_style="bold magenta", box=None, padding=(0, 2))
    lang_table.add_column("Language", style="bold")
    lang_table.add_column("Files", justify="right", style="dim")
    lang_table.add_column("Share", justify="right", style="magenta")

    if blueprint.languages:
        for lang in blueprint.languages[:7]:  # Top 7 languages
            lang_table.add_row(lang.name, str(lang.files), f"{lang.percentage}%")
    else:
        lang_table.add_row("[dim]None detected[/dim]", "-", "-")

    console.print(lang_table)
    console.print()

    # 3. Frameworks & Platforms
    fw_plat_table = Table(box=None, show_header=False, padding=(0, 2))
    fw_plat_table.add_column("Category", style="bold yellow", width=14)
    fw_plat_table.add_column("Details", style="white")

    if blueprint.frameworks:
        fw_list = ", ".join(f"{f.name}" + (f" ({f.version})" if f.version else "") for f in blueprint.frameworks)
        fw_plat_table.add_row("Frameworks:", fw_list)
    else:
        fw_plat_table.add_row("Frameworks:", "[dim]None detected[/dim]")

    if blueprint.platforms:
        plat_list = ", ".join(p.name.value for p in blueprint.platforms)
        fw_plat_table.add_row("Platforms:", plat_list)
    else:
        fw_plat_table.add_row("Platforms:", "[dim]Generic / Agnostic[/dim]")

    dep_count = len(blueprint.dependencies)
    fw_plat_table.add_row("Dependencies:", f"[bold]{dep_count}[/bold] identified")

    console.print(Panel(fw_plat_table, title="[bold]Ecosystem & Stack[/bold]", border_style="dim"))

    # 4. Structure Areas
    if blueprint.structure.areas:
        struct_table = Table(title="Structure Classification", title_style="bold blue", box=None, padding=(0, 2))
        struct_table.add_column("Area", style="bold")
        struct_table.add_column("Directories", style="dim")
        for area in blueprint.structure.areas:
            display_paths = ", ".join(area.paths[:4])
            if len(area.paths) > 4:
                display_paths += f" (+{len(area.paths) - 4} more)"
            struct_table.add_row(area.name.capitalize(), display_paths)
        console.print(struct_table)
        console.print()

    # 5. Architecture Summary
    if blueprint.architecture.patterns:
        arch_text = Text(", ".join(blueprint.architecture.patterns), style="green")
        console.print(f"[bold]Architecture Patterns:[/bold] {arch_text}\n")

    # 6. Warnings
    if blueprint.warnings:
        console.print("[bold yellow]Warnings:[/bold yellow]")
        for warn in blueprint.warnings:
            console.print(f"  [yellow]{warn}[/yellow]")
        console.print()

    # Footer rule
    console.rule(
        f"[bold green]✓ Scan completed in {blueprint.scanner.duration_seconds:.2f} seconds[/bold green]",
        style="green",
    )
    console.print()
