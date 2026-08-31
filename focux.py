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


def cmd_agents(args: argparse.Namespace) -> int:
    """List the 9 specialized business roles (+ due now / run one)."""
    from datetime import datetime

    from runtime.orchestrator import all_roles, due_roles, role_named

    if args.run:
        agent = build_agent()
        role = role_named(args.run)
        if role is None:
            print(f"unknown role: {args.run}")
            return 2
        result = agent.run_role(args.run, objective=args.objective)
        print(f"[{result.decision}] {result.summary}")
        if result.content:
            print(result.content)
        return 0 if result.ok else 1

    now = datetime.now()
    due = {r.name for r in due_roles(now)}
    for role in all_roles():
        marker = " ◀ due now" if role.name in due else ""
        print(
            f"- {role.name:20s} {role.pillar:12s} "
            f"{role.action_class.value:10s} {role.cadence:12s} "
            f"skill={role.skill}{marker}"
        )
    print(f"\n{len(all_roles())} roles · run one: python -m focux agents --run <name>")
    return 0


def cmd_attach(args: argparse.Namespace) -> int:
    """Mount THE FOCUX BRAIN on any agent/business directory."""
    import shutil

    target = Path(args.dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    mounted: list[str] = []

    # AGENTS.md (identity contract)
    agents_md = target / "AGENTS.md"
    if not agents_md.exists():
        shutil.copy2(REPO_ROOT / "AGENTS.md", agents_md)
        mounted.append("AGENTS.md")

    # focux-brain metaskill (the identity the agent loads)
    brain_skill = target / ".agents" / "skills" / "focux-brain"
    if not brain_skill.exists():
        brain_skill.mkdir(parents=True, exist_ok=True)
        shutil.copy2(
            REPO_ROOT / "skills" / "focux-brain" / "SKILL.md",
            brain_skill / "SKILL.md",
        )
        mounted.append(".agents/skills/focux-brain/SKILL.md")

    # constitution (immutable laws)
    constitution = target / "constitution.md"
    if not constitution.exists():
        shutil.copy2(REPO_ROOT / "constitution.md", constitution)
        mounted.append("constitution.md")

    # memory dir (shared business memory)
    memory_dir = target / "memory"
    if not memory_dir.exists():
        memory_dir.mkdir(parents=True, exist_ok=True)
        (memory_dir / "README.md").write_text(
            "FOCUX BRAIN shared memory: metrics.md, decisions.md, receipts/, "
            "focux.db (SQLite), selfmod.jsonl (audit).",
            encoding="utf-8",
        )
        mounted.append("memory/")

    if not mounted:
        print("already attached (AGENTS.md, brain skill, constitution, memory present)")
        return 0
    print(f"THE FOCUX BRAIN attached to {target}:")
    for item in mounted:
        print(f"  + {item}")
    print("\nNow any agent in that directory reads AGENTS.md + the brain skill.")
    return 0


def cmd_heartbeat(args: argparse.Namespace) -> int:
    """Heartbeat report: survival tier + roles due + approvals."""
    from runtime.heartbeat import format_report, heartbeat
    from runtime.survival import BusinessFinances

    finances = BusinessFinances(
        revenue=args.revenue,
        operating_cost=args.cost,
        cash=args.cash,
    )
    report = heartbeat(finances, pending_approvals=args.approvals)
    print(format_report(report))
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

    agents = sub.add_parser("agents", help="list/run the 9 specialized business roles")
    agents.add_argument("--run", default="", help="run one role (gated)")
    agents.add_argument("--objective", default="", help="objective for --run")
    agents.set_defaults(func=cmd_agents)

    attach = sub.add_parser("attach", help="mount THE FOCUX BRAIN on any agent/business dir")
    attach.add_argument("dir", help="target directory")
    attach.set_defaults(func=cmd_attach)

    hb = sub.add_parser("heartbeat", help="survival tier + roles due + approvals")
    hb.add_argument("--revenue", type=float, default=0.0)
    hb.add_argument("--cost", type=float, default=0.0)
    hb.add_argument("--cash", type=float, default=0.0)
    hb.add_argument("--approvals", type=int, default=0)
    hb.set_defaults(func=cmd_heartbeat)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
