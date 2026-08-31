"""LLM clients for the FOCUX runtime — provider-agnostic, zero SDK deps.

Two clients cover the whole spectrum:

- :class:`OpenAICompatClient`: any OpenAI-compatible endpoint over plain
  ``urllib`` (Qwen Token Plan, Groq, Mistral, OpenRouter, vLLM, llama.cpp
  server, ...). No ``openai`` SDK import — the agnosticism contract is kept
  at the HTTP level.
- :class:`OllamaClient`: local, keyless inference at ``http://localhost:11434``.

Both return plain text completions. Tool-call/structured output is left to the
shell that hosts this runtime; the runtime itself is a thin, deterministic
client.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass


class LLMError(RuntimeError):
    """Raised when a provider call fails (network, auth, bad response)."""


@dataclass(frozen=True)
class LLMClient:
    """Base protocol: ``complete(messages) -> str``."""

    def complete(self, messages: list[dict[str, str]]) -> str:  # pragma: no cover
        raise NotImplementedError

    def _post_json(self, url: str, payload: dict[str, object], key: str | None) -> str:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise LLMError(f"HTTP {exc.code} from {url}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise LLMError(f"cannot reach {url}: {exc.reason}") from exc
        parsed = json.loads(body)
        if key is None:
            return json.dumps(parsed, ensure_ascii=False)
        # Walk dotted key path (e.g. "choices.0.message.content").
        node: object = parsed
        for part in key.split("."):
            if isinstance(node, list):
                node = node[int(part)]
            elif isinstance(node, dict) and part in node:
                node = node[part]
            else:
                raise LLMError(f"missing key '{key}' in response from {url}")
        if not isinstance(node, str):
            raise LLMError(f"key '{key}' is not a string in response from {url}")
        return node


@dataclass(frozen=True)
class OpenAICompatClient(LLMClient):
    """Any OpenAI-compatible chat completions endpoint."""

    base_url: str = "http://localhost:8000/v1"
    api_key: str = ""
    model: str = "qwen3.8-max"
    temperature: float = 0.7
    max_tokens: int = 2048

    def complete(self, messages: list[dict[str, str]]) -> str:
        url = self.base_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        payload: dict[str, object] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.api_key:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={**headers, "Authorization": f"Bearer {self.api_key}"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
                    body = resp.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:300]
                raise LLMError(f"HTTP {exc.code} from {url}: {detail}") from exc
            except urllib.error.URLError as exc:
                raise LLMError(f"cannot reach {url}: {exc.reason}") from exc
            parsed = json.loads(body)
        else:
            # Reuse the base POST helper for the keyless path.
            parsed = json.loads(self._post_json(url, payload, key=None))
        try:
            content = parsed["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"unexpected response shape from {url}") from exc
        if not isinstance(content, str):
            raise LLMError(f"content is not a string from {url}")
        return content


@dataclass(frozen=True)
class OllamaClient(LLMClient):
    """Keyless local inference."""

    base_url: str = "http://localhost:11434"
    model: str = "qwen3.5"
    temperature: float = 0.7

    def complete(self, messages: list[dict[str, str]]) -> str:
        url = self.base_url.rstrip("/") + "/api/chat"
        payload: dict[str, object] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        return self._post_json(url, payload, "message.content")
