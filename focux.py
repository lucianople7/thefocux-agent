"""FOCUX CLI — drive the agent from the terminal.

Two modes:

- ``python -m focux run "objective"`` — one-shot: propose + optionally draft.
- ``python -m focux repl`` — interactive session with the agent.
- ``python -m focux skills`` — list loaded skills.

Provider selection (agnostic):
- ``FOCUX_MODEL`` / ``FOCUX_BASE_URL`` / ``FOCUX_API_KEY`` -> OpenAI-compatible
- ``FOCUX_OLLAMA=1`` (default when no env is set) -> local Ollama
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from policy.money_gate import ActionClass, MoneyGate, PolicyRule  # noqa: E402
from runtime.agent import FocuxAgent  # noqa: E402
from runtime.config import load_settings  # noqa: E402
from runtime.llm import LLMClient, OllamaClient, OpenAICompatClient  # noqa: E402
from runtime.skills import load_skills  # noqa: E402


def default_gate() -> MoneyGate:
    """L1 table: money/commerce/account/content REVIEW; read auto-approve."""
    return MoneyGate(
        {
            # auto_approve rules MUST declare a bound (falsification invariant)
            ActionClass.READ: PolicyRule(
                ActionClass.READ, max_amount=0.0, auto_approve=True
            ),
            ActionClass.CONTENT: PolicyRule(ActionClass.CONTENT),
            ActionClass.COMMERCE: PolicyRule(ActionClass.COMMERCE),
            ActionClass.MONEY: PolicyRule(ActionClass.MONEY),
            ActionClass.ACCOUNT: PolicyRule(ActionClass.ACCOUNT),
        }
    )


def build_llm() -> LLMClient:
    settings = load_settings(REPO_ROOT)
    if settings.provider == "ollama" and settings.keyless:
        return OllamaClient(model=settings.model)
    return OpenAICompatClient(
        base_url=settings.base_url,
        api_key=settings.api_key,
        model=settings.model,
    )


def build_agent() -> FocuxAgent:
    skills = load_skills(REPO_ROOT / "skills")
    return FocuxAgent(llm=build_llm(), gate=default_gate(), skills=skills)


def cmd_run(args: argparse.Namespace) -> int:
    agent = build_agent()
    print(f"THE FOCUX Agent — skills loaded: {len(agent.skills)}")
    result = agent.propose(
        pillar=args.pillar,
        objective=args.objective,
        amount=args.amount,
        content=args.content,
    )
    print(f"gate: {result.decision}")
    print(f"summary: {result.summary}")
    if args.draft and result.decision in ("ALLOW", "REVIEW"):
        draft = agent.draft(args.objective)
        print("\n--- draft ---")
        print(draft)
    return 0 if result.ok else 1


def cmd_repl(args: argparse.Namespace) -> int:
    agent = build_agent()
    print(f"THE FOCUX Agent REPL — {len(agent.skills)} skills loaded. "
          "Type 'exit' to quit.")
    while True:
        try:
            line = input("focux> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in ("exit", "quit"):
            break
        if line.lower() == "skills":
            for skill in agent.skills:
                print(f"- {skill.name}: {skill.description[:60]}")
            continue
        result = agent.propose(pillar=args.pillar, objective=line)
        print(f"[{result.decision}] {result.summary}")
        if result.decision == "ALLOW":
            print(agent.draft(line))
    return 0


def cmd_skills(args: argparse.Namespace) -> int:
    agent = build_agent()
    for skill in agent.skills:
        print(f"- {skill.name}: {skill.description[:80]}")
    print(f"\n{len(agent.skills)} skills loaded from skills/")
    return 0


def cmd_drafts(args: argparse.Namespace) -> int:
    from runtime.skills import list_drafts

    drafts = list_drafts(REPO_ROOT / "skills-draft")
    if not drafts:
        print("no drafts (the agent has not crystallized anything yet)")
        return 0
    for skill in drafts:
        print(f"- {skill.name} (DRAFT): {skill.description[:60]}")
    print(f"\n{len(drafts)} draft(s). Promote with: python -m focux promote <name>")
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    from runtime.skills import promote_skill

    target = promote_skill(
        REPO_ROOT / "skills-draft", REPO_ROOT / "skills", args.name
    )
    print(f"promoted {args.name} -> {target}")
    print("HUMAN REVIEW: the skill is now active in skills/. Review it first.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="focux", description="THE FOCUX Agent")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="one-shot proposal + optional draft")
    run.add_argument("objective")
    run.add_argument("--pillar", default="content",
                     help="content|commerce|monetization|research|account")
    run.add_argument("--amount", type=float, default=0.0)
    run.add_argument("--content", default="")
    run.add_argument("--draft", action="store_true", help="also draft via LLM")
    run.set_defaults(func=cmd_run)

    repl = sub.add_parser("repl", help="interactive session")
    repl.add_argument("--pillar", default="content")
    repl.set_defaults(func=cmd_repl)

    skills = sub.add_parser("skills", help="list loaded skills")
    skills.set_defaults(func=cmd_skills)

    drafts = sub.add_parser("drafts", help="list crystallized draft skills")
    drafts.set_defaults(func=cmd_drafts)

    promote = sub.add_parser("promote", help="promote a DRAFT skill to active (HUMAN review)")
    promote.add_argument("name")
    promote.set_defaults(func=cmd_promote)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
