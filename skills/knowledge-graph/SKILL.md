---
name: knowledge-graph
description: Build and query a deterministic business knowledge graph over the memory — entities and relations, every edge explained with evidence, no vector store.
version: 1.0.0
metadata:
  openclaw:
    emoji: "🔎"
---

# Knowledge Graph

Turn the business memory (MEMORY.md, metrics.md, decisions.md, receipts/,
plans/) into a queryable graph: entities (businesses, products, campaigns,
channels, customers, vendors, metrics) and relations (produces, targets,
sourced-from, measured-by, decided-by, evidenced-by). The graph is a derived,
evidence-first view — it never replaces the files it is built from.

## Rules

1. Build deterministically from the files: parse the Markdown structure of the
   memory (headings, lists, tables, links) to extract entities and relations.
   No vector store, no embeddings, no fuzzy matching — the same files must
   always produce the same graph.
2. Every edge carries its evidence (file path + line, or receipt id). An edge
   without evidence is not created.
3. Use the graph to answer cross-cutting questions (which campaigns drove which
   metrics; which decisions touched which products) and to spot gaps (products
   with no campaign, metrics with no receipt). Report gaps as findings, not as
   invented facts.
4. The graph is a derived view over the evidence files: rebuilding it must
   always be possible from the files alone. Never store facts only in the
   graph — the memory files stay authoritative.
5. Maintenance: rebuild/refresh at cadence time (weekly) or whenever memory
   files change. Superseded entities get a validity note (supersede-not-delete)
   instead of being removed.

## Never

- Invent an edge without evidence.
- Treat the graph as authoritative over the evidence files.
- Put derived graph content into the trusted/system prompt.
- Let the graph drive money actions — money decisions come from the money-gate,
  not the graph.
