"""CLI entrypoint for CI Code Reviewer."""

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ci_code_reviewer import __version__
from ci_code_reviewer.config import ReviewerConfig
from ci_code_reviewer.context.blast_radius import (
    extract_modified_symbols,
    find_downstream_references,
    format_blast_radius_context,
)
from ci_code_reviewer.harness.factory import get_harness
from ci_code_reviewer.integrations.github import GitHubClient
from ci_code_reviewer.lenses import extract_touched_files

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
    harness: str | None = typer.Option(
        None,
        "--harness",
        help="Review harness to use: 'native', 'strands' (AWS Strands), or 'maf' (Microsoft Agent Framework).",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Run review agent without publishing comments to GitHub."
    ),
    emit_vote: bool = typer.Option(
        False,
        "--emit-vote",
        help="Allow agent to cast official PR review vote (APPROVE / REQUEST_CHANGES).",
    ),
    repo: str | None = typer.Option(
        None,
        "--repo",
        help="GitHub repository in owner/repo format (defaults to GITHUB_REPOSITORY env var).",
    ),
) -> None:
    """Run an agentic code review on a git diff or GitHub PR."""
    cfg = ReviewerConfig.load(config)
    if model:
        cfg.model = model
    if harness:
        cfg.harness = harness
    if emit_vote:
        cfg.voting.enabled = True

    console.print(
        f"[cyan]Loaded configuration. Model: [bold]{cfg.model}[/bold] | Harness: [bold]{cfg.harness}[/bold][/cyan]"
    )

    commit_sha = "local-head"
    repository = repo or os.getenv("GITHUB_REPOSITORY", "")
    gh_client: GitHubClient | None = None

    if diff_file and diff_file.is_file():
        diff_text = diff_file.read_text(encoding="utf-8")
        console.print(f"[green]Read diff from {diff_file} ({len(diff_text)} chars)[/green]")
    elif pr:
        console.print(f"[yellow]Pull Request #{pr} review requested. Resolving PR data...[/yellow]")
        gh_client = GitHubClient()
        if not repository:
            console.print(
                "[red]Error: Must specify --repo or set GITHUB_REPOSITORY for PR review.[/red]"
            )
            raise typer.Exit(code=1)

        try:
            pr_info = gh_client.get_pr_info(repository, pr)
            commit_sha = pr_info["head_sha"]
            diff_text = gh_client.get_pr_diff(repository, pr)
            console.print(
                f"[green]Fetched diff for PR #{pr} ({len(diff_text)} chars, commit: {commit_sha[:8]})[/green]"
            )
        except Exception as e:
            console.print(f"[red]Failed to retrieve PR #{pr} from GitHub: {e}[/red]")
            raise typer.Exit(code=1) from e
    else:
        console.print("[red]Error: Must specify either --pr <num> or --diff-file <path>[/red]")
        raise typer.Exit(code=1)

    # Downstream blast radius analysis across local workspace
    touched_files = extract_touched_files(diff_text)
    modified_symbols = extract_modified_symbols(diff_text)
    blast_refs = find_downstream_references(
        symbols=modified_symbols,
        workspace_root=Path.cwd(),
        exclude_files=touched_files,
        ignore_patterns=cfg.filters.ignore_patterns,
    )
    blast_radius_context = format_blast_radius_context(blast_refs)
    if blast_refs:
        console.print(
            f"[yellow]Identified {len(blast_refs)} modified symbol(s) with downstream workspace references.[/yellow]"
        )

    # Harness turn execution
    try:
        active_harness = get_harness(cfg.harness)
    except Exception as e:
        console.print(f"[red]Error initializing harness '{cfg.harness}': {e}[/red]")
        raise typer.Exit(code=1) from e

    console.print(
        f"[cyan]Executing review across configured lenses using harness '{active_harness.name}'...[/cyan]"
    )
    assessment = active_harness.review(
        diff=diff_text,
        context=blast_radius_context,
        config=cfg,
    )

    # Console output rendering
    console.print(
        Panel(
            f"[bold]Verdict:[/bold] {assessment.recommendation.value}\n\n{assessment.summary}",
            title="[bold green]Review Assessment[/bold green]",
            subtitle=f"Harness: {active_harness.name}",
        )
    )

    if assessment.critical_findings or assessment.suggestions:
        table = Table(title="Review Findings by Lens")
        table.add_column("Severity", style="bold")
        table.add_column("Lens")
        table.add_column("Location")
        table.add_column("Issue")

        for f in assessment.critical_findings:
            loc = f"{f.file_path}:{f.line_number}" if f.line_number else f.file_path
            table.add_row("[red]BLOCKER[/red]", f.lens or "-", loc, f.title)

        for f in assessment.suggestions:
            loc = f"{f.file_path}:{f.line_number}" if f.line_number else f.file_path
            table.add_row("[yellow]SUGGESTION[/yellow]", f.lens or "-", loc, f.title)

        console.print(table)

    # Publishing
    if dry_run:
        console.print("[yellow]DRY RUN MODE: Skipping GitHub review publishing.[/yellow]")
    elif pr and repository and gh_client:
        console.print(f"[cyan]Publishing review to {repository} PR #{pr}...[/cyan]")
        try:
            gh_client.post_review(
                repo=repository,
                pr_number=pr,
                commit_sha=commit_sha,
                assessment=assessment,
                voting=cfg.voting,
                blast_radius_context=blast_radius_context,
            )
            console.print("[bold green]Successfully published review to GitHub![/bold green]")
        except Exception as e:
            console.print(f"[red]Failed to publish review to GitHub: {e}[/red]")
            raise typer.Exit(code=1) from e

    # Check for blocking failure exit code
    if assessment.critical_findings:
        raise typer.Exit(code=1)


def main() -> None:
    """Entry point for python console script."""
    app()


if __name__ == "__main__":
    main()
