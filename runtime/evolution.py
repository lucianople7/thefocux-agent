"""FOCUX daily evolution — the brain improves itself, every day.

The evolution cycle is the daily heartbeat of MEJORAR: it reads what was
executed (procedures with success/fail counters), what was learned (skills
crystallized), and the momentum metrics; then it produces CONCRETE
improvement proposals — never vibes:

1. **Fix failure-heavy procedures** — a procedure with fail_count >= 2 and
   fail ratio >= 0.5 is flagged with a proposal to rework it.
2. **Crystallize winners** — a procedure with success ratio >= 0.8 becomes a
   proposal to crystallize as a DRAFT skill (human promotes).
3. **Review drafts** — crystallized drafts waiting for promotion are listed.

The cycle is deterministic in its analysis; the LLM (optional) only words the
proposals. Every run records an 'evolution' event in memory and appends to
the self-mod audit. It never executes anything: all proposals are DRAFT.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .memory import FocuxMemory
from .selfmod import SelfModLog


@dataclass(frozen=True)
class EvolutionProposal:
    kind: str  # fix | crystallize | promote
    target: str
    evidence: str
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "target": self.target,
            "evidence": self.evidence,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class EvolutionReport:
    timestamp: str
    workspace: str
    proposals: tuple[EvolutionProposal, ...] = ()
    summary: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "workspace": self.workspace,
            "proposals": [p.as_dict() for p in self.proposals],
            "summary": self.summary,
        }


def analyze(
    mem: FocuxMemory,
    workspace: str,
    *,
    drafts_dir: Path | None = None,
) -> EvolutionReport:
    """Deterministic daily analysis: what to fix, what to crystallize."""
    proposals: list[EvolutionProposal] = []
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")

    procedures = mem.procedures(workspace)
    for proc in procedures:
        total = proc.success_count + proc.fail_count
        if total == 0:
            continue
        fail_ratio = proc.fail_count / total
        success_ratio = proc.success_count / total

        # 1) failure-heavy -> propose fix
        if proc.fail_count >= 2 and fail_ratio >= 0.5:
            proposals.append(EvolutionProposal(
                kind="fix",
                target=proc.name,
                evidence=f"{proc.success_count} ok / {proc.fail_count} fail",
                reason="failure-heavy procedure; rework the steps",
            ))
        # 2) proven winner -> propose crystallize (human promotes)
        elif success_ratio >= 0.8 and proc.success_count >= 3:
            proposals.append(EvolutionProposal(
                kind="crystallize",
                target=proc.name,
                evidence=f"{proc.success_count} ok / {proc.fail_count} fail",
                reason="proven winner; crystallize as DRAFT skill",
            ))

    # 3) drafts waiting for human promotion
    if drafts_dir is not None and drafts_dir.is_dir():
        for d in sorted(p for p in drafts_dir.iterdir() if p.is_dir()):
            if (d / "SKILL.md").is_file():
                proposals.append(EvolutionProposal(
                    kind="promote",
                    target=d.name,
                    evidence="draft in skills-draft/",
                    reason="awaiting human promotion",
                ))

    summary = (
        f"{len(procedures)} procedures analyzed, "
        f"{len(proposals)} improvement proposal(s)"
    )
    return EvolutionReport(
        timestamp=timestamp,
        workspace=workspace,
        proposals=tuple(proposals),
        summary=summary,
    )


def run_daily_evolution(
    *,
    workspace: str = "default",
    memory_dir: Path = Path("memory"),
    drafts_dir: Path | None = None,
) -> EvolutionReport:
    """Run the daily cycle: analyze, record event + audit, return report."""
    mem = FocuxMemory(memory_dir / "focux.db")
    try:
        report = analyze(mem, workspace, drafts_dir=drafts_dir)
        mem.remember_event(workspace, "evolution", {
            "summary": report.summary,
            "proposals": [p.as_dict() for p in report.proposals],
            "at": report.timestamp,
        })
    finally:
        mem.close()

    # audit the cycle itself (append-only)
    try:
        SelfModLog().append(
            "evolution_run",
            f"daily evolution for '{workspace}': {report.summary}",
            data={"proposals": len(report.proposals)},
        )
    except Exception:  # noqa: BLE001 - audit is best-effort
        pass
    return report


def format_report(report: EvolutionReport) -> str:
    lines = [f"EVOLUTION {report.timestamp} — {report.workspace}",
             report.summary]
    for proposal in report.proposals:
        lines.append(
            f"  [{proposal.kind}] {proposal.target}: "
            f"{proposal.reason} ({proposal.evidence})"
        )
    if not report.proposals:
        lines.append("  (no improvement proposals today — all clean)")
    return "\n".join(lines)
