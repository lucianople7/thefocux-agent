"""THE FOCUX Agent — minimal self-contained runtime.

THE FOCUX stands on its OWN runtime: no shell dependency (no OpenClaw, no
CowAgent, no kaizen7-jarvis needed). This runtime loads the DNA (policy
modules), the 17 skills (open Agent Skills format), connects to ANY LLM
(OpenAI-compatible or Ollama-local), and runs the business loop with the
money-gate + constitution always in the path.

Principles (from docs/provider-agnostic-guarantee.md):
- NO LLM SDK imports: providers are spoken over plain HTTP (urllib), so this
  runtime has zero third-party dependencies for inference.
- Deterministic gates first: every action passes the money-gate before any
  tool runs; the constitution audits the verdict.
- Proposal-only: the runtime proposes; the human approves (REVIEW gates).
"""
from __future__ import annotations

from .agent import FocuxAgent, FocuxResult
from .llm import LLMClient, OllamaClient, OpenAICompatClient
from .skills import Skill, load_skills

__all__ = [
    "FocuxAgent",
    "FocuxResult",
    "LLMClient",
    "OllamaClient",
    "OpenAICompatClient",
    "Skill",
    "load_skills",
]
