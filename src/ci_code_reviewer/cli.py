"""CLI entrypoint for CI Code Reviewer."""

from pathlib import Path

import typer
from rich.console import Console

from ci_code_reviewer import __version__
from ci_code_reviewer.config import ReviewerConfig

app = typer.Typer(
    name="ci-code-reviewer",
    help="Agentic open-source code reviewer for CI/CD pipelines.",
)
console = Console()


@app.command()
def version() -> None:
    """Print the CI Code Reviewer version."""
    console.print(f"[bold green]ci-code-reviewer[/bold green] version: {__version__}")


@app.command()
def review(
    pr: int | None = typer.Option(None, "--pr", help="Pull Request number to review."),
    diff_file: Path | None = typer.Option(
        None, "--diff-file", help="Path to raw git diff file to review."
    ),
    config: Path | None = typer.Option(
        None, "--config", "-c", help="Path to .ci-reviewer.yml configuration file."
    ),
    model: str | None = typer.Option(
        None, "--model", "-m", help="Override LLM model name (passed to LiteLLM)."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Run review agent without publishing comments to GitHub."
    ),
) -> None:
    """Run an agentic code review on a git diff or GitHub PR."""
    cfg = ReviewerConfig.load(config)
    if model:
        cfg.model = model

    console.print(f"[cyan]Loaded configuration. Model: [bold]{cfg.model}[/bold][/cyan]")

    if diff_file and diff_file.is_file():
        diff_text = diff_file.read_text(encoding="utf-8")
        console.print(f"[green]Read diff from {diff_file} ({len(diff_text)} chars)[/green]")
    elif pr:
        console.print(f"[yellow]Pull Request #{pr} review requested. (Fetching PR diff)[/yellow]")
    else:
        console.print("[red]Error: Must specify either --pr <num> or --diff-file <path>[/red]")
        raise typer.Exit(code=1)

    console.print("[dim]Review agent workflow initialized...[/dim]")


def main() -> None:
    """Entry point for python console script."""
    app()


if __name__ == "__main__":
    main()
