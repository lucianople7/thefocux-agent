"""FOCUX Orchestrator — 9 specialized business roles with schedules.

Original implementation inspired by the business-agent *pattern* popularized
by Polsia (9 agents with cadences) — NOT their code (repo has no license).
Each role maps to THE FOCUX pillars, runs through the money-gate, and is
proposal-only: nothing executes without human approval where the gate says
REVIEW. The orchestrator is deterministic (no LLM in the schedule logic);
the LLM does the drafting per role via the agent.

Roles:
  orchestrator        morning plan + evening summary         06:00 / 20:00
  planning            strategy, KPIs, growth recs            daily
  competitor-research web search + profile updates           daily
  social-media        draft + post content                   every 2h
  email-outreach      prospect finding + sequences           every 3h
  customer-support     inbox triage + draft replies           every 3h
  ads                 campaign optimization                  every 6h
  code                ship features, PRs                    on demand
  finance             revenue sync, spend tracking           every 6h
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from policy.money_gate import ActionClass

#: Role -> (pillar, action class, cadence label, skill hint)
ROLES: dict[str, dict[str, object]] = {
    "orchestrator": {
        "pillar": "research", "action_class": ActionClass.READ,
        "cadence": "06:00 / 20:00", "skill": "cadence",
    },
    "planning": {
        "pillar": "research", "action_class": ActionClass.READ,
        "cadence": "daily", "skill": "content-matrix",
    },
    "competitor-research": {
        "pillar": "research", "action_class": ActionClass.READ,
        "cadence": "daily", "skill": "research",
    },
    "social-media": {
        "pillar": "content", "action_class": ActionClass.CONTENT,
        "cadence": "every 2h", "skill": "post-writer",
    },
    "email-outreach": {
        "pillar": "content", "action_class": ActionClass.CONTENT,
        "cadence": "every 3h", "skill": "post-formatter",
    },
    "customer-support": {
        "pillar": "content", "action_class": ActionClass.CONTENT,
        "cadence": "every 3h", "skill": "post-writer",
    },
    "ads": {
        "pillar": "monetization", "action_class": ActionClass.COMMERCE,
        "cadence": "every 6h", "skill": "commerce-ops",
    },
    "code": {
        "pillar": "account", "action_class": ActionClass.ACCOUNT,
        "cadence": "on demand", "skill": "incremental-implementation",
    },
    "finance": {
        "pillar": "monetization", "action_class": ActionClass.MONEY,
        "cadence": "every 6h", "skill": "money-gate",
    },
}


@dataclass(frozen=True)
class Role:
    name: str
    pillar: str
    action_class: ActionClass
    cadence: str
    skill: str

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "pillar": self.pillar,
            "action_class": self.action_class.value,
            "cadence": self.cadence,
            "skill": self.skill,
        }


def all_roles() -> list[Role]:
    return [
        Role(
            name=name,
            pillar=str(meta["pillar"]),
            action_class=meta["action_class"],  # type: ignore[arg-type]
            cadence=str(meta["cadence"]),
            skill=str(meta["skill"]),
        )
        for name, meta in ROLES.items()
    ]


def role_named(name: str) -> Role | None:
    for role in all_roles():
        if role.name == name:
            return role
    return None


# --- Schedule evaluation (deterministic, no LLM) -----------------------------

def _parse_hours(cadence: str) -> tuple[int, ...] | None:
    """'06:00 / 20:00' -> (6, 20). None if not an hourly clock."""
    if ":" not in cadence:
        return None
    hours: list[int] = []
    for part in cadence.split("/"):
        part = part.strip()
        try:
            hours.append(int(part.split(":")[0]))
        except ValueError:
            return None
    return tuple(sorted(hours))


def _parse_interval_hours(cadence: str) -> int | None:
    """'every 2h' -> 2. None if not an interval."""
    if not cadence.startswith("every "):
        return None
    try:
        return int(cadence.split()[1].rstrip("h"))
    except (IndexError, ValueError):
        return None


def role_due(role: Role, now: datetime) -> bool:
    """Deterministic due check for a role at a given time."""
    hours = _parse_hours(role.cadence)
    if hours is not None:
        return now.hour in hours
    interval = _parse_interval_hours(role.cadence)
    if interval is not None:
        # Due at the top of the hour when the hour is divisible by interval.
        return now.minute == 0 and (now.hour % interval == 0)
    if role.cadence == "daily":
        return now.hour == 8  # once a day, 08:00
    if role.cadence == "on demand":
        return False  # triggered by the human, never auto
    return False


def due_roles(now: datetime) -> list[Role]:
    """Roles whose schedule fires at ``now`` (deterministic)."""
    return [role for role in all_roles() if role_due(role, now)]


def next_due_in(role: Role, now: datetime) -> timedelta:
    """Minutes until the role is due again (for the dashboard/CLI)."""
    hours = _parse_hours(role.cadence)
    if hours is not None:
        for h in hours:
            target = now.replace(hour=h, minute=0, second=0, microsecond=0)
            if target > now:
                return target - now
        # next day, earliest hour
        target = (now + timedelta(days=1)).replace(
            hour=hours[0], minute=0, second=0, microsecond=0
        )
        return target - now
    interval = _parse_interval_hours(role.cadence)
    if interval is not None:
        next_hour = ((now.hour // interval) + 1) * interval
        target = now.replace(hour=next_hour % 24, minute=0, second=0, microsecond=0)
        if next_hour >= 24:
            target += timedelta(days=1)
        return target - now
    if role.cadence == "daily":
        target = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target - now
    return timedelta(hours=24)
