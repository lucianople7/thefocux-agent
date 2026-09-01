"""THE FOCUX MASTER — the brain's one-glance status and daily cycle.

This is the masterpiece layer: the powers assembled into ONE coherent
picture and ONE daily ritual.

- **master_status()** — everything at a glance (deterministic): survival
  tier, objectives with gaps, work harness state, focus file, absorb
  freshness, user-level MCP registration. What `focux status` shows.
- **daily_cycle()** — the brain working by itself, the daily intelligence
  ritual: VER (absorb real data) -> ENFOQUE (refresh focus) -> ESTRATEGIA
  (drive objectives: gated plan) -> OPORTUNIDADES (insights: gated) ->
  VIGILANCIA (heartbeat with tier). Every step keeps the discipline: the
  LLM proposes, the gate decides, REVIEW stays human.
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .focus import focus_pack, write_focus_file
from .heartbeat import heartbeat
from .objectives import objective_status
from .survival import BusinessFinances, survival_tier
from .workflow import load_state, status_text, work_root


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def master_status(
    memory,
    workspace: str = "default",
    *,
    revenue: float = 0.0,
    operating_cost: float = 0.0,
    cash: float = 0.0,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Everything at a glance (deterministic — no LLM)."""
    tier = survival_tier(BusinessFinances(
        revenue=revenue, operating_cost=operating_cost, cash=cash)).value
    statuses = objective_status(memory, workspace, tier=tier) if memory else []
    root = work_root(cwd)
    state = load_state(root)
    return {
        "workspace": workspace,
        "tier": tier,
        "generated_at": _now(),
        "objectives": [s.as_dict() for s in statuses],
        "work": {
            "stage": state.stage if state else None,
            "objective": state.objective if state else None,
            "status": status_text(root),
        },
        "focus_file": str((cwd or Path.cwd()).resolve() / ".focux" / "focus.md"),
        "absorb": _absorb_freshness(memory, workspace),
        "mcp": _user_mcp(),
    }


def _absorb_freshness(memory, workspace: str) -> dict[str, Any]:
    """When was the last real absorb for this workspace? (evidence freshness)"""
    if memory is None:
        return {"last": None, "fresh": False}
    events = memory.recent_events(workspace, limit=30)
    for e in events:
        if e.kind.startswith("absorb:") and not e.kind.endswith(":error"):
            return {"last": e.created_at, "fresh": True}
    return {"last": None, "fresh": False}


def _user_mcp() -> dict[str, bool]:
    try:
        from .install import user_mcp_registered

        return user_mcp_registered()
    except Exception:  # noqa: BLE001 - enhancement, never fatal
        return {}


def daily_cycle(
    agent,
    workspace: str = "default",
    *,
    revenue: float = 0.0,
    operating_cost: float = 0.0,
    cash: float = 0.0,
    sources: tuple[str, ...] = (),
    github_query: str = "ai agent",
    limit: int = 3,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """The daily intelligence ritual (absorb -> focus -> drive -> insights ->
    heartbeat). Every proposal stays gated; REVIEW is human."""
    report: dict[str, Any] = {
        "generated_at": _now(),
        "workspace": workspace,
    }
    tier = survival_tier(BusinessFinances(
        revenue=revenue, operating_cost=operating_cost, cash=cash)).value
    report["tier"] = tier
    memory = agent.memory

    # 1) VER: absorb real data (network; skipped when no sources)
    absorbed = {"stored": 0, "sources": {}}
    if sources and memory is not None:
        from .ingest import absorb, store_results

        results = absorb(
            sources=sources, github_query=github_query,
            x_bearer=os.environ.get("X_BEARER_TOKEN", ""),
            x_query=github_query, limit=limit,
        )
        absorbed["stored"] = store_results(results, memory, workspace=workspace)
        absorbed["sources"] = {
            s: {"ok": r.ok, "error": r.error} for s, r in results.items()
        }
    report["absorbed"] = absorbed

    # 2) ENFOQUE: refresh the directed-intelligence file
    if memory is not None:
        pack = focus_pack(memory, workspace, tier=tier)
        path = write_focus_file(pack, cwd=cwd)
        report["focus"] = {"file": str(path),
                           "objectives": [o for o in pack.objectives]}
    else:
        report["focus"] = {"file": "", "objectives": []}

    # 3) ESTRATEGIA: drive the objectives (gated plan)
    from .objectives import drive

    drive_report = drive(agent, workspace, limit=limit, tier=tier)
    report["drive"] = {
        "actions": drive_report.actions,
        "note": drive_report.note,
    }

    # 4) OPORTUNIDADES: insights from real signals (gated)
    from .ask import insights

    insights_report = insights(agent, workspace, limit=limit, tier=tier)
    report["insights"] = insights_report

    # 5) VIGILANCIA: heartbeat with the tier
    hb = heartbeat(
        BusinessFinances(revenue=revenue, operating_cost=operating_cost,
                         cash=cash),
        pending_approvals=0,
    )
    report["heartbeat"] = hb.as_dict()

    # 6) MEJORA: the success governor - improvements at all hours (gated)
    from .improve import improve

    improve_report = improve(agent, workspace, limit=min(2, limit),
                             tier=tier, repo_root=None)
    report["improve"] = improve_report
    return report


def format_master_status(data: dict[str, Any]) -> str:
    """One-glance masterpiece view (console-safe)."""
    lines = ["THE FOCUX BRAIN - master status",
             f"  workspace: {data['workspace']} | tier: {data['tier']} "
             f"(esfuerzo, nunca autorizacion)"]
    objs = data.get("objectives", [])
    if objs:
        lines.append(f"  objetivos: {len(objs)}")
        for o in objs:
            lines.append(
                f"    [{o['objective_id']}] {o['title']} | {o['kpi']}: "
                f"{o['current']:.0f}/{o['target']:.0f} | {o['progress'] * 100:.0f}%"
                f" | gap {o['gap']:.0f}"
            )
    else:
        lines.append("  objetivos: none - intelligence without goals is noise")
    work = data.get("work", {})
    if work.get("stage"):
        lines.append(f"  work: [{work['stage']}] {work.get('objective', '')}")
    else:
        lines.append("  work: no staged work (do it directly if it fits a session)")
    absorb = data.get("absorb", {})
    lines.append("  datos reales: " + (
        f"absorbed {absorb['last']}" if absorb.get("fresh")
        else "no absorb yet - run `focux absorb` or `focux daily`"))
    mcp = data.get("mcp", {})
    registered = [a for a, ok in mcp.items() if ok]
    lines.append("  MCP user-level: " + (
        ", ".join(registered) if registered else "not registered (focux install --mcp)"))
    return _safe("\n".join(lines))


def format_daily(report: dict[str, Any]) -> str:
    """The daily ritual report (console-safe)."""
    lines = [f"DAILY CYCLE (workspace: {report['workspace']}) - "
             f"tier {report['tier']}"]
    absorbed = report.get("absorbed", {})
    lines.append(f"  1. VER: absorbed {absorbed['stored']} real items"
                 + (f" ({', '.join(absorbed['sources'])})" if absorbed["sources"] else " (sin red)"))
    lines.append(f"  2. ENFOQUE: focus refreshed ({report.get('focus', {}).get('file', '')})")
    drive = report.get("drive", {})
    if drive.get("actions"):
        for a in drive["actions"]:
            lines.append(f"  3. ESTRATEGIA: [{a['decision']}] ({a['pillar']}) {a['action']}")
    else:
        lines.append(f"  3. ESTRATEGIA: note: {drive.get('note', '')}")
    insights = report.get("insights", {})
    for i in insights.get("insights", []):
        lines.append(f"  4. OPORTUNIDADES: [{i['decision']}] ({i['pillar']}) {i['insight']}")
    if not insights.get("insights"):
        lines.append("  4. OPORTUNIDADES: none (model produced nothing parseable)")
    hb = report.get("heartbeat", {})
    lines.append(f"  5. VIGILANCIA: tier {hb.get('tier', '?')} | "
                 f"runway {hb.get('runway_days', 0):.0f}d | healthy {hb.get('healthy', '?')}")
    improve_report = report.get("improve", {})
    for i in improve_report.get("improvements", []):
        lines.append(f"  6. MEJORA: [{i['decision']}] ({i['target']}) {i['improvement']}")
    if not improve_report.get("improvements"):
        lines.append("  6. MEJORA: none (model produced nothing parseable)")
    reviews = [a for a in drive.get("actions", []) if a["decision"] == "REVIEW"]
    reviews += [i for i in insights.get("insights", []) if i["decision"] == "REVIEW"]
    reviews += [i for i in improve_report.get("improvements", [])
                if i["decision"] == "REVIEW"]
    if reviews:
        lines.append(f"  {len(reviews)} REVIEW items await human approval.")
    return _safe("\n".join(lines))


def _safe(text: str) -> str:
    try:
        return text.encode("cp1252", errors="replace").decode("cp1252")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text.encode("ascii", errors="replace").decode("ascii")
