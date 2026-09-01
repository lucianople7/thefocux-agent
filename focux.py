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


def console_safe(text: str) -> str:
    """LLM output is not ASCII-safe: DeepSeek drafts contain '->' arrows,
    emoji etc. that crash Windows cp1252 consoles. Fold only the characters
    cp1252 cannot encode (keeps Spanish accents, replaces the rest with '?')."""
    try:
        return text.encode("cp1252", errors="replace").decode("cp1252")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text.encode("ascii", errors="replace").decode("ascii")


def refresh_focus(workspace: str) -> None:
    """Keep .focux/focus.md fresh so ANY agent reads the current directed
    intelligence (goals, gaps, evidence, state). Never fatal."""
    try:
        from runtime.focus import focus_pack, write_focus_file
        from runtime.memory import FocuxMemory

        mem = FocuxMemory(REPO_ROOT / "memory" / "focux.db")
        try:
            write_focus_file(focus_pack(mem, workspace))
        finally:
            mem.close()
    except Exception:  # noqa: BLE001 - focus is an enhancement, never fatal
        pass


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


def build_agent(workspace: str | None = None) -> FocuxAgent:
    """Agent bound to the shared SQLite memory and the current workspace.

    The workspace is auto-detected from the nearest `.focux-workspace`
    marker (declared by `focux attach <dir> --workspace <name>`), so every
    command inside an attached project uses that project's memory namespace.
    """
    from runtime.attach import detect_workspace
    from runtime.memory import FocuxMemory

    ws = workspace or detect_workspace()
    skills = load_skills(REPO_ROOT / "skills")
    memory = FocuxMemory(REPO_ROOT / "memory" / "focux.db")
    return FocuxAgent(
        llm=build_llm(), gate=default_gate(), skills=skills,
        memory=memory, workspace=ws,
    )


def cmd_run(args: argparse.Namespace) -> int:
    agent = build_agent()
    refresh_focus(agent.workspace)
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
        print(console_safe(draft))
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
            print(console_safe(agent.draft(line)))
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
            print(console_safe(result.content))
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
        workspace_name=args.workspace,
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


def cmd_install(args: argparse.Namespace) -> int:
    """Global CLI install: portable launchers + (optional) user-level MCP."""
    from runtime.install import default_prefix, install_launchers, register_user_mcp

    prefix = Path(args.prefix).resolve() if args.prefix else default_prefix()
    created = install_launchers(prefix, REPO_ROOT)
    print(f"THE FOCUX CLI installed to {prefix}:")
    for path in created:
        print(f"  + {path}")
    print("\nAdd it to your PATH (once):")
    if os.name == "nt":
        print(f'  setx PATH "%PATH%;{prefix}"')
    else:
        print(f'  export PATH="{prefix}:$PATH"')
    if args.mcp:
        from runtime.install import user_mcp_registered

        report = register_user_mcp(REPO_ROOT)
        print("\nMCP registration (user level, ANY agent):")
        for item in report.created:
            print(f"  + {item}")
        for item in report.updated:
            print(f"  ~ {item}")
        for item in report.skipped:
            print(f"  = {item}")
        for note in report.notes:
            print(f"  note: {note}")
        status = user_mcp_registered()
        print("\n  agents with thefocux MCP registered:")
        for agent, registered in status.items():
            mark = "OK " if registered else "no "
            print(f"    [{mark}] {agent}")
        if not any(status.values()):
            print("  (none found yet - re-run after the writes or check paths)")
    # verify: the launcher answers
    import subprocess

    launcher = prefix / "focux"
    probe = subprocess.run(
        [sys.executable, str(launcher), "--help"],
        capture_output=True, text=True, timeout=60,
    )
    if probe.returncode == 0 and "usage" in probe.stdout:
        print(f"\nVERIFIED: {launcher} answers (focux --help -> OK)")
        return 0
    print(f"\nWARNING: launcher probe failed (rc={probe.returncode})")
    return 1


def cmd_objective(args: argparse.Namespace) -> int:
    """Objective Brain: measurable goals the brain drives toward."""
    from runtime.attach import detect_workspace
    from runtime.memory import FocuxMemory

    workspace = args.workspace or detect_workspace()
    mem = FocuxMemory(REPO_ROOT / "memory" / "focux.db")
    try:
        if args.action == "add":
            obj = mem.add_objective(
                workspace, args.title, args.kpi, args.target,
                unit=args.unit, deadline=args.deadline,
            )
            print(f"objective added [{obj.objective_id}]: {obj.title} | "
                  f"{obj.kpi}: 0/{obj.target:.0f}{(' ' + obj.unit) if obj.unit else ''}"
                  f" | deadline {obj.deadline or 'none'}")
            return 0

        if args.action == "list":
            for obj in mem.objectives(workspace):
                print(f"  [{obj.objective_id}] {obj.title} | {obj.kpi}: "
                      f"{obj.current:.0f}/{obj.target:.0f}"
                      f"{(' ' + obj.unit) if obj.unit else ''}")
            if not mem.objectives(workspace):
                print("  (no objectives - add one: focux objective add '<title>' "
                      "--kpi <kpi> --target <n>)")
            return 0

        if args.action == "status":
            from runtime.objectives import format_status, objective_status
            print(format_status(objective_status(mem, workspace)))
            return 0

        if args.action == "set":
            obj = mem.update_objective_current(workspace, args.id, args.current)
            if obj is None:
                print(f"no objective '{args.id}' in workspace '{workspace}'")
                return 2
            print(f"[{obj.objective_id}] {obj.title} | {obj.kpi}: "
                  f"{obj.current:.0f}/{obj.target:.0f} "
                  f"({obj.progress() * 100:.0f}%) - measured")
            return 0

        if args.action == "drive":
            from runtime.objectives import drive, format_drive

            agent = build_agent(workspace=workspace)
            report = drive(agent, workspace, objective_id=args.id,
                           limit=args.limit, tier=args.tier)
            print(format_drive(report))
            return 0
        return 2
    finally:
        mem.close()


def cmd_expert(args: argparse.Namespace) -> int:
    """Expert Panel: world-class domain expertise (ask + quality review)."""
    from runtime.attach import detect_workspace
    from runtime.experts import ask_expert, list_experts, review_draft

    workspace = getattr(args, "workspace", "") or detect_workspace()
    if args.action == "list":
        for expert in list_experts():
            print(f"  - {expert['domain']:14s} {expert['title']}"
                  + (f"  [{expert['playbook']}]" if expert["playbook"] else ""))
        return 0

    agent = build_agent(workspace=workspace)
    if args.action == "ask":
        answer = ask_expert(agent, args.domain, args.question, workspace)
        print(f"[{answer.decision}] {answer.domain} expert:")
        print(console_safe(answer.answer))
        return 0

    if args.action == "review":
        verdict = review_draft(agent, args.domain, args.draft, workspace)
        print(f"REVIEW [{args.domain}] -> {verdict.verdict}")
        for item in verdict.items:
            mark = "ok " if item.passed else "FAIL"
            print(f"  [{mark}] {item.item} - {item.reason}")
        if verdict.judge_reason:
            print(f"  judge: {verdict.judge_reason}")
        return 0 if verdict.passed else 1
    return 2


def cmd_focus(args: argparse.Namespace) -> int:
    """FOCUS: directed intelligence for ANY agent — real goals, gaps, evidence."""
    from runtime.attach import detect_workspace
    from runtime.focus import focus_pack, format_focus, write_focus_file
    from runtime.memory import FocuxMemory
    from runtime.survival import BusinessFinances, survival_tier

    workspace = getattr(args, "workspace", "") or detect_workspace()
    tier = ""
    if args.tier:
        tier = args.tier
    elif args.revenue is not None:
        tier = survival_tier(BusinessFinances(
            revenue=args.revenue, operating_cost=args.cost, cash=args.cash,
        )).value
    mem = FocuxMemory(REPO_ROOT / "memory" / "focux.db")
    try:
        pack = focus_pack(mem, workspace, tier=tier)
    finally:
        mem.close()
    print(format_focus(pack))
    path = write_focus_file(pack)
    print(f"\n(refreshed: {path})")
    return 0


def cmd_work(args: argparse.Namespace) -> int:
    """Work Harness: durable, stage-gated work (frame->plan->execute->verify)."""
    from runtime.attach import detect_workspace
    from runtime.workflow import (
        approve, execute, frame, load_state, plan, resume_text, status_text,
        validate, verify, work_root,
    )

    workspace = getattr(args, "workspace", "") or detect_workspace()
    root = work_root()
    action = args.action
    refresh_focus(workspace)

    if action == "status":
        print(status_text(root))
        return 0

    if action == "resume":
        print(resume_text(root))
        return 0

    if action == "validate":
        issues = validate(root)
        if not issues:
            print("VALID: .focux/work state is consistent")
            return 0
        for issue in issues:
            print(f"  [FAIL] {issue}")
        return 1

    agent = build_agent(workspace=workspace)
    state = load_state(root)

    if action == "frame":
        try:
            state = frame(agent, args.objective, domain=args.domain,
                          workspace=workspace, force=args.force)
        except ValueError as exc:
            print(f"cannot frame: {exc}")
            return 2
        print(f"FRAMED -> {state.spec_path}")
        print("SPEC draft written. YOUR approval is the product review "
              "(no model gate): focux work approve")
        return 0

    if action == "approve":
        if state is None:
            print("no work to approve - run `focux work frame '<objective>'`")
            return 2
        state = approve(state)
        print(f"SPEC approved (product review) - stage: {state.stage}")
        print("next: focux work plan")
        return 0

    if action == "plan":
        if state is None:
            print("no work - run `focux work frame '<objective>'`")
            return 2
        state = plan(agent, state, workspace=workspace)
        print(f"PLANNED -> {state.plan_path}")
        print("next: focux work execute")
        return 0

    if action == "execute":
        if state is None:
            print("no work - run `focux work frame '<objective>'`")
            return 2
        gated = execute(agent, state, workspace=workspace)
        print(f"EXECUTE (stage: {state.stage}) - plan steps gated:")
        for step in gated:
            print(f"  [{step['decision']}] ({step['pillar']}) {step['action']}")
        reviews = [s for s in gated if s["decision"] == "REVIEW"]
        if reviews:
            print("REVIEW steps need human approval; ALLOW steps are yours "
                  "to do across sessions. Close with: focux work verify")
        return 0

    if action == "verify":
        if state is None:
            print("no work - run `focux work frame '<objective>'`")
            return 2
        state = verify(agent, state, workspace=workspace,
                       confirm=getattr(args, "confirm", False))
        if state.stage == "verified":
            print(f"VERIFIED ('{state.objective}') - harness disengaged. "
                  "Next sessions open quiet.")
        else:
            print(f"verification did not pass - back to {state.stage}. "
                  "Fix and re-run: focux work verify")
        return 0 if state.stage == "verified" else 1
    return 2


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
        check("memory", True, f"workspace '{agent.workspace}' (SQLite)")
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

    # user-level MCP registration (`focux install --mcp`) — info, not critical
    from runtime.install import user_mcp_registered
    for agent, registered in user_mcp_registered().items():
        detail = "registered" if registered else "not registered (focux install --mcp)"
        print(f"  [info] user MCP {agent}: {detail}")

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
    from runtime.attach import detect_workspace
    from runtime.evolution import format_report, run_daily_evolution

    workspace = args.workspace or detect_workspace()
    report = run_daily_evolution(
        workspace=workspace,
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
                print(f"[{asset.id}]\n{console_safe(asset.draft[:300])}\n")
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

    from runtime.attach import detect_workspace
    from runtime.ingest import absorb, format_absorb, store_results

    sources = tuple(s.strip().lower() for s in args.sources.split(",") if s.strip())
    if not sources:
        print("usage: focux absorb --sources github,huggingface,x [--query 'ai agent']")
        return 2
    workspace = args.workspace or detect_workspace()
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
        stored = store_results(results, mem, workspace=workspace)
    finally:
        mem.close()
    ok_sources = [s for s, r in results.items() if r.ok]
    print(f"\nabsorbed into memory ({workspace}): {stored} items "
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

    objective = sub.add_parser("objective", help="Objective Brain: measurable goals the brain drives toward")
    osub = objective.add_subparsers(dest="action", required=True)
    oadd = osub.add_parser("add", help="add an objective")
    oadd.add_argument("title")
    oadd.add_argument("--kpi", required=True, help="metric (followers, revenue, leads...)")
    oadd.add_argument("--target", type=float, required=True)
    oadd.add_argument("--unit", default="")
    oadd.add_argument("--deadline", default="", help="ISO date YYYY-MM-DD")
    oadd.add_argument("--workspace", default="")
    oadd.set_defaults(func=cmd_objective)
    olist = osub.add_parser("list", help="list objectives")
    olist.add_argument("--workspace", default="")
    olist.set_defaults(func=cmd_objective)
    ostatus = osub.add_parser("status", help="progress, gap, overdue, momentum")
    ostatus.add_argument("--workspace", default="")
    ostatus.set_defaults(func=cmd_objective)
    oset = osub.add_parser("set", help="MEDIR: record the current KPI value")
    oset.add_argument("id")
    oset.add_argument("--current", type=float, required=True)
    oset.add_argument("--workspace", default="")
    oset.set_defaults(func=cmd_objective)
    odrive = osub.add_parser("drive", help="INTELLIGENCE: gap analysis -> gated plan (LLM)")
    odrive.add_argument("--id", default="", help="one objective id (default: all)")
    odrive.add_argument("--limit", type=int, default=3)
    odrive.add_argument("--tier", default="normal")
    odrive.add_argument("--workspace", default="")
    odrive.set_defaults(func=cmd_objective)

    expert = sub.add_parser("expert", help="Expert Panel: world-class domain expertise")
    esub = expert.add_subparsers(dest="action", required=True)
    elist = esub.add_parser("list", help="list the domain experts + playbooks")
    elist.set_defaults(func=cmd_expert)
    eask = esub.add_parser("ask", help="consult a domain expert (LLM, gated READ)")
    eask.add_argument("domain", choices=("content", "social", "ecommerce",
                                         "monetization", "opportunities"))
    eask.add_argument("question")
    eask.add_argument("--workspace", default="")
    eask.set_defaults(func=cmd_expert)
    ereview = esub.add_parser("review", help="quality gate: PASS/REVISE a draft")
    ereview.add_argument("domain", choices=("content", "social", "ecommerce",
                                            "monetization", "opportunities"))
    ereview.add_argument("draft", help="the draft to review")
    ereview.add_argument("--workspace", default="")
    ereview.set_defaults(func=cmd_expert)

    work = sub.add_parser("work", help="Work Harness: durable stage-gated work (Automaton mindset)")
    wsub = work.add_subparsers(dest="action", required=True)
    wframe = wsub.add_parser("frame", help="write SPEC.md (draft); YOU approve it = product review")
    wframe.add_argument("objective")
    wframe.add_argument("--domain", default="code", choices=("code", "content"))
    wframe.add_argument("--force", action="store_true", help="replace existing active work")
    wframe.add_argument("--workspace", default="")
    wframe.set_defaults(func=cmd_work)
    wapprove = wsub.add_parser("approve", help="approve SPEC.md (product review, no model gate)")
    wapprove.set_defaults(func=cmd_work)
    wplan = wsub.add_parser("plan", help="write PLAN.md (gated steps)")
    wplan.add_argument("--workspace", default="")
    wplan.set_defaults(func=cmd_work)
    wexec = wsub.add_parser("execute", help="gate every plan step before doing it")
    wexec.add_argument("--workspace", default="")
    wexec.set_defaults(func=cmd_work)
    wverify = wsub.add_parser("verify", help="run real checks -> verified (terminal)")
    wverify.add_argument("--confirm", action="store_true",
                         help="verify by human confirmation when no auto checks")
    wverify.add_argument("--workspace", default="")
    wverify.set_defaults(func=cmd_work)
    wstatus = wsub.add_parser("status", help="session-start honesty: where the work is")
    wstatus.set_defaults(func=cmd_work)
    wresume = wsub.add_parser("resume", help="re-enter existing work from a fresh session")
    wresume.set_defaults(func=cmd_work)
    wvalid = wsub.add_parser("validate", help="consistency check of the work state")
    wvalid.set_defaults(func=cmd_work)

    focus = sub.add_parser("focus", help="directed intelligence: real goals, gaps, evidence, state")
    focus.add_argument("--workspace", default="",
                       help="workspace (default: auto-detect from .focux-workspace)")
    focus.add_argument("--tier", default="",
                       help="override survival tier (default: none)")
    focus.add_argument("--revenue", type=float, default=None,
                       help="revenue to compute the tier")
    focus.add_argument("--cost", type=float, default=0.0)
    focus.add_argument("--cash", type=float, default=0.0)
    focus.set_defaults(func=cmd_focus)

    attach = sub.add_parser("attach", help="mount THE FOCUX BRAIN on any agent/business dir")
    attach.add_argument("dir", help="target directory")
    attach.add_argument("--agents", default="all",
                        help="comma list: all,claude,codex,cursor,aider,copilot,gemini")
    attach.add_argument("--workspace", default="",
                        help="business workspace name (memory namespace); "
                             "defaults to the directory name")
    attach.add_argument("--force", action="store_true",
                        help="refresh files THE FOCUX owns (safe merges for configs)")
    attach.add_argument("--no-mcp", action="store_true",
                        help="skip MCP server registration")
    attach.set_defaults(func=cmd_attach)

    install = sub.add_parser("install", help="global CLI: portable launchers on PATH (+ MCP)")
    install.add_argument("--prefix", default="",
                         help="bin dir (default ~/.thefocux/bin)")
    install.add_argument("--mcp", action="store_true",
                         help="register thefocux MCP at user level (Codex)")
    install.set_defaults(func=cmd_install)

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
    evolve.add_argument("--workspace", default="",
                        help="workspace (default: auto-detect from .focux-workspace)")
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
    absorb.add_argument("--workspace", default="",
                        help="workspace (default: auto-detect from .focux-workspace)")
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
