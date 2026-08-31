"""Tests for provider configuration — one-step DeepSeek/Qwen/OpenAI/Ollama."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from runtime.config import PROVIDERS, _load_dotenv, load_settings  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Remove FOCUX_* vars between tests so each test starts clean."""
    for key in list(os.environ):
        if key.startswith("FOCUX_"):
            monkeypatch.delenv(key, raising=False)
    # The repo's real .env (DeepSeek) must not leak into REPO-based calls;
    # tests that explicitly exercise .env use tmp_path and bypass this stub
    # by calling load_settings(tmp_path) which is not REPO.
    real_load = _load_dotenv

    def _guarded_load(root):
        if Path(root).resolve() == REPO.resolve():
            return  # skip the real .env during tests
        real_load(root)

    monkeypatch.setattr("runtime.config._load_dotenv", _guarded_load)
    yield


def test_deepseek_preset() -> None:
    os.environ["FOCUX_PROVIDER"] = "deepseek"
    os.environ["FOCUX_API_KEY"] = "sk-test"
    s = load_settings(REPO)
    assert s.provider == "deepseek"
    assert s.model == "deepseek-chat"
    assert "api.deepseek.com" in s.base_url
    assert s.api_key == "sk-test"
    assert not s.keyless


def test_deepseek_by_model_name() -> None:
    os.environ["FOCUX_MODEL"] = "deepseek-chat"
    os.environ["FOCUX_API_KEY"] = "sk-test"
    s = load_settings(REPO)
    assert s.provider == "deepseek"
    assert "api.deepseek.com" in s.base_url


def test_reasoner_model() -> None:
    os.environ["FOCUX_PROVIDER"] = "deepseek"
    os.environ["FOCUX_MODEL"] = "deepseek-reasoner"
    s = load_settings(REPO)
    assert s.model == "deepseek-reasoner"


def test_qwen_preset() -> None:
    os.environ["FOCUX_PROVIDER"] = "qwen"
    s = load_settings(REPO)
    assert s.provider == "qwen"
    assert "token-plan" in s.base_url


def test_openai_preset() -> None:
    os.environ["FOCUX_PROVIDER"] = "openai"
    s = load_settings(REPO)
    assert s.provider == "openai"
    assert "api.openai.com" in s.base_url


def test_custom_compatible() -> None:
    os.environ["FOCUX_MODEL"] = "my-model"
    os.environ["FOCUX_BASE_URL"] = "http://localhost:8000/v1"
    os.environ["FOCUX_API_KEY"] = "k"
    s = load_settings(REPO)
    assert s.provider == "custom"
    assert s.base_url == "http://localhost:8000/v1"


def test_default_is_ollama_keyless() -> None:
    s = load_settings(REPO)
    assert s.provider == "ollama"
    assert s.keyless


def test_dotenv_loaded(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text(
        "FOCUX_PROVIDER=deepseek\nFOCUX_API_KEY=sk-from-dotenv\n# comment\n",
        encoding="utf-8",
    )
    s = load_settings(tmp_path)
    assert s.provider == "deepseek"
    assert s.api_key == "sk-from-dotenv"


def test_env_wins_over_dotenv(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    env = tmp_path / ".env"
    env.write_text("FOCUX_API_KEY=from-dotenv\n", encoding="utf-8")
    monkeypatch.setenv("FOCUX_API_KEY", "from-env")
    s = load_settings(tmp_path)
    assert s.api_key == "from-env"


def test_all_presets_defined() -> None:
    assert set(PROVIDERS) == {"deepseek", "qwen", "openai", "ollama"}
    for preset, (base, model, needs_key) in PROVIDERS.items():
        assert base.startswith("http")
        assert model
        assert isinstance(needs_key, bool)
