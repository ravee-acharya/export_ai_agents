"""
LLM provider factory.

A single place to swap the underlying LLM the orchestrator uses.
The orchestrator and synthesize nodes just call get_llm() — they never
import a provider directly, so switching from Anthropic to Gemini (or
any other provider) requires changing nothing else.

Supported providers
-------------------
  anthropic   Claude Sonnet (default) — needs ANTHROPIC_API_KEY
  gemini      Gemini 2.5 Flash        — needs GEMINI_API_KEY (free tier is generous)
  ollama      Llama 3.1 local         — needs Ollama running on your machine, no key
  openrouter  Any free model          — needs OPENROUTER_API_KEY (free tier available)

Usage
-----
  # use default from env / CLI flag
  llm = get_llm()

  # override explicitly (e.g. from run_demo.py --llm gemini)
  llm = get_llm("gemini")

Environment variables
---------------------
  ANTHROPIC_API_KEY   — for provider "anthropic"
  GEMINI_API_KEY      — for provider "gemini"
  OPENROUTER_API_KEY  — for provider "openrouter"
  OLLAMA_BASE_URL     — optional override, defaults to http://localhost:11434
  EXPORT_AI_LLM       — set this to make a provider the default without
                        passing --llm every time, e.g.:
                        export EXPORT_AI_LLM=gemini
"""

import os
from typing import Literal

ProviderName = Literal["anthropic", "gemini", "ollama", "openrouter"]

# Free/generous-tier model names per provider.
# Change these if you want a different model from the same provider.
_MODELS: dict[str, str] = {
    "anthropic":  "claude-sonnet-4-6",
    "gemini":     "gemini-2.5-flash",
    "ollama":     "llama3.1",           # must be pulled: ollama pull llama3.1
    "openrouter": "meta-llama/llama-3.1-8b-instruct:free",
}

_MAX_TOKENS = 1000


def get_llm(provider: str | None = None):
    """
    Return a LangChain chat model for the given provider.
    Falls back to the EXPORT_AI_LLM env var, then "anthropic".
    """
    if provider is None:
        provider = os.environ.get("EXPORT_AI_LLM", "anthropic")

    provider = provider.lower().strip()

    if provider == "anthropic":
        return _anthropic()
    elif provider == "gemini":
        return _gemini()
    elif provider == "ollama":
        return _ollama()
    elif provider == "openrouter":
        return _openrouter()
    else:
        raise ValueError(
            f"Unknown provider: '{provider}'. "
            "Choose: anthropic | gemini | ollama | openrouter"
        )


def _anthropic():
    _require_key("ANTHROPIC_API_KEY", "anthropic")
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(
        model=_MODELS["anthropic"],
        max_tokens=_MAX_TOKENS,
    )


def _gemini():
    _require_key("GEMINI_API_KEY", "gemini")
    # langchain-google-genai checks GOOGLE_API_KEY first, GEMINI_API_KEY second.
    # Set both so it works regardless of package version.
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=_MODELS["gemini"],
        max_output_tokens=_MAX_TOKENS,
    )


def _ollama():
    from langchain_ollama import ChatOllama
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    return ChatOllama(
        model=_MODELS["ollama"],
        base_url=base_url,
        num_predict=_MAX_TOKENS,
    )


def _openrouter():
    _require_key("OPENROUTER_API_KEY", "openrouter")
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=_MODELS["openrouter"],
        openai_api_key=os.environ["OPENROUTER_API_KEY"],
        openai_api_base="https://openrouter.ai/api/v1",
        max_tokens=_MAX_TOKENS,
        default_headers={
            # OpenRouter uses these for analytics / rate-limit buckets.
            # Optional but good practice.
            "HTTP-Referer": "https://exportai.in",
            "X-Title": "ExportAI SME Tool",
        },
    )


def _require_key(env_var: str, provider: str) -> None:
    if not os.environ.get(env_var):
        raise EnvironmentError(
            f"\n\nProvider '{provider}' needs {env_var} to be set.\n"
            f"  Mac/Linux:  export {env_var}=your-key-here\n"
            f"  Windows:    set {env_var}=your-key-here\n"
        )
