"""Configuration models and loader for CI Code Reviewer."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class FilterConfig(BaseModel):
    ignore_patterns: list[str] = Field(
        default_factory=lambda: [
            "**/*.lock",
            "**/pnpm-lock.yaml",
            "**/package-lock.json",
            "**/poetry.lock",
            "**/uv.lock",
            "**/dist/**",
            "**/build/**",
            "**/*.min.js",
            "**/*.min.css",
        ],
        description="Glob patterns of files to exclude from LLM review.",
    )
    max_diff_lines: int = Field(
        default=2500,
        description="Maximum diff line count to send in a single review context.",
    )


class RulesConfig(BaseModel):
    require_tests: bool = Field(default=True, description="Flag PRs missing test updates.")
    check_security: bool = Field(default=True, description="Run OWASP and secret leak checks.")
    check_architecture: bool = Field(
        default=True, description="Cross-reference docs/adr/ and architecture rules if present."
    )
    custom_guidelines: list[str] = Field(
        default_factory=list, description="Repo-specific review guidelines or style standards."
    )


class AuthConfig(BaseModel):
    provider: str = Field(
        default="litellm",
        description="Auth and provider engine: 'litellm', 'ollama', 'subscription_bridge'.",
    )
    model: str = Field(
        default="anthropic/claude-3-5-sonnet-20241022",
        description="Model name string passed to LiteLLM or backend provider.",
    )
    api_base: str | None = Field(
        default=None, description="Custom base URL (e.g., http://localhost:11434 for Ollama)."
    )
    api_key_env: str | None = Field(
        default=None, description="Custom environment variable name containing the API key."
    )


class ReviewerConfig(BaseModel):
    version: str = Field(default="1", description="Configuration schema version.")
    model: str = Field(
        default="anthropic/claude-3-5-sonnet-20241022",
        description="Default model name.",
    )
    filters: FilterConfig = Field(default_factory=FilterConfig)
    rules: RulesConfig = Field(default_factory=RulesConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)

    @classmethod
    def load(cls, path: str | Path | None = None) -> "ReviewerConfig":
        """Load configuration from .ci-reviewer.yml, falling back to defaults."""
        search_paths = [
            Path(path) if path else None,
            Path(".ci-reviewer.yml"),
            Path(".ci-reviewer.yaml"),
            Path(".github/ci-reviewer.yml"),
        ]
        for p in search_paths:
            if p and p.is_file():
                with open(p, encoding="utf-8") as f:
                    raw_data: dict[str, Any] = yaml.safe_load(f) or {}
                    return cls.model_validate(raw_data)
        return cls()
