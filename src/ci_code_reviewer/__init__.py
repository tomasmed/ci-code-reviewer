"""CI Code Reviewer - Open-source Agentic Code Reviewer for CI/CD."""

import os

# Prevent LiteLLM from making remote HTTP calls for cost maps on startup
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

__version__ = "0.1.0"
