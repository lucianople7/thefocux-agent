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

    try:
        target = promote_skill(
            REPO_ROOT / "skills-draft", REPO_ROOT / "skills", args.name
        )
    except FileNotFoundError:
        print(f"no draft skill named '{args.name}' (check: focux drafts)")
        return 2
    except ValueError as exc:
        print(f"cannot promote: {exc}")
        return 2
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
    """Mount THE FOCUX BRAIN on any agent/business directory (universal)."""
    from runtime.attach import AGENTS, attach

    agents = tuple(a.strip() for a in args.agents.split(",") if a.strip())
    report = attach(
        Path(args.dir).resolve(),
        REPO_ROOT,
        agents=agents,
        force=args.force,
        with_mcp=not args.no_mcp,
    )
    target = Path(args.dir).resolve()
    if not report.changed:
        print(f"already attached ({target}): all brain files present")
        for note in report.notes:
            print(f"  note: {note}")
        return 0
    print(f"THE FOCUX BRAIN attached to {target}:")
    for item in report.created:
        print(f"  + {item}")
    for item in report.updated:
        print(f"  ~ {item} (refreshed)")
    for item in report.skipped:
        print(f"  = {item} (already present)")
    for note in report.notes:
        print(f"  note: {note}")
    names = ", ".join(
        label for aid, label in AGENTS.items()
        if aid in agents or "all" in agents
    )
    print(f"\nAgents covered: {names}")
    print("Now ANY coding agent in that directory reads AGENTS.md + the brain")
    print("skill, shares the SQLite memory, and can call the MCP tools.")
    print("Configure: .env -> add your API key. Verify: focux doctor --target <dir>")
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


def cmd_doctor(args: argparse.Namespace) -> int:
    """Brain diagnostics: skills, gates, memory, providers, MCP, survival.

    With ``--target <dir>`` it also verifies an ATTACHED workspace end-to-end
    (the universal installer's contract).
    """
    ok = True

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        status = "OK " if cond else "FAIL"
        if not cond:
            ok = False
        print(f"  [{status}] {label}" + (f" - {detail}" if detail else ""))

    print("THE FOCUX BRAIN - doctor")

    # skills
    agent = build_agent()
    check("skills", len(agent.skills) >= 17, f"{len(agent.skills)} loaded")

    # gates
    gate = default_gate()
    check("money-gate falsification", gate.falsification_test(),
          "never auto-approves money")

    # memory
    mem = agent.memory
    if mem is not None:
        check("memory", True, f"workspace '{agent.workspace}'")
    else:
        check("memory", True, "not attached (optional)")

    # provider
    settings = load_settings(REPO_ROOT)
    check("provider", settings.provider in ("deepseek", "qwen", "openai", "ollama", "custom"),
          f"{settings.provider} ({settings.model})")

    # orchestrator
    from runtime.orchestrator import all_roles
    roles = all_roles()
    check("orchestrator", len(roles) >= 11, f"{len(roles)} roles")

    # survival
    from runtime.survival import BusinessFinances, survival_tier
    tier = survival_tier(BusinessFinances(revenue=0, operating_cost=0, cash=0))
    check("survival", tier.value in ("high", "normal", "low_compute", "critical", "dead"),
          f"engine ok (zero-cost => {tier.value})")

    # selfmod
    from runtime.selfmod import SelfModLog
    log = SelfModLog()
    check("selfmod audit", log.count() >= 0, f"{log.count()} entries")

    # MCP bridge: real stdio handshake (initialize + tools/list + gate call)
    import subprocess
    try:
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "mcp_bridge.py"), "--selfcheck"],
            capture_output=True, text=True, timeout=60,
        )
        mcp_ok = proc.returncode == 0 and "MCP OK" in proc.stdout
        check("MCP bridge handshake", mcp_ok,
              proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "no output")
        if not mcp_ok:
            check("MCP bridge stderr", False,
                  (proc.stderr or "").strip()[:200])
    except Exception as exc:  # noqa: BLE001
        check("MCP bridge handshake", False, f"{type(exc).__name__}: {exc}")

    # attached workspace verification (universal installer contract)
    if args.target:
        from runtime.attach import verify_attached
        print(f"\n  attached workspace: {Path(args.target).resolve()}")
        vrep = verify_attached(Path(args.target).resolve(), REPO_ROOT)
        for c in vrep.checks:
            if c.critical:
                check(c.label, c.ok, c.detail)
            else:
                print(f"  [info] {c.label}" + (f" - {c.detail}" if c.detail else ""))
        if not vrep.ok:
            ok = False

    print("RESULT: " + ("OK - THE FOCUX BRAIN is operational." if ok else "ISSUES FOUND"))
    return 0 if ok else 1


def cmd_evolve(args: argparse.Namespace) -> int:
    """Daily evolution cycle: analyze executed work, propose improvements."""
    from runtime.evolution import format_report, run_daily_evolution

    report = run_daily_evolution(
        workspace=args.workspace,
        memory_dir=REPO_ROOT / "memory",
        drafts_dir=REPO_ROOT / "skills-draft",
    )
    print(format_report(report))
    return 0


def cmd_multiply(args: argparse.Namespace) -> int:
    """1 asset -> 20+ distributable outputs (the revenue multiplier)."""
    from runtime.repurpose import format_plan, multiply

    if not args.insight:
        print("usage: focux multiply '<core insight>' [--offer '<offer>'] [--draft]")
        return 2
    write = None
    if args.draft:
        agent = build_agent()

        def _write(asset, insight, offer):
            return agent.draft(
                f"Write the {asset.format} for platform {asset.platform}. "
                f"Brief: {asset.brief}. CTA: {asset.cta}. "
                f"Core insight: {insight}. "
                + (f"Offer: {offer}." if offer else ""),
                skill_name="post-writer",
            )

        write = _write
    assets = multiply(args.insight, offer=args.offer, write=write)
    print(format_plan(assets))
    if args.draft:
        print("\n--- drafts ---")
        for asset in assets:
            if asset.draft:
                print(f"[{asset.id}]\n{asset.draft[:300]}\n")
    return 0


def cmd_offer(args: argparse.Namespace) -> int:
    """The 5-rung offer ladder: attention -> revenue."""
    from runtime.offer import build_ladder, format_ladder

    ladder = build_ladder(business=args.business)
    print(format_ladder(ladder))
    return 0


def cmd_absorb(args: argparse.Namespace) -> int:
    """Absorb REAL data from GitHub / Hugging Face / X into memory."""
    import os

    from runtime.ingest import absorb, format_absorb, store_results

    sources = tuple(s.strip().lower() for s in args.sources.split(",") if s.strip())
    if not sources:
        print("usage: focux absorb --sources github,huggingface,x [--query 'ai agent']")
        return 2
    x_bearer = os.environ.get("X_BEARER_TOKEN", "")
    results = absorb(
        sources=sources,
        github_query=args.query,
        x_bearer=x_bearer,
        x_query=args.query,
        limit=args.limit,
    )
    print(format_absorb(results))

    # store into memory so the brain can ANALIZAR with real signals
    from runtime.memory import FocuxMemory

    mem = FocuxMemory(REPO_ROOT / "memory" / "focux.db")
    try:
        stored = store_results(results, mem, workspace=args.workspace)
    finally:
        mem.close()
    ok_sources = [s for s, r in results.items() if r.ok]
    print(f"\nabsorbed into memory ({args.workspace}): {stored} items "
          f"from {', '.join(ok_sources) or 'no source'}")
    return 0 if ok_sources else 1


def cmd_modules(args: argparse.Namespace) -> int:
    """Modular system: every brain organ registered + integrity check."""
    from runtime.modules import all_modules, integrity_check

    for module in all_modules():
        deps = f" deps={','.join(module.deps)}" if module.deps else ""
        print(f"- {module.id:14s} v{module.version:5s} {module.description}{deps}")

    check = integrity_check()
    print(f"\nINTEGRITY: {check['count']} checks, "
          + ("ALL OK" if check["ok"] else f"{sum(1 for m in check['modules'] if not m['ok'])} FAILED"))
    return 0 if check["ok"] else 1


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
    attach.add_argument("--agents", default="all",
                        help="comma list: all,claude,codex,cursor,aider,copilot,gemini")
    attach.add_argument("--force", action="store_true",
                        help="refresh files THE FOCUX owns (safe merges for configs)")
    attach.add_argument("--no-mcp", action="store_true",
                        help="skip MCP server registration")
    attach.set_defaults(func=cmd_attach)

    hb = sub.add_parser("heartbeat", help="survival tier + roles due + approvals")
    hb.add_argument("--revenue", type=float, default=0.0)
    hb.add_argument("--cost", type=float, default=0.0)
    hb.add_argument("--cash", type=float, default=0.0)
    hb.add_argument("--approvals", type=int, default=0)
    hb.set_defaults(func=cmd_heartbeat)

    doctor = sub.add_parser("doctor", help="THE FOCUX BRAIN diagnostics")
    doctor.add_argument("--target", default="",
                        help="verify an attached workspace (focux attach <dir>)")
    doctor.set_defaults(func=cmd_doctor)

    evolve = sub.add_parser("evolve", help="daily evolution cycle (analyze -> improve)")
    evolve.add_argument("--workspace", default="default")
    evolve.set_defaults(func=cmd_evolve)

    modules = sub.add_parser("modules", help="modular system: organs + integrity check")
    modules.set_defaults(func=cmd_modules)

    multiply = sub.add_parser("multiply", help="1 asset -> 20+ outputs (revenue multiplier)")
    multiply.add_argument("insight", help="core insight to multiply")
    multiply.add_argument("--offer", default="", help="offer for the CTAs")
    multiply.add_argument("--draft", action="store_true", help="draft each output via LLM")
    multiply.set_defaults(func=cmd_multiply)

    offer = sub.add_parser("offer", help="5-rung offer ladder: attention -> revenue")
    offer.add_argument("--business", default="the business")
    offer.set_defaults(func=cmd_offer)

    absorb = sub.add_parser("absorb", help="absorb REAL data (github/huggingface/x) into memory")
    absorb.add_argument("--sources", default="github,huggingface",
                        help="comma list: github,huggingface,x")
    absorb.add_argument("--query", default="ai agent", help="search query")
    absorb.add_argument("--limit", type=int, default=10)
    absorb.add_argument("--workspace", default="default")
    absorb.set_defaults(func=cmd_absorb)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # Downstream closed the pipe early (e.g. `focux ... | head`):
        # exit quietly like standard Unix tools instead of crashing.
        import os

        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 1)
        raise SystemExit(0)
