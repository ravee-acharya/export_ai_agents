"""
LLM provider factory.

For Gemini, bypasses langchain-google-genai entirely and calls the
Gemini REST API directly using the requests library. This avoids all
SDK authentication issues with AQ. prefixed keys, which require the
x-goog-api-key header and do NOT work through the langchain SDK's
default gRPC transport regardless of the transport= parameter.
"""

import os
from typing import Any

_MAX_TOKENS = 1000

_MODELS = {
    "anthropic":  "claude-sonnet-4-6",
    "gemini":     "gemini-2.5-flash",
    "ollama":     "llama3.1",
    "openrouter": "meta-llama/llama-3.1-8b-instruct:free",
}


def get_llm(provider: str | None = None):
    if provider is None:
        provider = os.environ.get("EXPORT_AI_LLM", "anthropic")
    provider = provider.lower().strip()

    if provider == "anthropic":
        return _anthropic()
    elif provider == "gemini":
        return _gemini_direct()
    elif provider == "ollama":
        return _ollama()
    elif provider == "openrouter":
        return _openrouter()
    else:
        raise ValueError(f"Unknown provider: '{provider}'")


def _anthropic():
    _require_key("ANTHROPIC_API_KEY", "anthropic")
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(model=_MODELS["anthropic"], max_tokens=_MAX_TOKENS)


def _gemini_direct():
    """
    Calls Gemini REST API directly — no langchain-google-genai SDK.
    Works with both AIza... and AQ. prefixed keys.
    Returns a LangChain-compatible wrapper so the rest of the app
    (which calls llm.invoke(prompt)) works without any changes.
    """
    _require_key("GEMINI_API_KEY", "gemini")
    key = os.environ["GEMINI_API_KEY"]
    return _GeminiDirectLLM(api_key=key, model=_MODELS["gemini"])


class _GeminiDirectLLM:
    """
    Minimal LangChain-compatible wrapper around the Gemini REST API.
    Implements only .invoke(prompt_or_message) which is all ExportAI uses.
    """

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model
        self._url = (
            f"https://generativelanguage.googleapis.com"
            f"/v1beta/models/{model}:generateContent"
        )

    def invoke(self, prompt: Any) -> "_GeminiResponse":
        import requests  # always available on Streamlit Cloud

        # Accept both raw strings and LangChain message objects
        if hasattr(prompt, "content"):
            text = prompt.content
        elif isinstance(prompt, str):
            text = prompt
        else:
            text = str(prompt)

        payload = {
            "contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"maxOutputTokens": _MAX_TOKENS},
        }

        # AQ. keys MUST be sent as x-goog-api-key header, not ?key= param
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }

        resp = requests.post(self._url, json=payload, headers=headers, timeout=60)

        if not resp.ok:
            raise RuntimeError(
                f"Gemini API error {resp.status_code}: {resp.text[:400]}"
            )

        data = resp.json()
        try:
            content = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Unexpected Gemini response shape: {data}") from e

        return _GeminiResponse(content=content)


class _GeminiResponse:
    """Mirrors the .content attribute that LangChain AIMessage has."""
    def __init__(self, content: str):
        self.content = content


def _ollama():
    from langchain_ollama import ChatOllama
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    return ChatOllama(model=_MODELS["ollama"], base_url=base_url, num_predict=_MAX_TOKENS)


def _openrouter():
    _require_key("OPENROUTER_API_KEY", "openrouter")
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=_MODELS["openrouter"],
        openai_api_key=os.environ["OPENROUTER_API_KEY"],
        openai_api_base="https://openrouter.ai/api/v1",
        max_tokens=_MAX_TOKENS,
        default_headers={"HTTP-Referer": "https://exportai.in", "X-Title": "ExportAI"},
    )


def _require_key(env_var: str, provider: str) -> None:
    if not os.environ.get(env_var):
        raise EnvironmentError(
            f"\n\nProvider '{provider}' needs {env_var} to be set.\n"
            f"  Mac/Linux:  export {env_var}=your-key-here\n"
            f"  Windows:    set {env_var}=your-key-here\n"
        )
