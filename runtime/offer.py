"""FOCUX Offer Ladder — turn multiplied attention into revenue.

The monetization side of the multiplier: a 5-step offer ladder that takes a
stranger (free) to a premium customer. Each rung has a clear asset, a value
anchor, a suggested price band, and the conversion CTA. Deterministic
structure; the LLM fills the actual copy. Law II applies: every rung must
create genuine value — the ladder monetizes trust, not pressure.
"""
from __future__ import annotations

from dataclasses import dataclass

from policy.constitution import check_law2


@dataclass(frozen=True)
class LadderRung:
    step: str
    purpose: str
    asset: str
    price_band: str
    conversion: str
    passed_gate: bool = True

    def as_dict(self) -> dict[str, str]:
        return {
            "step": self.step,
            "purpose": self.purpose,
            "asset": self.asset,
            "price_band": self.price_band,
            "conversion": self.conversion,
        }


#: The 5-rung ladder (deterministic structure).
def build_ladder(
    *,
    business: str = "the business",
    lead_magnet: str = "a free guide",
    entry_offer: str = "a low-ticket starter",
    core_offer: str = "the flagship product",
    premium_offer: str = "done-for-you / high-touch",
) -> list[LadderRung]:
    rungs = [
        LadderRung(
            step="1 · free",
            purpose="capture attention from multiplied reach",
            asset=lead_magnet,
            price_band="$0",
            conversion="every CTA in the 20 outputs points here",
        ),
        LadderRung(
            step="2 · lead",
            purpose="build email/contact list",
            asset="opt-in + welcome sequence",
            price_band="$0",
            conversion="lead magnet -> welcome email -> soft offer",
        ),
        LadderRung(
            step="3 · entry",
            purpose="first purchase, low risk",
            asset=entry_offer,
            price_band="$9-$49",
            conversion="one small win builds trust",
        ),
        LadderRung(
            step="4 · core",
            purpose="main revenue",
            asset=core_offer,
            price_band="$99-$499",
            conversion="entry buyers upgraded with proof",
        ),
        LadderRung(
            step="5 · premium",
            purpose="high margin, high touch",
            asset=premium_offer,
            price_band="$500+",
            conversion="core buyers invited to premium",
        ),
    ]
    # Law II gate: no rung may be an extraction signal.
    for rung in rungs:
        verdict = check_law2(f"{rung.asset} {rung.conversion}")
        if not verdict.passed:
            rungs = [
                LadderRung(
                    step=r.step, purpose=r.purpose, asset=r.asset,
                    price_band=r.price_band, conversion=r.conversion,
                    passed_gate=False,
                )
                if r is rung else r
                for r in rungs
            ]
    return rungs


def format_ladder(rungs: list[LadderRung]) -> str:
    lines = ["OFFER LADDER"]
    for rung in rungs:
        gate = "OK " if rung.passed_gate else "GATE"
        lines.append(
            f"  [{gate}] {rung.step:10s} {rung.price_band:10s} {rung.asset}"
        )
        lines.append(f"           purpose: {rung.purpose}")
        lines.append(f"           convert: {rung.conversion}")
    return "\n".join(lines)
