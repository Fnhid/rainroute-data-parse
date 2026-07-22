from __future__ import annotations

import os
import sys
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(
    name="rainroute-data",
    help="RainRoute weather data pipeline.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def doctor() -> None:
    """Validate the local runtime and storage configuration."""
    root_value = os.environ.get("RAINROUTE_DATA_ROOT")

    console.print(f"Python: {sys.version.split()[0]}")

    if not root_value:
        console.print("[red]RAINROUTE_DATA_ROOT is not set.[/red]")
        raise typer.Exit(code=1)

    root = Path(root_value).expanduser().resolve()
    console.print(f"Data root: {root}")

    if not root.is_dir():
        console.print("[red]Data root does not exist.[/red]")
        raise typer.Exit(code=1)

    if not os.access(root, os.W_OK):
        console.print("[red]Data root is not writable.[/red]")
        raise typer.Exit(code=1)

    console.print("[green]Environment check passed.[/green]")


if __name__ == "__main__":
    app()
