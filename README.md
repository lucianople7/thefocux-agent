<div align="center">

# THE FOCUX Agent

**El superagente de negocio — redes sociales, ecommerce, búsqueda de
oportunidades, monetización y creación de contenido.**

No un agente con plugins: un agente **construido con esa mentalidad**. El
negocio es su núcleo nativo — código Python puro, determinista, testeable —
que se conecta a **cualquier LLM**, acepta **cualquier skill de agente**, y
está preparado para **el mundo real** (gates humanos, receipts, proposal-only).

</div>

---

## La mentalidad (el ADN)

THE FOCUX vive un bucle continuo, con el negocio en cada paso:

```
ANALIZAR → PLANIFICAR → EJECUTAR → MEDIR → MEJORAR
```

| Pilar | Qué hace | Dónde vive |
|---|---|---|
| **Redes sociales** | Voz aprendida, matrix de contenido (pilares × 8 formatos), hooks, drafts en tu voz | `policy/focux_voice.py`, `policy/focux_content.py`, `skills/voice-builder`, `content-matrix`, `hook-generator` |
| **Ecommerce** | Auditoría ecommerce, agentic-commerce, operaciones gateadas | fork Growth OS + `skills/commerce-ops` |
| **Búsqueda de oportunidades** | Research de nicho, análisis competitivo, stories de los últimos 7 días | `skills/research`, `skills/cli-hub-meta-skill` (búsqueda AI-nativa) |
| **Monetización** | Growth packs, oferta, experimentos, survival tiers (esfuerzo ≠ autorización) | fork Monetization Engine + `policy/constitution.py` |
| **Creación de contenido** | Pipeline contenido → quality-gate → aprobación humana → distribución | `skills/content-pipeline`, `quality-gate` |

## El sistema inmune (nunca se suspende)

- **Money-gate determinista**: el dinero NUNCA se auto-aprueba (falsification
  test, tainted o no). Aprobaciones single-use, expirantes, byte-bound.
- **Constitución de 3 leyes** (`constitution.md`, código en
  `policy/constitution.py`): I nunca dañar · II ganarse la existencia ·
  III nunca engañar. La Ley I es absoluta.
- **SOUL.md validado** (`policy/focux_soul.py`): identidad evolutiva con
  defensa anti-inyección determinista.
- **Proposal-only**: pagos, publicaciones, mensajes salientes, credenciales,
  operaciones financieras y cambios irreversibles requieren aprobación humana.

## Agnóstico total

- **Cualquier LLM**: la capa DNA no importa ningún SDK — Python puro. El
  runtime se conecta a OpenAI-compatible (Qwen Token Plan, Groq, Mistral...),
  Gemini, Claude, OpenRouter, Ollama local sin llave.
- **Cualquier skill/plugin**: formato estándar open Agent Skills (SKILL.md con
  `name` + `description`) — el mismo que Claude Code, Cursor, Codex, OpenClaw
  y CowAgent consumen. Los skills externos son instrucciones, nunca permisos.
- Ver garantía completa en [`docs/provider-agnostic-guarantee.md`](docs/provider-agnostic-guarantee.md)
  con test de contrato (`policy/tests/test_provider_agnostic.py`).

## Quickstart

```bash
git clone https://github.com/lucianople7/thefocux-agent.git
cd thefocux-agent
python -m pytest -q                 # 76+ tests: money-gate, constitution, soul, voice, content, cli, agnosticism
python tools/skill_validator.py     # 17 skills, all valid
```

Monta los skills en cualquier shell agente-nativo apuntando su `skills.dirs`
(o workspace skills) a `skills/`.

## Estructura

```
thefocux-agent/
├── policy/                # DNA determinista, NO LLM en rutas de decisión
│   ├── money_gate.py      #   approval boundary (ALLOW/REVIEW/DENY)
│   ├── constitution.py    #   3 leyes inmutables como código
│   ├── focux_soul.py      #   SOUL.md validation + injection defense
│   ├── focux_voice.py     #   voice profile (entrevista + absence signals)
│   ├── focux_content.py   #   content matrix + hook generator
│   ├── focux_cli.py       #   capa CLI agente-nativa (gating)
│   └── tests/             #   76+ tests, falsification verde
├── skills/                # 17 SKILL.md (formato open Agent Skills)
├── soul/SOUL.md.template  # identidad evolutiva (validada)
├── tools/skill_validator.py
├── constitution.md        # las 3 leyes (docs)
├── docs/
│   ├── plans/             # design spec THE FOCUX
│   ├── research/          # absorción: Charlie Hills, Automaton, CLI-Anything, catálogos
│   └── provider-agnostic-guarantee.md
└── pytest.ini
```

## Licencia

MIT. Los patrones absorbidos tienen fuente nombrada en
[`docs/research/`](docs/research/) (Charlie Hills social-media-skills MIT,
Conway Automaton MIT, CLI-Anything Apache-2.0, awesome-llm-apps Apache-2.0).
