---
name: commerce-ops
description: Store operations — reads are free, writes (pricing, discounts, refunds, inventory changes) are gated through the money-gate skill.
version: 1.0.0
metadata:
  openclaw:
    requires:
      bins:
        - curl
    emoji: "🛒"
---

# Commerce Ops

Operate the store via its API/MCP surface (Saleor or Medusa; Stripe for
payments). Two surfaces, never mixed:

## Read-only surface (free)

- Catalog, product, order and customer reads.
- Metrics pulls for the cadence skill (revenue, orders, refunds).

## Write surface (gated)

Every write is a COMMERCE or MONEY action — route through the money-gate
skill first: pricing changes, discounts, refunds, subscription changes,
inventory adjustments, customer account changes.

## Rules

1. Use the read-only token/scope for reads and a SEPARATE scoped write token
   for gated writes. Never send the write token on a read.
2. Every mutation carries an idempotency key; retries reuse the same key.
3. Refunds and price changes show a diff in the approval card.
4. After every executed write, write a receipt (what, order id, amount,
   fingerprint, outcome).
5. Never expose payment credentials or customer PII in conversation.
6. **Parameter-level authorization** (Tetrate/Ory pattern): enforcement is
   per-request on the parameters — amount, recipient, account — not just a
   tool allowlist. The same refund tool that handles a $50 credit can issue a
   $50,000 one, so every write action carries its amount + recipient for the
   gate.
7. **Capability-scoped, short-lived credentials** (credential-broker pattern):
   never hold long-lived write keys; use JIT tokens (minutes-to-hour TTL) from
   a credential broker, single-use or short-TTL. The agent never holds standing
   permission to move money. **Step-up approval**: crossing a risk threshold
   pauses and requires a fresh human step-up (an expiring grant); then the
   grant expires and is never reusable.
8. **Point-of-sale policy enforcement** (Ramp pattern): policy is enforced at
   the transaction point BEFORE money moves — decline at transaction time with
   a per-decision audit trail. Audit coverage is 100%, never sampling;
   out-of-policy events are flagged and reported in the weekly review.
9. **Recipes** (Goose pattern): recurring workflows ("refund order X", "update
   product price", "monthly inventory count") are packaged as named recipes
   with parameters, so the agent executes a vetted flow instead of improvising.
   Recipes are reviewed like code.
10. **Narrow-scope persona agents** (Infosys pattern): prefer
    single-responsibility operations — order ops, pricing ops, inventory ops —
    over one generalist for writes. Each persona has its own scoped
    credentials.
