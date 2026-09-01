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
import json
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


def _out(args: argparse.Namespace, lines: list[str],
         data: object | None = None) -> int:
    """Emit the result: JSON for agents (--json), prose for humans."""
    if getattr(args, "json", False):
        print(json.dumps(data if data is not None else {},
                         ensure_ascii=False, default=str))
    else:
        print("\n".join(lines))
    return 0


def _out_err(args: argparse.Namespace, message: str, code: int = 2) -> int:
    if getattr(args, "json", False):
        print(json.dumps({"error": message}, ensure_ascii=False))
    else:
        print(message)
    return code


#: Every CLI command accepts --json so AGENTS can consume machine-readable
#: output instead of parsing prose (fluent agent usage).
_JSON_PARENT = argparse.ArgumentParser(add_help=False)
_JSON_PARENT.add_argument("--json", action="store_true",
                          help="machine-readable JSON output (for agents)")


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
    result = agent.propose(
        pillar=args.pillar,
        objective=args.objective,
        amount=args.amount,
        content=args.content,
    )
    data: dict[str, object] = {
        "gate": result.decision,
        "summary": result.summary,
        "workspace": agent.workspace,
        "skills": len(agent.skills),
    }
    draft = ""
    if args.draft and result.decision in ("ALLOW", "REVIEW"):
        draft = agent.draft(args.objective)
        data["draft"] = draft
    lines = [
        f"THE FOCUX Agent - skills loaded: {len(agent.skills)}",
        f"gate: {result.decision}",
        f"summary: {result.summary}",
    ]
    if draft:
        lines += ["", "--- draft ---", console_safe(draft)]
    _out(args, lines, data)
    return 0 if result.ok else 1


def cmd_repl(args: argparse.Namespace) -> int:
    agent = build_agent()
    print(f"THE FOCUX Agent REPL — {len(agent.skills)} skills loaded. "
          "Type 'exit' to quit.")
    try:
        from runtime.focus import focus_pack, format_focus

        pack = focus_pack(agent.memory, agent.workspace)
        summary = "\n".join(
            l for l in format_focus(pack).splitlines()
            if l.startswith(("#", "##", "- [")) or "Metas reales" in l
        )
        if summary:
            print("\nFOCUS:", summary, sep="\n")
    except Exception:  # noqa: BLE001 - focus is an enhancement
        pass
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
    """List the specialized business roles (+ due now / run one)."""
    from datetime import datetime

    from runtime.orchestrator import all_roles, due_roles, role_named

    if args.run:
        agent = build_agent()
        role = role_named(args.run)
        if role is None:
            return _out_err(args, f"unknown role: {args.run}")
        result = agent.run_role(args.run, objective=args.objective)
        data: dict[str, object] = {
            "role": args.run,
            "decision": result.decision,
            "summary": result.summary,
            "content": result.content,
        }
        lines = [f"[{result.decision}] {result.summary}"]
        if result.content:
            lines.append(console_safe(result.content))
        _out(args, lines, data)
        return 0 if result.ok else 1

    now = datetime.now()
    due = {r.name for r in due_roles(now)}
    roles = [r.as_dict() for r in all_roles()]
    for role in roles:
        role["due_now"] = role["name"] in due
    lines = []
    for role in roles:
        marker = " <- due now" if role["due_now"] else ""
        lines.append(
            f"- {role['name']:20s} {role['pillar']:12s} "
            f"{role['action_class']:10s} {role['cadence']:12s} "
            f"skill={role['skill']}{marker}"
        )
    lines.append(f"\n{len(roles)} roles - run one: python -m focux agents --run <name>")
    return _out(args, lines, {"roles": roles})


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
    from runtime.install import (
        default_prefix, install_launchers, register_user_mcp, uninstall,
    )

    prefix = Path(args.prefix).resolve() if args.prefix else default_prefix()
    if args.uninstall:
        ureport = uninstall(prefix, REPO_ROOT)
        print(f"THE FOCUX CLI uninstalled from {prefix}:")
        for item in ureport.updated:
            print(f"  - {item}")
        for note in ureport.notes:
            print(f"  note: {note}")
        return 0
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
            lines = [f"objective added [{obj.objective_id}]: {obj.title} | "
                     f"{obj.kpi}: 0/{obj.target:.0f}"
                     f"{(' ' + obj.unit) if obj.unit else ''}"
                     f" | deadline {obj.deadline or 'none'}"]
            return _out(args, lines, obj.as_dict())

        if args.action == "list":
            objs = [o.as_dict() for o in mem.objectives(workspace)]
            lines = [f"  [{o['objective_id']}] {o['title']} | {o['kpi']}: "
                     f"{o['current']:.0f}/{o['target']:.0f}"
                     f"{(' ' + o['unit']) if o.get('unit') else ''}"
                     for o in objs]
            if not objs:
                lines.append("  (no objectives - add one: focux objective add "
                             "'<title>' --kpi <kpi> --target <n>)")
            return _out(args, lines, {"objectives": objs})

        if args.action == "status":
            from runtime.objectives import format_status, objective_status
            statuses = objective_status(mem, workspace)
            return _out(args, [format_status(statuses)],
                        {"statuses": [s.as_dict() for s in statuses]})

        if args.action == "set":
            obj = mem.update_objective_current(workspace, args.id, args.current)
            if obj is None:
                return _out_err(args, f"no objective '{args.id}' in workspace '{workspace}'")
            lines = [f"[{obj.objective_id}] {obj.title} | {obj.kpi}: "
                     f"{obj.current:.0f}/{obj.target:.0f} "
                     f"({obj.progress() * 100:.0f}%) - measured"]
            return _out(args, lines, obj.as_dict())

        if args.action == "drive":
            from runtime.objectives import drive, format_drive

            agent = build_agent(workspace=workspace)
            report = drive(agent, workspace, objective_id=args.id,
                           limit=args.limit, tier=args.tier)
            return _out(args, [format_drive(report)], report.as_dict())
        return 2
    finally:
        mem.close()


def cmd_expert(args: argparse.Namespace) -> int:
    """Expert Panel: world-class domain expertise (ask + quality review)."""
    from runtime.attach import detect_workspace
    from runtime.experts import ask_expert, list_experts, review_draft

    workspace = getattr(args, "workspace", "") or detect_workspace()
    if args.action == "list":
        experts = list_experts()
        lines = [f"  - {e['domain']:14s} {e['title']}"
                 + (f"  [{e['playbook']}]" if e["playbook"] else "")
                 for e in experts]
        return _out(args, lines, {"experts": experts})

    agent = build_agent(workspace=workspace)
    if args.action == "ask":
        answer = ask_expert(agent, args.domain, args.question, workspace)
        lines = [f"[{answer.decision}] {answer.domain} expert:",
                 console_safe(answer.answer)]
        return _out(args, lines, answer.as_dict())

    if args.action == "review":
        verdict = review_draft(agent, args.domain, args.draft, workspace)
        lines = [f"REVIEW [{args.domain}] -> {verdict.verdict}"]
        for item in verdict.items:
            mark = "ok " if item.passed else "FAIL"
            lines.append(f"  [{mark}] {item.item} - {item.reason}")
        if verdict.judge_reason:
            lines.append(f"  judge: {verdict.judge_reason}")
        _out(args, lines, verdict.as_dict())
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
    path = write_focus_file(pack)
    lines = [format_focus(pack), f"\n(refreshed: {path})"]
    return _out(args, lines, pack.as_dict())


def cmd_ask(args: argparse.Namespace) -> int:
    """The anything-interface: ask the brain anything (directed intelligence)."""
    from runtime.attach import detect_workspace
    from runtime.ask import ask

    workspace = getattr(args, "workspace", "") or detect_workspace()
    agent = build_agent(workspace=workspace)
    result = ask(agent, args.question, workspace)
    lines = [f"[{result.decision}] answer:", console_safe(result.answer)]
    _out(args, lines, result.as_dict())
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """MASTER status: everything at a glance (tier, objectives, work, MCP)."""
    from runtime.attach import detect_workspace
    from runtime.master import format_master_status, master_status
    from runtime.memory import FocuxMemory

    workspace = getattr(args, "workspace", "") or detect_workspace()
    mem = FocuxMemory(REPO_ROOT / "memory" / "focux.db")
    try:
        data = master_status(
            mem, workspace,
            revenue=args.revenue, operating_cost=args.cost, cash=args.cash,
        )
    finally:
        mem.close()
    return _out(args, [format_master_status(data)], data)


def cmd_map(args: argparse.Namespace) -> int:
    """PROJECT MAP: map the project into a queryable graph (local, stdlib)."""
    from runtime.projectmap import (
        build_graph, explain, format_explain, format_map_summary, format_path,
        format_query, load_graph, query, save_graph, shortest_path,
    )

    root = Path(args.dir or ".").resolve()
    if args.action == "build" or args.action == "":
        graph = build_graph(root)
        path = save_graph(graph, root / ".focux" / "map")
        lines = [format_map_summary(graph, root), f"\nsaved: {path}",
                 "query: focux map explain '<name>' | path '<a>' '<b>' | "
                 "query '<pregunta>'"]
        return _out(args, lines, graph.as_dict())

    map_dir = root / ".focux" / "map" / "projectmap.json"
    if not map_dir.exists():
        return _out_err(args, "no map yet - run `focux map` first")
    graph = load_graph(map_dir)
    if args.action == "explain":
        result = explain(graph, args.name)
        return _out(args, [format_explain(result)], result)
    if args.action == "path":
        result = shortest_path(graph, args.a, args.b)
        return _out(args, [format_path(result)], result)
    if args.action == "query":
        result = query(graph, args.question)
        return _out(args, [format_query(result)], result)
    return 2


def cmd_lesson(args: argparse.Namespace) -> int:
    """Save a lesson from real work (the brain's accumulated wisdom)."""
    from runtime.attach import detect_workspace
    from runtime.lessons import save_lesson
    from runtime.memory import FocuxMemory

    workspace = getattr(args, "workspace", "") or detect_workspace()
    mem = FocuxMemory(REPO_ROOT / "memory" / "focux.db")
    try:
        result = save_lesson(mem, workspace, args.lesson)
    finally:
        mem.close()
    lines = [f"lesson saved [{result['key']}]", "aggregate with: focux reflect"]
    return _out(args, lines, result)


def cmd_reflect(args: argparse.Namespace) -> int:
    """Aggregate saved lessons into .focux/lessons.md."""
    from runtime.attach import detect_workspace
    from runtime.lessons import reflect
    from runtime.memory import FocuxMemory

    workspace = getattr(args, "workspace", "") or detect_workspace()
    mem = FocuxMemory(REPO_ROOT / "memory" / "focux.db")
    try:
        target = reflect(mem, workspace, out=Path.cwd() / ".focux" / "lessons.md")
    finally:
        mem.close()
    lines = [f"LESSONS reflected -> {target}"]
    return _out(args, lines, {"file": str(target)})


def cmd_improve(args: argparse.Namespace) -> int:
    """SUCCESS GOVERNOR: improvements at all hours, always measured (gated)."""
    from runtime.attach import detect_workspace
    from runtime.improve import format_improve, improve

    workspace = getattr(args, "workspace", "") or detect_workspace()
    agent = build_agent(workspace=workspace)
    report = improve(agent, workspace, system=args.system, limit=args.limit,
                     tier=args.tier, repo_root=REPO_ROOT)
    if report["note"]:
        return _out_err(args, report["note"])
    return _out(args, [format_improve(report)], report)


def cmd_harness(args: argparse.Namespace) -> int:
    """HARNESS: make ANY software agent-native (CLI-Anything pattern)."""
    from runtime.attach import detect_workspace
    from runtime.harness import (
        generate_harness, list_harnesses, refine_harness, run_harness,
    )

    workspace = getattr(args, "workspace", "") or detect_workspace()
    if args.action == "list":
        harnesses = list_harnesses()
        lines = [f"  - {h['name']}  [{h['dir']}]" for h in harnesses] or \
            ["  (no harnesses yet - generate one: focux harness <dir>)"]
        return _out(args, lines, {"harnesses": harnesses})

    agent = build_agent(workspace=workspace)
    if args.action == "generate" or args.action == "":
        try:
            result = generate_harness(agent, Path(args.dir).resolve(),
                                      name=args.name, workspace=workspace)
        except ValueError as exc:
            return _out_err(args, f"cannot generate: {exc}")
        lines = [f"HARNESS '{result.name}' generated -> {result.dir}"]
        for f in result.files:
            lines.append(f"  + {f}")
        lines.append(f"  {result.note}")
        lines.append("  run: focux harness run '" + result.name + "' -- --help")
        return _out(args, lines, result.as_dict())

    if args.action == "run":
        try:
            return run_harness(args.name, args.args)
        except FileNotFoundError as exc:
            return _out_err(args, str(exc))

    if args.action == "refine":
        try:
            result = refine_harness(agent, args.name, args.focus,
                                    workspace=workspace)
        except (ValueError, FileNotFoundError) as exc:
            return _out_err(args, f"cannot refine: {exc}")
        lines = [f"HARNESS '{result.name}' refined"] + \
            [f"  + {f}" for f in result.files] + [f"  {result.note}"]
        return _out(args, lines, result.as_dict())
    return 2


def cmd_daily(args: argparse.Namespace) -> int:
    """The daily intelligence ritual: VER -> ENFOQUE -> ESTRATEGIA -> OPORTUNIDADES -> VIGILANCIA."""
    from runtime.attach import detect_workspace
    from runtime.master import daily_cycle, format_daily

    workspace = getattr(args, "workspace", "") or detect_workspace()
    sources = tuple(s.strip() for s in args.sources.split(",") if s.strip()) \
        if args.sources else ()
    agent = build_agent(workspace=workspace)
    report = daily_cycle(
        agent, workspace,
        revenue=args.revenue, operating_cost=args.cost, cash=args.cash,
        sources=sources, github_query=args.query, limit=args.limit,
    )
    return _out(args, [format_daily(report)], report)


def cmd_insights(args: argparse.Namespace) -> int:
    """Opportunity analyst: real signals + goals -> gated opportunities."""
    from runtime.attach import detect_workspace
    from runtime.ask import insights

    workspace = getattr(args, "workspace", "") or detect_workspace()
    agent = build_agent(workspace=workspace)
    report = insights(agent, workspace, limit=args.limit, tier=args.tier)
    if report["note"]:
        return _out_err(args, report["note"])
    lines = [f"INSIGHTS (workspace: {workspace}) - gated opportunities:"]
    for item in report["insights"]:
        lines.append(f"  [{item['decision']}] ({item['pillar']}) {item['insight']}"
                     + (f" - why: {item['why']}" if item.get("why") else ""))
    if not report["insights"]:
        lines.append("  (no parseable insights from the model - nothing invented)")
    reviews = [i for i in report["insights"] if i["decision"] == "REVIEW"]
    if reviews:
        lines.append("REVIEW opportunities need human approval before execution.")
    return _out(args, lines, report)


def cmd_mcp(args: argparse.Namespace) -> int:
    """Run the MCP bridge over stdio (the tools any agent consumes)."""
    import mcp_bridge

    return mcp_bridge.main()


def cmd_audit(args: argparse.Namespace) -> int:
    """Full health: doctor + work validate + attached verification (--json)."""
    from runtime.attach import detect_workspace, verify_attached
    from runtime.workflow import validate, work_root

    workspace = getattr(args, "workspace", "") or detect_workspace()
    checks: list[dict[str, object]] = []
    ok = True

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        checks.append({"label": label, "ok": bool(cond), "detail": detail})
        if not cond:
            ok = False

    # doctor core (local, fast)
    agent = build_agent(workspace=workspace)
    check("skills", len(agent.skills) >= 17, f"{len(agent.skills)} loaded")
    check("money-gate falsification", default_gate().falsification_test())
    check("memory", agent.memory is not None, f"workspace '{workspace}'")

    # work harness consistency
    work_root_path = work_root()
    work_issues = validate(work_root_path)
    if work_root_path.exists():
        for issue in work_issues:
            check("work:" + issue, False)
        if not work_issues:
            check("work state", True, "consistent")
    else:
        check("work state", True, "no staged work (ok)")

    # attached workspace contract (this project)
    target = Path.cwd()
    if (target / ".focux-workspace").exists():
        vrep = verify_attached(target, REPO_ROOT)
        for c in vrep.checks:
            if c.critical:
                check("attach:" + c.label, c.ok, c.detail)

    data: dict[str, object] = {"ok": ok, "checks": checks,
                               "result": "AUDIT OK" if ok else "ISSUES FOUND"}
    lines = ["THE FOCUX BRAIN - audit"] + [
        f"  [{'OK ' if c['ok'] else 'FAIL'}] {c['label']}"
        + (f" - {c['detail']}" if c["detail"] else "")
        for c in checks
    ] + [f"RESULT: {data['result']}"]
    _out(args, lines, data)
    return 0 if ok else 1


def cmd_work(args: argparse.Namespace) -> int:
    """Work Harness: durable, stage-gated work (frame->plan->execute->verify)."""
    from runtime.attach import detect_workspace
    from runtime.workflow import (
        approve, execute, frame, load_state, plan, resume_text, review,
        status_text, validate, verify, work_root,
    )

    workspace = getattr(args, "workspace", "") or detect_workspace()
    root = work_root()
    action = args.action
    refresh_focus(workspace)

    if action == "status":
        from runtime.attach import drift_report

        text = status_text(root)
        drift = drift_report(Path.cwd(), REPO_ROOT)
        lines = [text]
        if drift:
            lines += ["", "DRIFT warnings (Automaton-style):"]
            lines += [f"  - {d}" for d in drift]
            lines += ["  (durable .focux history is preserved regardless)"]
        return _out(args, lines, {"work": text, "drift": drift})

    if action == "resume":
        return _out(args, [resume_text(root)], {"work": resume_text(root)})

    if action == "validate":
        issues = validate(root)
        if not issues:
            return _out(args, ["VALID: .focux/work state is consistent"],
                        {"valid": True, "issues": []})
        lines = [f"  [FAIL] {i}" for i in issues]
        _out(args, lines, {"valid": False, "issues": issues})
        return 1

    agent = build_agent(workspace=workspace)
    state = load_state(root)

    if action == "frame":
        try:
            state = frame(agent, args.objective, domain=args.domain,
                          workspace=workspace, force=args.force)
        except ValueError as exc:
            return _out_err(args, f"cannot frame: {exc}")
        lines = [f"FRAMED -> {state.spec_path}",
                 "SPEC draft written. YOUR approval is the product review "
                 "(no model gate): focux work approve"]
        return _out(args, lines, state.as_dict())

    if action == "approve":
        if state is None:
            return _out_err(args, "no work to approve - run `focux work frame '<objective>'`")
        state = approve(state)
        lines = [f"SPEC approved (product review) - stage: {state.stage}",
                 "next: focux work plan"]
        return _out(args, lines, state.as_dict())

    if action == "plan":
        if state is None:
            return _out_err(args, "no work - run `focux work frame '<objective>'`")
        state = plan(agent, state, workspace=workspace)
        lines = [f"PLANNED -> {state.plan_path}",
                 "optional: focux work review (engineering review)"]
        return _out(args, lines, state.as_dict())

    if action == "review":
        if state is None:
            return _out_err(args, "no work - run `focux work frame '<objective>'`")
        try:
            state = review(agent, state, workspace=workspace)
        except ValueError as exc:
            return _out_err(args, f"cannot review: {exc}")
        lines = ([f"ENGINEERING REVIEW PASS - stage: {state.stage}"]
                 if state.stage == "reviewed"
                 else [f"ENGINEERING REVIEW REVISE - plan unchanged "
                       f"({state.history[-1]})"])
        return _out(args, lines, state.as_dict())

    if action == "execute":
        if state is None:
            return _out_err(args, "no work - run `focux work frame '<objective>'`")
        gated = execute(agent, state, workspace=workspace)
        lines = [f"EXECUTE (stage: {state.stage}) - plan steps gated:"]
        for step in gated:
            lines.append(f"  [{step['decision']}] ({step['pillar']}) {step['action']}")
        reviews = [s for s in gated if s["decision"] == "REVIEW"]
        if reviews:
            lines.append("REVIEW steps need human approval; ALLOW steps are "
                         "yours to do across sessions. Close with: focux work verify")
        return _out(args, lines, {"stage": state.stage, "steps": gated})

    if action == "verify":
        if state is None:
            return _out_err(args, "no work - run `focux work frame '<objective>'`")
        state = verify(agent, state, workspace=workspace,
                       confirm=getattr(args, "confirm", False))
        if state.stage == "verified":
            lines = [f"VERIFIED ('{state.objective}') - harness disengaged. "
                     "Next sessions open quiet."]
        else:
            lines = [f"verification did not pass - back to {state.stage}. "
                     "Fix and re-run: focux work verify"]
        _out(args, lines, state.as_dict())
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
    return _out(args, [format_report(report)], report.as_dict())


def cmd_doctor(args: argparse.Namespace) -> int:
    """Brain diagnostics: skills, gates, memory, providers, MCP, survival.

    With ``--target <dir>`` it also verifies an ATTACHED workspace end-to-end
    (the universal installer's contract).
    """
    ok = True
    checks: list[dict[str, object]] = []
    infos: list[str] = []

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        checks.append({"label": label, "ok": bool(cond), "detail": detail})
        if not cond:
            ok = False

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
    for reg_agent, registered in user_mcp_registered().items():
        detail = "registered" if registered else "not registered (focux install --mcp)"
        infos.append(f"[info] user MCP {reg_agent}: {detail}")

    # attached workspace verification (universal installer contract)
    if args.target:
        from runtime.attach import verify_attached
        infos.append(f"attached workspace: {Path(args.target).resolve()}")
        vrep = verify_attached(Path(args.target).resolve(), REPO_ROOT)
        for c in vrep.checks:
            if c.critical:
                check(c.label, c.ok, c.detail)
            else:
                infos.append(f"[info] {c.label}" + (f" - {c.detail}" if c.detail else ""))
        if not vrep.ok:
            ok = False

    data: dict[str, object] = {
        "ok": ok,
        "checks": checks,
        "infos": infos,
        "result": "OK - THE FOCUX BRAIN is operational." if ok else "ISSUES FOUND",
    }
    lines = ["THE FOCUX BRAIN - doctor"] + [
        f"  [{'OK ' if c['ok'] else 'FAIL'}] {c['label']}"
        + (f" - {c['detail']}" if c["detail"] else "")
        for c in checks
    ] + [f"  {i}" for i in infos] + [f"RESULT: {data['result']}"]
    _out(args, lines, data)
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
        return _out_err(args, "usage: focux absorb --sources github,huggingface,x "
                              "[--query 'ai agent']")
    workspace = args.workspace or detect_workspace()
    x_bearer = os.environ.get("X_BEARER_TOKEN", "")
    results = absorb(
        sources=sources,
        github_query=args.query,
        x_bearer=x_bearer,
        x_query=args.query,
        limit=args.limit,
    )

    # store into memory so the brain can ANALIZAR with real signals
    from runtime.memory import FocuxMemory

    mem = FocuxMemory(REPO_ROOT / "memory" / "focux.db")
    try:
        stored = store_results(results, mem, workspace=workspace)
    finally:
        mem.close()
    ok_sources = [s for s, r in results.items() if r.ok]
    data = {
        "workspace": workspace,
        "stored": stored,
        "sources": {s: {"ok": r.ok, "error": r.error, "items": list(r.items),
                        "fetched_at": r.fetched_at}
                    for s, r in results.items()},
    }
    lines = [format_absorb(results),
             f"\nabsorbed into memory ({workspace}): {stored} items "
             f"from {', '.join(ok_sources) or 'no source'}"]
    _out(args, lines, data)
    return 0 if ok_sources else 1


def cmd_modules(args: argparse.Namespace) -> int:
    """Modular system: every brain organ registered + integrity check."""
    from runtime.modules import all_modules, integrity_check

    modules = [m.as_dict() for m in all_modules()]
    check = integrity_check()
    lines = []
    for module in modules:
        deps = f" deps={','.join(module['deps'])}" if module["deps"] else ""
        lines.append(f"- {module['id']:14s} v{module['version']:5s} "
                     f"{module['description']}{deps}")
    lines.append("\nINTEGRITY: " + str(check["count"]) + " checks, "
                 + ("ALL OK" if check["ok"]
                    else f"{sum(1 for m in check['modules'] if not m['ok'])} FAILED"))
    data = {"modules": modules, "integrity": check}
    _out(args, lines, data)
    return 0 if check["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="focux", description="THE FOCUX Agent")
    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", parents=[_JSON_PARENT], help="one-shot proposal + optional draft")
    run.add_argument("objective")
    run.add_argument("--pillar", default="content",
                     help="content|commerce|monetization|research|account")
    run.add_argument("--amount", type=float, default=0.0)
    run.add_argument("--content", default="")
    run.add_argument("--draft", action="store_true", help="also draft via LLM")
    run.set_defaults(func=cmd_run)

    repl = sub.add_parser("repl", parents=[_JSON_PARENT], help="interactive session")
    repl.add_argument("--pillar", default="content")
    repl.set_defaults(func=cmd_repl)

    ask = sub.add_parser("ask", parents=[_JSON_PARENT],
                         help="ANYTHING interface: ask the brain (directed intelligence)")
    ask.add_argument("question", help="any question for the brain")
    ask.add_argument("--workspace", default="")
    ask.set_defaults(func=cmd_ask)

    insights = sub.add_parser("insights", parents=[_JSON_PARENT],
                              help="opportunity analyst: real signals -> gated opportunities")
    insights.add_argument("--limit", type=int, default=3)
    insights.add_argument("--tier", default="normal")
    insights.add_argument("--workspace", default="")
    insights.set_defaults(func=cmd_insights)

    mcp = sub.add_parser("mcp", parents=[_JSON_PARENT],
                         help="run the MCP bridge over stdio (19 tools for agents)")
    mcp.set_defaults(func=cmd_mcp)

    audit = sub.add_parser("audit", parents=[_JSON_PARENT],
                           help="full health: doctor + work validate + attached check")
    audit.add_argument("--workspace", default="")
    audit.set_defaults(func=cmd_audit)

    skills = sub.add_parser("skills", parents=[_JSON_PARENT], help="list loaded skills")
    skills.set_defaults(func=cmd_skills)

    drafts = sub.add_parser("drafts", parents=[_JSON_PARENT], help="list crystallized draft skills")
    drafts.set_defaults(func=cmd_drafts)

    promote = sub.add_parser("promote", parents=[_JSON_PARENT], help="promote a DRAFT skill to active (HUMAN review)")
    promote.add_argument("name")
    promote.set_defaults(func=cmd_promote)

    agents = sub.add_parser("agents", parents=[_JSON_PARENT], help="list/run the 9 specialized business roles")
    agents.add_argument("--run", default="", help="run one role (gated)")
    agents.add_argument("--objective", default="", help="objective for --run")
    agents.set_defaults(func=cmd_agents)

    objective = sub.add_parser("objective", parents=[_JSON_PARENT], help="Objective Brain: measurable goals the brain drives toward")
    osub = objective.add_subparsers(dest="action", required=True)
    oadd = osub.add_parser("add", parents=[_JSON_PARENT], help="add an objective")
    oadd.add_argument("title")
    oadd.add_argument("--kpi", required=True, help="metric (followers, revenue, leads...)")
    oadd.add_argument("--target", type=float, required=True)
    oadd.add_argument("--unit", default="")
    oadd.add_argument("--deadline", default="", help="ISO date YYYY-MM-DD")
    oadd.add_argument("--workspace", default="")
    oadd.set_defaults(func=cmd_objective)
    olist = osub.add_parser("list", parents=[_JSON_PARENT], help="list objectives")
    olist.add_argument("--workspace", default="")
    olist.set_defaults(func=cmd_objective)
    ostatus = osub.add_parser("status", parents=[_JSON_PARENT], help="progress, gap, overdue, momentum")
    ostatus.add_argument("--workspace", default="")
    ostatus.set_defaults(func=cmd_objective)
    oset = osub.add_parser("set", parents=[_JSON_PARENT], help="MEDIR: record the current KPI value")
    oset.add_argument("id")
    oset.add_argument("--current", type=float, required=True)
    oset.add_argument("--workspace", default="")
    oset.set_defaults(func=cmd_objective)
    odrive = osub.add_parser("drive", parents=[_JSON_PARENT], help="INTELLIGENCE: gap analysis -> gated plan (LLM)")
    odrive.add_argument("--id", default="", help="one objective id (default: all)")
    odrive.add_argument("--limit", type=int, default=3)
    odrive.add_argument("--tier", default="normal")
    odrive.add_argument("--workspace", default="")
    odrive.set_defaults(func=cmd_objective)

    expert = sub.add_parser("expert", parents=[_JSON_PARENT], help="Expert Panel: world-class domain expertise")
    esub = expert.add_subparsers(dest="action", required=True)
    elist = esub.add_parser("list", parents=[_JSON_PARENT], help="list the domain experts + playbooks")
    elist.set_defaults(func=cmd_expert)
    eask = esub.add_parser("ask", parents=[_JSON_PARENT], help="consult a domain expert (LLM, gated READ)")
    eask.add_argument("domain", choices=("content", "social", "ecommerce",
                                         "monetization", "opportunities"))
    eask.add_argument("question")
    eask.add_argument("--workspace", default="")
    eask.set_defaults(func=cmd_expert)
    ereview = esub.add_parser("review", parents=[_JSON_PARENT], help="quality gate: PASS/REVISE a draft")
    ereview.add_argument("domain", choices=("content", "social", "ecommerce",
                                            "monetization", "opportunities"))
    ereview.add_argument("draft", help="the draft to review")
    ereview.add_argument("--workspace", default="")
    ereview.set_defaults(func=cmd_expert)

    work = sub.add_parser("work", parents=[_JSON_PARENT], help="Work Harness: durable stage-gated work (Automaton mindset)")
    wsub = work.add_subparsers(dest="action", required=True)
    wframe = wsub.add_parser("frame", parents=[_JSON_PARENT], help="write SPEC.md (draft); YOU approve it = product review")
    wframe.add_argument("objective")
    wframe.add_argument("--domain", default="code", choices=("code", "content"))
    wframe.add_argument("--force", action="store_true", help="replace existing active work")
    wframe.add_argument("--workspace", default="")
    wframe.set_defaults(func=cmd_work)
    wapprove = wsub.add_parser("approve", parents=[_JSON_PARENT], help="approve SPEC.md (product review, no model gate)")
    wapprove.set_defaults(func=cmd_work)
    wplan = wsub.add_parser("plan", parents=[_JSON_PARENT], help="write PLAN.md (gated steps)")
    wplan.add_argument("--workspace", default="")
    wplan.set_defaults(func=cmd_work)
    wreview = wsub.add_parser("review", parents=[_JSON_PARENT],
                              help="optional engineering review (plan -> reviewed)")
    wreview.add_argument("--workspace", default="")
    wreview.set_defaults(func=cmd_work)
    wexec = wsub.add_parser("execute", parents=[_JSON_PARENT], help="gate every plan step before doing it")
    wexec.add_argument("--workspace", default="")
    wexec.set_defaults(func=cmd_work)
    wverify = wsub.add_parser("verify", parents=[_JSON_PARENT], help="run real checks -> verified (terminal)")
    wverify.add_argument("--confirm", action="store_true",
                         help="verify by human confirmation when no auto checks")
    wverify.add_argument("--workspace", default="")
    wverify.set_defaults(func=cmd_work)
    wstatus = wsub.add_parser("status", parents=[_JSON_PARENT], help="session-start honesty: where the work is")
    wstatus.set_defaults(func=cmd_work)
    wresume = wsub.add_parser("resume", parents=[_JSON_PARENT], help="re-enter existing work from a fresh session")
    wresume.set_defaults(func=cmd_work)
    wvalid = wsub.add_parser("validate", parents=[_JSON_PARENT], help="consistency check of the work state")
    wvalid.set_defaults(func=cmd_work)

    focus = sub.add_parser("focus", parents=[_JSON_PARENT], help="directed intelligence: real goals, gaps, evidence, state")
    focus.add_argument("--workspace", default="",
                       help="workspace (default: auto-detect from .focux-workspace)")
    focus.add_argument("--tier", default="",
                       help="override survival tier (default: none)")
    focus.add_argument("--revenue", type=float, default=None,
                       help="revenue to compute the tier")
    focus.add_argument("--cost", type=float, default=0.0)
    focus.add_argument("--cash", type=float, default=0.0)
    focus.set_defaults(func=cmd_focus)

    attach = sub.add_parser("attach", parents=[_JSON_PARENT], help="mount THE FOCUX BRAIN on any agent/business dir")
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

    install = sub.add_parser("install", parents=[_JSON_PARENT], help="global CLI: portable launchers on PATH (+ MCP)")
    install.add_argument("--prefix", default="",
                         help="bin dir (default ~/.thefocux/bin)")
    install.add_argument("--mcp", action="store_true",
                         help="register thefocux MCP at user level (Codex)")
    install.add_argument("--uninstall", action="store_true",
                         help="remove launchers + user MCP; .focux history preserved")
    install.set_defaults(func=cmd_install)

    hb = sub.add_parser("heartbeat", parents=[_JSON_PARENT], help="survival tier + roles due + approvals")
    hb.add_argument("--revenue", type=float, default=0.0)
    hb.add_argument("--cost", type=float, default=0.0)
    hb.add_argument("--cash", type=float, default=0.0)
    hb.add_argument("--approvals", type=int, default=0)
    hb.set_defaults(func=cmd_heartbeat)

    doctor = sub.add_parser("doctor", parents=[_JSON_PARENT], help="THE FOCUX BRAIN diagnostics")
    doctor.add_argument("--target", default="",
                        help="verify an attached workspace (focux attach <dir>)")
    doctor.set_defaults(func=cmd_doctor)

    evolve = sub.add_parser("evolve", parents=[_JSON_PARENT], help="daily evolution cycle (analyze -> improve)")
    evolve.add_argument("--workspace", default="",
                        help="workspace (default: auto-detect from .focux-workspace)")
    evolve.set_defaults(func=cmd_evolve)

    modules = sub.add_parser("modules", parents=[_JSON_PARENT], help="modular system: organs + integrity check")
    modules.set_defaults(func=cmd_modules)

    multiply = sub.add_parser("multiply", parents=[_JSON_PARENT], help="1 asset -> 20+ outputs (revenue multiplier)")
    multiply.add_argument("insight", help="core insight to multiply")
    multiply.add_argument("--offer", default="", help="offer for the CTAs")
    multiply.add_argument("--draft", action="store_true", help="draft each output via LLM")
    multiply.set_defaults(func=cmd_multiply)

    offer = sub.add_parser("offer", parents=[_JSON_PARENT], help="5-rung offer ladder: attention -> revenue")
    offer.add_argument("--business", default="the business")
    offer.set_defaults(func=cmd_offer)

    absorb = sub.add_parser("absorb", parents=[_JSON_PARENT], help="absorb REAL data (github/huggingface/x) into memory")
    absorb.add_argument("--sources", default="github,huggingface",
                        help="comma list: github,huggingface,x")
    absorb.add_argument("--query", default="ai agent", help="search query")
    absorb.add_argument("--limit", type=int, default=10)
    absorb.add_argument("--workspace", default="",
                        help="workspace (default: auto-detect from .focux-workspace)")
    absorb.set_defaults(func=cmd_absorb)

    status = sub.add_parser("status", parents=[_JSON_PARENT],
                            help="MASTER: todo en una mirada (tier, objetivos, work, MCP)")
    status.add_argument("--revenue", type=float, default=0.0)
    status.add_argument("--cost", type=float, default=0.0)
    status.add_argument("--cash", type=float, default=0.0)
    status.add_argument("--workspace", default="")
    status.set_defaults(func=cmd_status)

    daily = sub.add_parser("daily", parents=[_JSON_PARENT],
                           help="ciclo diario: VER->ENFOQUE->ESTRATEGIA->OPORTUNIDADES->VIGILANCIA")
    daily.add_argument("--sources", default="",
                       help="comma list for the VER step (default: none = sin red)")
    daily.add_argument("--query", default="ai agent")
    daily.add_argument("--limit", type=int, default=3)
    daily.add_argument("--revenue", type=float, default=0.0)
    daily.add_argument("--cost", type=float, default=0.0)
    daily.add_argument("--cash", type=float, default=0.0)
    daily.add_argument("--workspace", default="")
    daily.set_defaults(func=cmd_daily)

    map_cmd = sub.add_parser("map", parents=[_JSON_PARENT],
                             help="PROJECT MAP: mapea el proyecto a un grafo consultable (local, stdlib)")
    msub = map_cmd.add_subparsers(dest="action")
    mbuild = msub.add_parser("build", help="build the project graph")
    mbuild.add_argument("dir", nargs="?", default=".")
    mbuild.set_defaults(func=cmd_map)
    mexp = msub.add_parser("explain", help="a node and its connections (EXTRACTED/INFERRED)")
    mexp.add_argument("name")
    mexp.add_argument("--dir", default=".")
    mexp.set_defaults(func=cmd_map)
    mpath = msub.add_parser("path", help="shortest path between two concepts")
    mpath.add_argument("a")
    mpath.add_argument("b")
    mpath.add_argument("--dir", default=".")
    mpath.set_defaults(func=cmd_map)
    mquery = msub.add_parser("query", help="keyword-scored subgraph for a question")
    mquery.add_argument("question")
    mquery.add_argument("--dir", default=".")
    mquery.set_defaults(func=cmd_map)
    # bare `focux map` builds the current dir
    map_cmd.set_defaults(action="build", dir=".", func=cmd_map)

    lesson = sub.add_parser("lesson", parents=[_JSON_PARENT],
                            help="save a lesson from real work (work memory)")
    lesson.add_argument("lesson")
    lesson.add_argument("--workspace", default="")
    lesson.set_defaults(func=cmd_lesson)

    reflect = sub.add_parser("reflect", parents=[_JSON_PARENT],
                             help="aggregate lessons into .focux/lessons.md")
    reflect.add_argument("--workspace", default="")
    reflect.set_defaults(func=cmd_reflect)

    improve_cmd = sub.add_parser("improve", parents=[_JSON_PARENT],
                                 help="SUCCESS GOVERNOR: mejoras a todas horas, siempre medidas (gateadas)")
    improve_cmd.add_argument("--system", action="store_true",
                             help="focalizar en mejorar el sistema THE FOCUX mismo")
    improve_cmd.add_argument("--limit", type=int, default=4)
    improve_cmd.add_argument("--tier", default="normal")
    improve_cmd.add_argument("--workspace", default="")
    improve_cmd.set_defaults(func=cmd_improve)

    harness = sub.add_parser("harness", parents=[_JSON_PARENT],
                             help="HARNESS: make ANY software agent-native (CLI-Anything pattern)")
    hsub = harness.add_subparsers(dest="action")
    hgen = hsub.add_parser("generate", help="analyze->design->generate->verify->publish a CLI for a codebase")
    hgen.add_argument("dir", help="target codebase path")
    hgen.add_argument("--name", default="", help="harness name (default: dir name)")
    hgen.add_argument("--workspace", default="")
    hgen.set_defaults(func=cmd_harness)
    hlist = hsub.add_parser("list", help="installed harnesses")
    hlist.set_defaults(func=cmd_harness)
    hrun = hsub.add_parser("run", help="run an installed harness")
    hrun.add_argument("name")
    hrun.add_argument("args", nargs=argparse.REMAINDER,
                      help="args passed to the harness CLI")
    hrun.set_defaults(func=cmd_harness)
    hrefine = hsub.add_parser("refine", help="gap analysis: extend a harness")
    hrefine.add_argument("name")
    hrefine.add_argument("focus", nargs="?", default="")
    hrefine.add_argument("--workspace", default="")
    hrefine.set_defaults(func=cmd_harness)
    harness.set_defaults(action="list", func=cmd_harness)

    args = parser.parse_args(argv)
    if getattr(args, "command", None) is None:
        # `focux` alone shows the master status (the masterpiece one-glance)
        return cmd_status(argparse.Namespace(
            revenue=0.0, cost=0.0, cash=0.0, workspace="",
            json=any(a == "--json" for a in (argv or [])),
        ))
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
