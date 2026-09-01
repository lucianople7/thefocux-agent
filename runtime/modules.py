"""FOCUX modular registry — every brain organ registered, versioned, checkable.

THE FOCUX is deliberately modular: each organ (gate, memory, survival,
heartbeat, selfmod, orchestrator, tools, eval, evolution) is an independent
module with a declared id, version, dependencies and a health check. The
registry is the single source of truth for "what the brain is made of", and
``integrity_check`` proves every module loads and the money-gate falsification
still holds — so a new module cannot silently break the immune system.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Module:
    id: str
    version: str
    description: str
    deps: tuple[str, ...] = ()
    entry: str = ""  # primary symbol (for import check)

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "version": self.version,
            "description": self.description,
            "deps": list(self.deps),
            "entry": self.entry,
        }


MODULES: tuple[Module, ...] = (
    Module("money-gate", "1.0.0", "Deterministic approval boundary (ALLOW/REVIEW/DENY)",
           entry="policy.money_gate"),
    Module("constitution", "1.0.0", "Three immutable laws as code",
           deps=("money-gate",), entry="policy.constitution"),
    Module("soul", "1.0.0", "SOUL.md validation + injection defense",
           entry="policy.focux_soul"),
    Module("voice", "1.0.0", "Voice profile builder (interview + absence signals)",
           entry="policy.focux_voice"),
    Module("content", "1.0.0", "Content matrix + hook generator",
           entry="policy.focux_content"),
    Module("cli-tools", "1.0.0", "Agent-native CLI layer (registry + gating)",
           deps=("money-gate",), entry="policy.focux_cli"),
    Module("memory", "1.1.0", "Local SQLite stores + retrieval gate + workspaces",
           entry="runtime.memory"),
    Module("tools", "1.0.0", "Gated tool layer (do_<name> dispatch)",
           deps=("money-gate", "constitution"), entry="runtime.tools"),
    Module("eval", "1.0.0", "Release gate: deterministic checks + LLM-judge",
           deps=("tools",), entry="runtime.eval"),
    Module("survival", "1.0.0", "Business survival tiers (effort, never auth)",
           entry="runtime.survival"),
    Module("heartbeat", "1.0.0", "Watch tier + roles + approvals + momentum",
           deps=("survival", "orchestrator"), entry="runtime.heartbeat"),
    Module("selfmod", "1.1.0", "Append-only audit + rate limits",
           entry="runtime.selfmod"),
    Module("orchestrator", "1.0.0", "9+ specialized business roles with schedules",
           deps=("survival",), entry="runtime.orchestrator"),
    Module("evolution", "1.0.0", "Daily evolution cycle (analyze -> improve)",
           deps=("memory", "selfmod"), entry="runtime.evolution"),
    Module("repurpose", "1.0.0", "Content multiplier: 1 asset -> 20+ outputs",
           deps=("money-gate", "constitution"), entry="runtime.repurpose"),
    Module("offer", "1.0.0", "5-rung offer ladder: attention -> revenue",
           deps=("constitution",), entry="runtime.offer"),
    Module("ingest", "1.0.0", "Real-data absorption: github/huggingface/x sensors -> memory",
           deps=("memory",), entry="runtime.ingest"),
    Module("attach", "1.0.0", "Universal installer: THE FOCUX BRAIN in any coding agent's workspace",
           deps=("memory",), entry="runtime.attach"),
    Module("install", "1.0.0", "Global CLI installer: portable launchers + user-level MCP",
           deps=("attach",), entry="runtime.install"),
    Module("mcp-bridge", "1.0.0", "The brain as MCP tools for any agent",
           deps=("tools", "memory", "survival", "heartbeat", "orchestrator",
                 "selfmod"), entry="mcp_bridge"),
    Module("webui", "1.0.0", "Local console with THE FOCUX logo",
           deps=("tools", "memory"), entry="webui"),
)


def all_modules() -> list[Module]:
    return list(MODULES)


def module_named(module_id: str) -> Module | None:
    for module in MODULES:
        if module.id == module_id:
            return module
    return None


def integrity_check() -> dict[str, object]:
    """Prove every module imports and the immune system still holds.

    Returns a report; ``ok`` is False if any module fails to import or the
    money-gate falsification test fails. Deterministic, no network.
    """
    import importlib

    results: list[dict[str, object]] = []
    ok = True
    for module in MODULES:
        try:
            importlib.import_module(module.entry)
            results.append({"id": module.id, "ok": True, "version": module.version})
        except Exception as exc:  # noqa: BLE001
            ok = False
            results.append({
                "id": module.id, "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            })

    # immune system invariant
    try:
        from policy.money_gate import MoneyGate

        falsification = MoneyGate({}).falsification_test()
        results.append({
            "id": "falsification", "ok": falsification,
            "version": "invariant",
        })
        if not falsification:
            ok = False
    except Exception as exc:  # noqa: BLE001
        ok = False
        results.append({"id": "falsification", "ok": False, "error": str(exc)})

    return {"ok": ok, "modules": results,
            "count": len(results), "healthy": ok}
