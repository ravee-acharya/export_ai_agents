"""
Prompt manager — loads and renders versioned prompt templates.

Why this exists:
  Previously every prompt was a hardcoded f-string inside an agent or
  orchestrator file. Changing a prompt required touching agent code,
  re-running tests, and re-deploying. Prompts are now in text files
  under prompts/ so they can be:
    - Edited without touching Python code
    - Versioned (prompts/v1/, prompts/v2/, etc.)
    - A/B tested by swapping the active version
    - Reviewed by non-engineers (product, domain experts)

Usage:
    from prompts.manager import render_prompt

    text = render_prompt("capability_gap", sector="textiles",
                         target_countries=["US", "DE"],
                         sme_certifications=["ISO 9001"],
                         all_requirements=["ISO 9001", "OEKO-TEX"])

Template syntax:
    Plain Python str.format_map() placeholders: {sector}, {query}, etc.
    Multi-line blocks use {context_block} where the caller provides a
    pre-formatted string (or "" to omit).

Versioning:
    PROMPT_VERSION env var (default "v1") selects the active version.
    Set PROMPT_VERSION=v2 in .env to switch all prompts at once, or
    override per-prompt by passing version= to render_prompt().
"""

import os
from pathlib import Path
from typing import Any

_PROMPTS_DIR = Path(__file__).parent
_DEFAULT_VERSION = os.environ.get("PROMPT_VERSION", "v1")


def render_prompt(
    name: str,
    version: str | None = None,
    **kwargs: Any,
) -> str:
    """
    Load and render a prompt template.

    Args:
        name:    Template name, e.g. "capability_gap" → loads
                 prompts/v1/capability_gap.txt
        version: Override the active version (default: PROMPT_VERSION env var)
        **kwargs: Template variables substituted via str.format_map()

    Returns:
        The rendered prompt string.

    Raises:
        FileNotFoundError: if the template file doesn't exist.
        KeyError: if a required template variable is missing.
    """
    v = version or _DEFAULT_VERSION
    path = _PROMPTS_DIR / v / f"{name}.txt"

    if not path.exists():
        raise FileNotFoundError(
            f"Prompt template not found: {path}\n"
            f"Available versions: {[d.name for d in _PROMPTS_DIR.iterdir() if d.is_dir()]}"
        )

    template = path.read_text(encoding="utf-8")

    try:
        return template.format_map(_SafeFormatMap(kwargs))
    except KeyError as e:
        raise KeyError(
            f"Missing variable {e} in prompt '{name}'. "
            f"Provided: {list(kwargs.keys())}"
        ) from e


class _SafeFormatMap(dict):
    """
    Allows prompts to contain literal curly braces (e.g. JSON schema
    examples) by leaving unrecognised {keys} unchanged rather than
    raising KeyError. Only keys explicitly passed as kwargs are
    substituted.
    """
    def __missing__(self, key):
        return "{" + key + "}"
