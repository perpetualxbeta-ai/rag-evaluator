"""Model factory: one place that decides which provider and models the repo uses.

Set LLM_PROVIDER in .env:
    openai  - OpenAI API (needs OPENAI_API_KEY, paid)
    ollama  - local models served by Ollama (free, runs on your machine)
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
if PROVIDER not in {"openai", "ollama"}:
    raise SystemExit(f"LLM_PROVIDER must be 'openai' or 'ollama', got '{PROVIDER}'.")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

_DEFAULTS = {
    "openai": {
        "EMBEDDING_MODEL": "text-embedding-3-small",
        "GENERATOR_MODEL": "gpt-4o-mini",
        "RAG_MODEL": "gpt-4o-mini",
        "JUDGE_MODEL": "gpt-4o",
    },
    "ollama": {
        "EMBEDDING_MODEL": "nomic-embed-text",
        "GENERATOR_MODEL": "qwen2.5:7b",
        "RAG_MODEL": "qwen2.5:7b",
        "JUDGE_MODEL": "qwen2.5:7b",
    },
}


def _setting(name: str) -> str:
    return os.getenv(name) or _DEFAULTS[PROVIDER][name]


EMBEDDING_MODEL = _setting("EMBEDDING_MODEL")
GENERATOR_MODEL = _setting("GENERATOR_MODEL")
RAG_MODEL = _setting("RAG_MODEL")
JUDGE_MODEL = _setting("JUDGE_MODEL")

# Local models answer one request at a time and are much slower, so Ragas needs
# fewer parallel workers and longer timeouts to avoid spurious failures.
DEFAULT_MAX_WORKERS = 2 if PROVIDER == "ollama" else 8
REQUEST_TIMEOUT = 900 if PROVIDER == "ollama" else 180


def get_chat_model(model: str, temperature: float = 0.0) -> BaseChatModel:
    if PROVIDER == "ollama":
        from langchain_ollama import ChatOllama

        # Ollama's default context window (2048 tokens) is too small for Ragas prompts.
        return ChatOllama(
            model=model, temperature=temperature, base_url=OLLAMA_BASE_URL, num_ctx=8192
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=model, temperature=temperature)


def get_embeddings() -> Embeddings:
    """Single source of truth for the embedding model used at index *and* query time."""
    if PROVIDER == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)

    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(model=EMBEDDING_MODEL)


def check_provider(*models: str) -> None:
    """Fail fast with a readable message if the provider isn't usable."""
    if PROVIDER == "openai":
        key = os.getenv("OPENAI_API_KEY", "")
        if not key or key == "sk-...":
            raise SystemExit(
                "OPENAI_API_KEY is not set. Put your key in .env, or set "
                "LLM_PROVIDER=ollama to use free local models instead."
            )
        return

    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=5) as resp:
            installed = {m["name"] for m in json.load(resp).get("models", [])}
    except (urllib.error.URLError, OSError) as exc:
        raise SystemExit(
            f"Can't reach Ollama at {OLLAMA_BASE_URL} ({exc}). "
            "Install it from https://ollama.com and make sure the Ollama app is running."
        ) from exc

    def is_installed(name: str) -> bool:
        return name in installed or f"{name}:latest" in installed

    missing = sorted({m for m in models if not is_installed(m)})
    if missing:
        raise SystemExit(
            "These Ollama models aren't downloaded yet: "
            + ", ".join(missing)
            + "\nRun: "
            + " && ".join(f"ollama pull {m}" for m in missing)
        )
