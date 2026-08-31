"""FOCUX provider configuration — one-step connection to any LLM.

Loads settings from the environment OR a local ``.env`` file (no external
dependencies — a minimal parser). Provider presets make connection a single
key:

- ``FOCUX_PROVIDER=deepseek`` -> https://api.deepseek.com/v1, deepseek-chat
- ``FOCUX_PROVIDER=qwen``     -> Qwen Token Plan compatible endpoint
- ``FOCUX_PROVIDER=openai``   -> api.openai.com
- ``FOCUX_PROVIDER=ollama``   -> local, keyless
- custom: ``FOCUX_MODEL`` + ``FOCUX_BASE_URL`` (+ ``FOCUX_API_KEY``)

Order: environment wins over ``.env``. The API key is read from env/.env —
never from the repo, never logged (runtime/redact.py guards receipts).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

#: Provider presets: provider -> (base_url, default_model, needs_key)
PROVIDERS: dict[str, tuple[str, str, bool]] = {
    "deepseek": ("https://api.deepseek.com/v1", "deepseek-chat", True),
    "qwen": (
        "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
        "qwen3.8-max",
        True,
    ),
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini", True),
    "ollama": ("http://localhost:11434", "qwen3.5", False),
}


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str
    base_url: str
    api_key: str

    @property
    def keyless(self) -> bool:
        return not self.api_key


def _load_dotenv(repo_root: Path) -> None:
    """Minimal .env loader (FOCUX_* keys only). No external dependency."""
    env_file = repo_root / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key.startswith("FOCUX_") and key not in os.environ:
            os.environ[key] = value


def load_settings(repo_root: Path) -> LLMSettings:
    """Resolve provider settings: env over .env over preset defaults."""
    _load_dotenv(repo_root)

    provider = os.environ.get("FOCUX_PROVIDER", "").strip().lower()
    model = os.environ.get("FOCUX_MODEL", "").strip()
    base_url = os.environ.get("FOCUX_BASE_URL", "").strip()
    api_key = os.environ.get("FOCUX_API_KEY", "").strip()

    # 1) explicit provider preset
    if provider in PROVIDERS:
        preset_base, preset_model, needs_key = PROVIDERS[provider]
        return LLMSettings(
            provider=provider,
            model=model or preset_model,
            base_url=base_url or preset_base,
            api_key=api_key,
        )

    # 2) custom OpenAI-compatible (model + base_url given)
    if model and base_url:
        return LLMSettings(
            provider="custom", model=model, base_url=base_url, api_key=api_key
        )

    # 3) model-only: guess provider by model name
    if model:
        lowered = model.lower()
        if "deepseek" in lowered:
            base, default_model, _ = PROVIDERS["deepseek"]
            return LLMSettings(
                provider="deepseek", model=model, base_url=base_url or base,
                api_key=api_key,
            )
        if "qwen" in lowered:
            base, default_model, _ = PROVIDERS["qwen"]
            return LLMSettings(
                provider="qwen", model=model, base_url=base_url or base,
                api_key=api_key,
            )
        if "gpt" in lowered or "o1" in lowered or "o3" in lowered:
            base, default_model, _ = PROVIDERS["openai"]
            return LLMSettings(
                provider="openai", model=model, base_url=base_url or base,
                api_key=api_key,
            )

    # 4) default: local Ollama, keyless
    base, default_model, _ = PROVIDERS["ollama"]
    return LLMSettings(
        provider="ollama", model=model or default_model, base_url=base_url or base,
        api_key=api_key,
    )
