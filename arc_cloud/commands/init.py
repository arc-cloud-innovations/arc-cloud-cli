"""The 'init' command for ARC CLOUD CLI."""
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console

from arc_cloud.core.config import ArcConfig

console = Console()
err_console = Console(stderr=True)


def init_command(
    path: Optional[str] = typer.Argument(
        None,
        help="Target directory to initialize .arccloud.yml (defaults to current working directory).",
        show_default=False,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing .arccloud.yml configuration file.",
    ),
) -> None:
    """Initialize ARC CLOUD configuration (.arccloud.yml) in a project."""
    target_dir = Path(path).resolve() if path else Path.cwd()

    if not target_dir.exists():
        err_console.print(f"[bold red]✗ Error:[/bold red] Target directory does not exist: {target_dir}")
        raise typer.Exit(code=2)

    if not target_dir.is_dir():
        err_console.print(f"[bold red]✗ Error:[/bold red] Target path is not a directory: {target_dir}")
        raise typer.Exit(code=2)

    config_file = target_dir / ".arccloud.yml"

    if config_file.exists() and not force:
        console.print(f"[yellow]Configuration file already exists:[/yellow] {config_file}")
        console.print("Use [cyan]--force[/cyan] to overwrite with defaults.")
        return

    try:
        yaml_content = ArcConfig.generate_default_yaml()
        config_file.write_text(yaml_content, encoding="utf-8")
        console.print(f"[bold green]✓ Initialized ARC CLOUD configuration:[/bold green] [cyan]{config_file}[/cyan]")
        console.print("You can now customize rules, complexity thresholds, and scan settings in this file.")
        console.print("Run [bold cyan]arc scan[/bold cyan] to analyze your project health.")
    except Exception as e:
        err_console.print(f"[bold red]✗ Error creating configuration:[/bold red] {e}")
        raise typer.Exit(code=3)
