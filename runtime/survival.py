"""FOCUX Survival — business survival tiers (pattern from Conway Automaton, MIT).

The business has no free existence: revenue must exceed operating cost.
Tiers change EFFORT (which models, which roles, how often) — NEVER
authorization. Money-gate rules are tier-independent: a `critical` business
still cannot auto-approve a payment. Survival is physics, not punishment.

Tier thresholds (Automaton-style, adapted to business units):

    high         runway >= 90 days
    normal       runway >= 30 days
    low_compute  runway >= 7 days
    critical     runway >= 0 days (broke but alive — seeking revenue)
    dead         runway < 0 days (negative: revenue < cost sustained)

Deterministic: NO LLM in the tier calculation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

#: Runway days per tier (min inclusive).
TIER_THRESHOLDS: dict[str, float] = {
    "high": 90.0,
    "normal": 30.0,
    "low_compute": 7.0,
    "critical": 0.0,
}

TIER_ORDER: tuple[str, ...] = ("high", "normal", "low_compute", "critical", "dead")


class SurvivalTier(str, Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW_COMPUTE = "low_compute"
    CRITICAL = "critical"
    DEAD = "dead"


@dataclass(frozen=True)
class BusinessFinances:
    revenue: float  # trailing revenue (e.g. last 30 days)
    operating_cost: float  # trailing cost (inference + tools + data)
    cash: float = 0.0  # buffer available

    @property
    def profit(self) -> float:
        return self.revenue - self.operating_cost

    @property
    def runway_days(self) -> float:
        """Days of runway: cash / daily burn. 0 burn => infinite (high)."""
        daily = self.operating_cost / 30.0
        if daily <= 0:
            return float("inf")
        return (self.cash + max(0.0, self.profit)) / daily

    def as_dict(self) -> dict[str, object]:
        return {
            "revenue": self.revenue,
            "operating_cost": self.operating_cost,
            "cash": self.cash,
            "profit": self.profit,
            "runway_days": (
                round(self.runway_days, 1) if self.runway_days != float("inf") else None
            ),
        }


def survival_tier(finances: BusinessFinances) -> SurvivalTier:
    """Deterministic tier from runway. NO LLM."""
    runway = finances.runway_days
    if runway == float("inf"):
        return SurvivalTier.HIGH
    if runway >= TIER_THRESHOLDS["high"]:
        return SurvivalTier.HIGH
    if runway >= TIER_THRESHOLDS["normal"]:
        return SurvivalTier.NORMAL
    if runway >= TIER_THRESHOLDS["low_compute"]:
        return SurvivalTier.LOW_COMPUTE
    if runway >= TIER_THRESHOLDS["critical"]:
        return SurvivalTier.CRITICAL
    return SurvivalTier.DEAD


#: What each tier MAY change (effort only).
TIER_BEHAVIOR: dict[SurvivalTier, dict[str, object]] = {
    SurvivalTier.HIGH: {
        "model": "frontier", "heartbeat": "fast", "roles": "all",
        "non_essential": True, "revenue_seeking": False,
    },
    SurvivalTier.NORMAL: {
        "model": "default", "heartbeat": "normal", "roles": "all",
        "non_essential": True, "revenue_seeking": False,
    },
    SurvivalTier.LOW_COMPUTE: {
        "model": "cheap", "heartbeat": "slow", "roles": "core",
        "non_essential": False, "revenue_seeking": False,
    },
    SurvivalTier.CRITICAL: {
        "model": "cheapest", "heartbeat": "minimal", "roles": "revenue",
        "non_essential": False, "revenue_seeking": True,
    },
    SurvivalTier.DEAD: {
        "model": "none", "heartbeat": "off", "roles": "none",
        "non_essential": False, "revenue_seeking": False,
    },
}


def tier_behavior(tier: SurvivalTier) -> dict[str, object]:
    return TIER_BEHAVIOR[tier]


def report(finances: BusinessFinances, *, now: datetime | None = None) -> dict[str, object]:
    """Full survival report (for the heartbeat + dashboard)."""
    tier = survival_tier(finances)
    return {
        "tier": tier.value,
        "finances": finances.as_dict(),
        "behavior": tier_behavior(tier),
        "checked_at": (now or datetime.now(UTC)).isoformat(timespec="seconds"),
        "authorization_unchanged": True,  # tiers never touch the money-gate
    }
