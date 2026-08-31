"""FOCUX tool layer — tools the agent can ACT with, always gated.

Pattern absorbed from GenericAgent (lsdefine, MIT): a tool registry with
``do_<tool_name>`` dispatch — zero-boilerplate tools. The FOCUX difference:
every tool is classified and routed through the money-gate BEFORE it runs.
The LLM may request a tool; the gate decides ALLOW / REVIEW / DENY; REVIEW
returns a human approval card (single-use, expiring, byte-bound via the
gate's Approval). The agent never executes what the gate did not ALLOW.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from policy.constitution import Claim, apply_constitution, law1_blocks
from policy.money_gate import Action, ActionClass, Decision, MoneyGate


@dataclass(frozen=True)
class ToolSpec:
    """Declarative metadata for a tool (what the LLM sees)."""

    name: str
    description: str
    action_class: ActionClass
    parameters: dict[str, dict[str, str]] = field(default_factory=dict)

    def as_schema(self) -> dict[str, object]:
        """OpenAI-style tool schema for the LLM."""
        props = {
            name: {"type": meta.get("type", "string"), "description": meta.get("desc", "")}
            for name, meta in self.parameters.items()
        }
        required = [n for n, m in self.parameters.items() if m.get("required")]
        schema: dict[str, object] = {
            "type": "object",
            "properties": props,
        }
        if required:
            schema["required"] = required
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    decision: str  # ALLOW / REVIEW / DENY
    output: str
    approval_hint: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "decision": self.decision,
            "output": self.output,
            "approval_hint": self.approval_hint,
        }


class ToolRegistry:
    """Tools with ``do_<name>(args)`` handlers, gated before execution.

    A handler returns a string (the observable output). Tools that move money
    or change the world declare a MONEY/COMMERCE/ACCOUNT/CONTENT class; the
    gate decides whether the tool may run at all.
    """

    def __init__(self, gate: MoneyGate) -> None:
        self._gate = gate
        self._specs: dict[str, ToolSpec] = {}
        self._handlers: dict[str, Callable[[dict[str, Any]], str]] = {}
        self._register_builtins()

    # -- registration --------------------------------------------------------

    def register(
        self,
        spec: ToolSpec,
        handler: Callable[[dict[str, Any]], str],
    ) -> None:
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler

    def _register_builtins(self) -> None:
        """Zero-boilerplate built-ins via the do_<name> convention."""
        # Declare specs for the built-in tools (what the LLM sees).
        builtin_specs: dict[str, ToolSpec] = {
            "ping": ToolSpec(
                "ping", "Health probe. Always safe.", ActionClass.READ,
                {},
            ),
            "draft_content": ToolSpec(
                "draft_content", "Draft content in the user's voice (no publish).",
                ActionClass.CONTENT,
                {"topic": {"type": "string", "desc": "topic to draft", "required": True}},
            ),
            "publish_post": ToolSpec(
                "publish_post", "Publish content to a platform (approval required).",
                ActionClass.CONTENT,
                {"platform": {"type": "string", "desc": "linkedin|x|instagram|youtube"}},
            ),
            "send_email": ToolSpec(
                "send_email", "Send an outbound message (approval required).",
                ActionClass.CONTENT,
                {"to": {"type": "string", "desc": "recipient email"}},
            ),
            "create_listing": ToolSpec(
                "create_listing", "Create an ecommerce listing (approval required).",
                ActionClass.COMMERCE,
                {"product": {"type": "string", "desc": "product name", "required": True},
                 "price": {"type": "number", "desc": "price"}},
            ),
            "make_payment": ToolSpec(
                "make_payment", "Move money (always human approval).",
                ActionClass.MONEY,
                {"amount": {"type": "number", "desc": "amount", "required": True},
                 "to": {"type": "string", "desc": "recipient"}},
            ),
            "update_credentials": ToolSpec(
                "update_credentials", "Change account credentials (approval required).",
                ActionClass.ACCOUNT,
                {"target": {"type": "string", "desc": "credential target"}},
            ),
        }
        for name, spec in builtin_specs.items():
            self._specs[name] = spec
        for name in dir(self):
            if name.startswith("do_"):
                tool_name = name[3:]
                handler = getattr(self, name)
                # Built-in specs are declared explicitly above; wire handlers.
                self._handlers.setdefault(tool_name, handler)

    # -- introspection --------------------------------------------------------

    def specs(self) -> list[ToolSpec]:
        return list(self._specs.values())

    def schemas(self) -> list[dict[str, object]]:
        return [s.as_schema() for s in self._specs.values()]

    def tool_names(self) -> list[str]:
        return sorted(self._specs)

    # -- the gated execution path --------------------------------------------

    def request(
        self,
        tool_name: str,
        args: dict[str, Any],
        *,
        tainted: bool = False,
        claims: tuple[Claim, ...] = (),
    ) -> ToolResult:
        """Gate then (maybe) execute. NEVER executes a DENY; REVIEW is a card."""
        spec = self._specs.get(tool_name)
        if spec is None:
            return ToolResult(False, "DENY", f"unknown tool: {tool_name}")
        action = Action(
            action_class=spec.action_class,
            amount=float(args.get("amount", 0.0) or 0.0),
            target=f"tool:{tool_name}",
            idempotency_key=f"tool:{tool_name}:{str(args)[:80]}",
        )
        decision = self._gate.decide(action, tainted=tainted)
        verdicts = apply_constitution(
            self._gate, action, content=str(args)[:200], claims=claims,
            tainted=tainted,
        )
        if law1_blocks(verdicts) or decision is Decision.DENY:
            return ToolResult(
                False, "DENY",
                "constitution Law I or money-gate DENY: tool must not run",
            )
        if decision is Decision.REVIEW:
            return ToolResult(
                True, "REVIEW",
                "human approval required before this tool may run",
                approval_hint=(
                    "approve exactly: "
                    f"{action.action_class.value} {action.amount:.2f} "
                    f"tool:{tool_name}"
                ),
            )
        handler = self._handlers.get(tool_name)
        if handler is None:
            return ToolResult(False, "DENY", f"no handler for tool: {tool_name}")
        try:
            output = handler(args)
        except Exception as exc:  # noqa: BLE001 - report, never crash the loop
            return ToolResult(False, "DENY", f"{tool_name} failed: {type(exc).__name__}: {exc}")
        return ToolResult(True, "ALLOW", output)

    # -- built-in tools (do_<name> convention) --------------------------------

    def do_ping(self, args: dict[str, Any]) -> str:
        """Health probe — READ class, auto-ALLOW."""
        return "pong"

    def do_draft_content(self, args: dict[str, Any]) -> str:
        """Draft content (no publish) — CONTENT class, REVIEW at L1."""
        topic = str(args.get("topic", ""))
        return f"[draft would be produced for: {topic}]"

    def do_publish_post(self, args: dict[str, Any]) -> str:
        """Publish content to a platform — CONTENT class, REVIEW at L1."""
        platform = str(args.get("platform", "linkedin"))
        return f"[PUBLISHED to {platform}]"

    def do_send_email(self, args: dict[str, Any]) -> str:
        """Send an outbound message — CONTENT class, REVIEW at L1."""
        to = str(args.get("to", ""))
        return f"[EMAIL sent to {to}]"

    def do_create_listing(self, args: dict[str, Any]) -> str:
        """Create an ecommerce listing — COMMERCE class, REVIEW at L1."""
        product = str(args.get("product", ""))
        price = float(args.get("price", 0.0) or 0.0)
        return f"[LISTING created: {product} @ {price:.2f}]"

    def do_make_payment(self, args: dict[str, Any]) -> str:
        """Move money — MONEY class, REVIEW always (never auto-approve)."""
        amount = float(args.get("amount", 0.0) or 0.0)
        to = str(args.get("to", ""))
        return f"[PAYMENT {amount:.2f} to {to}]"

    def do_update_credentials(self, args: dict[str, Any]) -> str:
        """Change account/credentials — ACCOUNT class, REVIEW at L1."""
        target = str(args.get("target", ""))
        return f"[CREDENTIALS updated: {target}]"
