"""FOCUX Heartbeat — watch business health, tier, and role schedules.

Pattern from Conway Automaton `src/heartbeat/` (MIT), adapted: a lightweight
daemon that runs scheduled checks — survival tier, memory health, pending
approvals, and the 9 role cadences — and reports what is due. It never
executes money/publish actions itself: it surfaces them for the human.

The heartbeat is deterministic + read-only: it inspects state and schedules;
it does not act. Acting stays behind the money-gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .orchestrator import Role, all_roles, due_roles
from .survival import BusinessFinances, report, survival_tier


@dataclass(frozen=True)
class HeartbeatReport:
    timestamp: str
    tier: str
    runway_days: float | None
    roles_due: tuple[str, ...]
    roles_next: dict[str, float]  # role -> minutes until next due
    pending_approvals: int
    healthy: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "tier": self.tier,
            "runway_days": self.runway_days,
            "roles_due": list(self.roles_due),
            "roles_next_minutes": self.roles_next,
            "pending_approvals": self.pending_approvals,
            "healthy": self.healthy,
        }


def heartbeat(
    finances: BusinessFinances,
    *,
    now: datetime | None = None,
    pending_approvals: int = 0,
    roles: list[Role] | None = None,
) -> HeartbeatReport:
    """Produce a heartbeat report. Read-only, deterministic."""
    now = now or datetime.now(UTC)
    tier = survival_tier(finances)
    roles = roles or all_roles()
    due = [r.name for r in due_roles(now)]

    from .orchestrator import next_due_in

    next_map: dict[str, float] = {}
    for role in roles:
        delta = next_due_in(role, now)
        minutes = delta.total_seconds() / 60.0
        next_map[role.name] = round(minutes, 1)

    healthy = tier.value not in ("dead", "critical")
    return HeartbeatReport(
        timestamp=now.isoformat(timespec="seconds"),
        tier=tier.value,
        runway_days=(
            round(finances.runway_days, 1)
            if finances.runway_days != float("inf")
            else None
        ),
        roles_due=tuple(sorted(due)),
        roles_next=next_map,
        pending_approvals=pending_approvals,
        healthy=healthy,
    )


def format_report(report: HeartbeatReport) -> str:
    """Human-readable heartbeat (for CLI/dashboard)."""
    lines = [
        f"HEARTBEAT {report.timestamp}",
        f"Tier: {report.tier} | runway: "
        + (f"{report.runway_days}d" if report.runway_days is not None else "infinite"),
        f"Pending approvals: {report.pending_approvals}",
    ]
    if report.roles_due:
        lines.append("Roles due now: " + ", ".join(report.roles_due))
    else:
        lines.append("Roles due now: none")
    next_line = ", ".join(
        f"{name} in {mins:.0f}m"
        for name, mins in sorted(report.roles_next.items(), key=lambda kv: kv[1])[:3]
    )
    lines.append("Next: " + next_line)
    lines.append("Healthy: " + ("yes" if report.healthy else "NO"))
    return "\n".join(lines)
