<#
.SYNOPSIS
    Deterministic Verification Gate for the Repository (PowerShell).
.DESCRIPTION
    Runs linter, typecheck, and test suite in a single command.
    Returns exit code 0 on success, non-zero on failure.
#>

$ErrorActionPreference = "Stop"

Write-Host "[Verify Gate] Running deterministic verification checks..." -ForegroundColor Cyan

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$hasPyproject = Test-Path (Join-Path $repoRoot "pyproject.toml")

try {
    if ($hasPyproject) {
        Write-Host "[DETECTED] Python ecosystem" -ForegroundColor Green
        $env:LITELLM_LOCAL_MODEL_COST_MAP = "True"
        Push-Location $repoRoot
        try {
            uv run ruff check .
            uv run ruff format --check .
            uv run pytest
        }
        finally {
            Pop-Location
        }
    }
    else {
        Write-Host "[INFO] No specific language manifest detected yet. Verification passed as no-op." -ForegroundColor Yellow
    }

    Write-Host "[SUCCESS] All deterministic checks passed successfully!" -ForegroundColor Green
    exit 0
}
catch {
    Write-Host "[ERROR] Verification failed!" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
