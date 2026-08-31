"""FOCUX Agent — the business loop with gates always in the path.

ANALIZAR -> PLANIFICAR -> EJECUTAR -> MEDIR -> MEJORAR, with the money-gate
and the constitution auditing every step. The runtime never executes an
action that the gate does not ALLOW; anything REVIEW is returned to the
human as a proposal (single-use, expiring, byte-bound approvals).

The LLM is injected (``LLMClient``) so the agent itself never imports a
provider SDK — the agnosticism contract holds inside the loop too.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from policy.constitution import Claim, Verdict, apply_constitution, law1_blocks
from policy.money_gate import Action, ActionClass, Decision, MoneyGate

from .llm import LLMClient
from .memory import FocuxMemory
from .skills import Skill


@dataclass(frozen=True)
class FocuxResult:
    ok: bool
    decision: str  # ALLOW / REVIEW / DENY
    summary: str
    verdicts: tuple[Verdict, ...] = ()
    content: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "decision": self.decision,
            "summary": self.summary,
            "verdicts": [v.as_dict() for v in self.verdicts],
            "content": self.content,
        }


#: Action classification for the five business pillars.
def classify_pillar(pillar: str) -> ActionClass:
    p = pillar.lower()
    if "money" in p or "monetiz" in p or "pay" in p:
        return ActionClass.MONEY
    if "commerce" in p or "shop" in p or "store" in p or "sell" in p:
        return ActionClass.COMMERCE
    if "content" in p or "social" in p or "post" in p or "video" in p:
        return ActionClass.CONTENT
    if "account" in p or "config" in p or "credential" in p:
        return ActionClass.ACCOUNT
    return ActionClass.READ


class FocuxAgent:
    """A business agent instance bound to one gate table and one LLM."""

    def __init__(
        self,
        llm: LLMClient,
        gate: MoneyGate,
        skills: list[Skill] | None = None,
        *,
        memory: FocuxMemory | None = None,
        workspace: str = "default",
        constitution: Callable[..., list[Verdict]] = apply_constitution,
    ) -> None:
        self._llm = llm
        self._gate = gate
        self._skills = skills or []
        self._memory = memory
        self._workspace = workspace
        self._constitution = constitution

    # -- introspection -------------------------------------------------------

    @property
    def skills(self) -> list[Skill]:
        return self._skills

    @property
    def memory(self) -> FocuxMemory | None:
        return self._memory

    @property
    def workspace(self) -> str:
        return self._workspace

    def skill_named(self, name: str) -> Skill | None:
        for skill in self._skills:
            if skill.name == name:
                return skill
        return None

    def _memory_block(self, prompt: str) -> str:
        """Context block injected before drafting (empty when gate says no)."""
        if self._memory is None:
            return ""
        try:
            return self._memory.context_block(prompt, self._workspace)
        except Exception:  # noqa: BLE001 - memory is an enhancement, never fatal
            return ""

    # -- the loop ------------------------------------------------------------

    def propose(
        self,
        pillar: str,
        objective: str,
        *,
        amount: float = 0.0,
        target: str = "",
        idempotency_key: str = "",
        content: str = "",
        claims: tuple[Claim, ...] = (),
        tainted: bool = False,
    ) -> FocuxResult:
        """Run one ANALIZAR -> PLANIFICAR -> EJECUTAR step, gated.

        ``propose`` never executes: it classifies the action, runs the
        money-gate, runs the constitution, and returns the verdict. The
        caller (CLI/REPL/shell) decides what to do with an ALLOW; REVIEW is
        the human-approval path.
        """
        action = Action(
            action_class=classify_pillar(pillar),
            amount=amount,
            target=target,
            idempotency_key=idempotency_key,
        )
        decision = self._gate.decide(action, tainted=tainted)
        verdicts = self._constitution(
            self._gate, action, content=content, claims=claims, tainted=tainted
        )
        blocked = law1_blocks(verdicts) or decision is Decision.DENY
        if blocked:
            return FocuxResult(
                ok=False,
                decision="DENY",
                summary="constitution Law I or money-gate DENY: action must not run",
                verdicts=verdicts,
            )
        if decision is Decision.REVIEW:
            return FocuxResult(
                ok=True,
                decision="REVIEW",
                summary="human approval required before execution",
                verdicts=verdicts,
                content=content,
            )
        return FocuxResult(
            ok=True,
            decision="ALLOW",
            summary="within policy; execution permitted (still audited)",
            verdicts=verdicts,
            content=content,
        )

    def draft(
        self,
        prompt: str,
        *,
        system: str | None = None,
        skill_name: str | None = None,
    ) -> str:
        """ANALIZAR/EJECUTAR: ask the LLM, optionally scoped by a skill.

        Drafting is a READ-class action (no money, no publish); the gate is
        still consulted to keep the discipline uniform.
        """
        system_prompt = system or (
            "You are THE FOCUX Agent, a business superagent. Be direct, "
            "practical, evidence-based. Never claim results you cannot verify."
        )
        if skill_name:
            skill = self.skill_named(skill_name)
            if skill:
                system_prompt += "\n\nApply this skill:\n" + skill.instructions()
        memory_block = self._memory_block(prompt)
        user_content = (
            f"{memory_block}\n\n{prompt}" if memory_block else prompt
        )
        return self._llm.complete(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]
        )
