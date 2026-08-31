<div align="center">

# THE FOCUX Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-e7c46e?style=for-the-badge&labelColor=242424)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-174%20passed-3ddc84?style=for-the-badge&labelColor=242424)]()
[![CI](https://github.com/lucianople7/thefocux-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/lucianople7/thefocux-agent/actions)
[![Skills](https://img.shields.io/badge/skills-56-6ea8fe?style=for-the-badge&labelColor=242424)]()
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&labelColor=242424&logo=python&logoColor=white)]()

**El superagente de negocio — redes sociales, ecommerce, búsqueda de
oportunidades, monetización y creación de contenido.**

No un agente con plugins: un agente **construido con esa mentalidad**. El
negocio es su núcleo nativo — código Python puro, determinista, testeable —
que se conecta a **cualquier LLM**, acepta **cualquier skill de agente**, y
está preparado para **el mundo real** (gates humanos, receipts, proposal-only).

</div>

## Instalación (1 comando)

```powershell
# Windows
irm https://raw.githubusercontent.com/lucianople7/thefocux-agent/main/install.ps1 | iex
```

```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/lucianople7/thefocux-agent/main/install.sh | bash
```

Instala el CLI global `focux` + `focux-web`, 57 skills, 9 roles y el BRAIN.
Luego: `Copy-Item .env.example .env` y añade tu API key (DeepSeek, Qwen,
OpenAI, o `auto` vía OmniRoute con free tiers).

## THE FOCUX BRAIN — el mejorador de agentes y negocios

No solo un agente: una **capa de gobierno** que cualquier agente adopta para
cualquier negocio. Monta el brain en un directorio con un comando:

```bash
focux attach ./mi-negocio     # AGENTS.md + metaskill + constitución + memoria
```

Cualquier agente (Codex, Claude Code, CowAgent, el futuro) que trabaje en ese
directorio lee `AGENTS.md` + `skills/focux-brain` y opera con la identidad,
la inmunidad y la mejora de THE FOCUX — sin cambiar su runtime:

- **Identidad** — `AGENTS.md` + `focux-brain/SKILL.md`: quién eres, qué
  consigues, cómo (el bucle), qué jamás.
- **Inmune** — money-gate + constitución (3 leyes) + falsification.
- **Memoria** — SQLite (hechos, eventos, procedimientos) compartible.
- **Mejora** — cristalización con release gate + **audit append-only + rate
  limits** (`runtime/selfmod.py`).
- **Supervivencia** — **tiers del negocio** (`runtime/survival.py`): runway
  determina el esfuerzo (modelos/roles/ritmo), **nunca la autorización**.
- **Vigilancia** — **heartbeat** (`runtime/heartbeat.py`): tier + roles due +
  aprobaciones pendientes.

```bash
focux heartbeat --revenue 3000 --cost 2000 --cash 5000 --approvals 2
# HEARTBEAT ... Tier: high | runway: 90.0d | Roles due: none | Healthy: yes
#            ... Momentum: 12 runs · 83% success · 3 skills crystallized · WINNING

focux doctor        # brain diagnostics (skills, gates, provider, survival, audit)
focux attach ./neg  # agent-first workspace: AGENTS.md + metaskill + constitución
                    # + SQLite memory initialized + .env + .gitignore
focux modules       # sistema modular: 16 órganos registrados + integrity check
focux evolve        # evolución diaria: analiza lo ejecutado, propone mejoras
focux multiply '<insight>'   # REVENUE MULTIPLIER: 1 pieza -> 20+ activos
focux offer         # escalera de 5 peldaños: atención -> ingresos
```

## Revenue multiplier — el mecanismo del 20x

El multiplicador probado (el sistema de Charlie Hills genera 100M vistas/año
así): **1 pieza de contenido → 20+ activos distribuibles**, cada uno con su
plataforma, su formato, su hook y su CTA hacia la oferta.

```bash
focux multiply "El agente que convierte atención en ingresos" --draft
# CONTENT MULTIPLIER — 20 outputs from 1 asset
#   [OK] linkedin-post        LinkedIn   post
#   [OK] x-thread             X          thread (5-8 tweets)
#   [OK] instagram-carousel   Instagram  carousel outline (8 slides)
#   [OK] youtube-script       YouTube    short script
#   ... 20 outputs, cada CTA apunta a la escalera de ofertas
```

`focux offer` muestra la **escalera de 5 peldaños**: free → lead → entry
($9-49) → core ($99-499) → premium ($500+). Cada peldaño crea valor real
(Law II: la escalera monetiza confianza, no presión). El rol `multiplier`
del orquestador ejecuta el ciclo completo: 1 insight → 20 activos con CTA →
escalera que convierte.

## Evolución diaria — el brain mejora solo, todos los días

`focux evolve` (rol `evolution`, cadencia daily) analiza lo ejecutado y
propone mejoras CONCRETAS, nunca vibes:

- **Fix** — procedimientos con fallos >= 2 y ratio >= 50% → propone rehacerlos
- **Crystallize** — procedimientos probados (>= 80% éxito, >= 3 runs) → propone
  cristalizarlos como skill DRAFT (humano promueve)
- **Promote** — drafts esperando tu revisión

Cada ciclo se registra en memoria (evento `evolution`) y en el audit
append-only. Todo es propuesta: nada se auto-activa.

## Sistema modular — cada órgano registrado y verificado

`focux modules` lista los 16 órganos del brain (money-gate, constitution,
soul, voice, content, memory, tools, eval, survival, heartbeat, selfmod,
orchestrator, evolution, mcp-bridge, webui...) con versión semver y
dependencias. `integrity_check` **prueba que cada módulo importa y que el
falsification del money-gate sigue verde** — un módulo nuevo no puede romper
el sistema inmune en silencio.

## Agent-first: el brain completo vía MCP

Cualquier agente (Codex, Claude Code, Cursor...) consulta el brain entero como
tools MCP (`mcp_bridge.py`, registrado en Codex como `thefocux`):

- `focux_gate` — decide ALLOW/REVIEW/DENY antes de actuar
- `focux_survival` — tier del negocio (esfuerzo, nunca autorización)
- `focux_heartbeat` — tier + roles due + aprobaciones pendientes
- `focux_roles` — los 9 roles con horarios
- `focux_memory` — hechos, eventos, procedimientos (SQLite compartido)
- `focux_learn` — cristaliza procedimientos como DRAFT (humano promueve)
- `focux_selfmod` — auditoría append-only de auto-modificaciones
- `focux_redact` — secrets nunca en receipts

**57 skills**: **17 de contenido** (el sistema completo de
[Charlie Hills social-media-skills](https://github.com/charlie947/social-media-skills),
MIT — voice, posts, carousels, reels, thumbnails, scoring, analytics) + **15 de
negocio** (commerce, monetización, research, CLI, gates, **focux-brain**) + **25 de ingeniería de
producción** ([addyosmani/agent-skills](https://github.com/addyosmani/agent-skills),
MIT): spec→plan→build→test→review→ship, frontend, APIs, CI/CD, seguridad,
observabilidad, debugging, deploy, ADRs. THE FOCUX crea contenido con una voz
aprendida, gestiona negocio y **construye su propio mundo**: código,
interfaces, pipelines y docs con disciplina production-grade.

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
python -m pytest -q                 # 90+ tests: money-gate, constitution, soul, voice, content, cli, runtime
python tools/skill_validator.py     # 17 skills, all valid
```

## Consola web (tu logo, cero dependencias)

`webui.py` — la consola local del agente con **tu logo THE FOCUX**, hecha solo
con la stdlib de Python (http.server, sin npm, sin Docker, sin framework):

```bash
python webui.py --port 47822     # abre http://127.0.0.1:47822
```

Paneles: chat con el agente (gateado), herramientas con **tarjetas de
aprobación** (aprobar/denegar), memoria por workspace, drafts cristalizados
(promover con un clic), skills y estado. El agente "de serie": logo + WebUI +
CLI (`python -m focux`), todo MIT, todo local.

## Runtime propio (sin depender de ningún shell)

THE FOCUX no necesita OpenClaw, CowAgent ni ningún runtime externo: se
**sostiene sobre su propio `runtime/`** — cero dependencias de terceros para
inferencia (solo `urllib`), con el money-gate y la constitución siempre en el
camino. El **tool layer gateado** (`runtime/tools.py`) le permite *actuar*:
el LLM pide una tool, el gate decide ALLOW/REVIEW/DENY, y REVIEW devuelve una
tarjeta de aprobación humana. Nada se ejecuta sin tu permiso. La **memoria
local-first** (`runtime/memory.py`, patrón Waku/Memmy) guarda episódica +
semántica + procedural en un SQLite tuyo, con **retrieval gate** (solo
recupera cuando el mensaje la necesita — fail-open) y workspaces que aíslan
dominios (billing, content, research). Y el bucle **MEJORAR** cristaliza lo
ejecutado: `agent.learn()` registra el procedimiento y escribe la skill en
`skills-draft/` como DRAFT — el release gate (`runtime/eval.py`) la revisa
(checks deterministas + LLM-judge opcional) y **solo un humano la promueve**:
`python -m focux promote <name>`. Higiene de auditoría (patrón OpenBot): los
secrets **nunca entran en receipts** (`runtime/redact.py` redacta keys,
tokens, prompts y args) y el **dry-run mode** decide-y-registra sin bloquear
para afinar policy contra tráfico real antes de exigirla.

```bash
python -m focux skills                 # 56 skills cargados
python -m focux agents                 # 9 roles de negocio con horarios
python -m focux agents --run planning  # ejecutar un rol (gateado)
python -m focux run "publish a post about AI" --pillar content   # gate: REVIEW
python -m focux repl                   # sesión interactiva con gates
python -m focux run "analizar el nicho" --pillar research --draft # ALLOW + draft
```

## Orquestador: 9 roles de negocio con horarios

El patrón de agentes especializados (estilo Polsia) implementado de forma
original en `runtime/orchestrator.py` — determinista (sin LLM en los
schedules), cada rol mapeado a un pilar + clase de acción + skill, y SIEMPRE
gateado por el money-gate:

| Rol | Pilar | Clase | Cadencia | Skill |
|---|---|---|---|---|
| orchestrator | research | read | 06:00 / 20:00 | cadence |
| planning | research | read | daily | content-matrix |
| competitor-research | research | read | daily | research |
| social-media | content | content | every 2h | post-writer |
| email-outreach | content | content | every 3h | post-formatter |
| customer-support | content | content | every 3h | post-writer |
| ads | monetization | commerce | every 6h | commerce-ops |
| code | account | account | on demand | incremental-implementation |
| finance | monetization | money | every 6h | money-gate |

`finance` → REVIEW (dinero nunca auto); `social-media`/`email` → REVIEW
(publicar/enviar requiere aprobación); `planning`/`research` → ALLOW + draft.

Provider (agnóstico, por env o `.env` — copia `.env.example`):

```powershell
# DeepSeek — un solo paso (solo tu key)
$env:FOCUX_PROVIDER = "deepseek"
$env:FOCUX_API_KEY  = "sk-..."          # tu key real
python -m focux repl                     # ¡ya habla con DeepSeek!

# Qwen Token Plan / OpenAI / local
$env:FOCUX_PROVIDER = "qwen"            # o "openai", "ollama" (sin llave)
```

Presets: `deepseek` (deepseek-chat/reasoner), `qwen` (Token Plan), `openai`,
`ollama` (local keyless). O custom: `FOCUX_MODEL` + `FOCUX_BASE_URL`.
La key se lee de env/`.env` — nunca del repo, nunca en receipts (redact).

Monta los skills en cualquier shell agente-nativo apuntando su `skills.dirs`
(o workspace skills) a `skills/`.

## Estructura

```
thefocux-agent/
├── focux.py               # CLI: run | repl | skills
├── runtime/               # runtime propio: agente, LLM, skills (sin shell)
├── policy/                # DNA determinista, NO LLM en rutas de decisión
│   ├── money_gate.py      #   approval boundary (ALLOW/REVIEW/DENY)
│   ├── constitution.py    #   3 leyes inmutables como código
│   ├── focux_soul.py      #   SOUL.md validation + injection defense
│   ├── focux_voice.py     #   voice profile (entrevista + absence signals)
│   ├── focux_content.py   #   content matrix + hook generator
│   ├── focux_cli.py       #   capa CLI agente-nativa (gating)
│   └── tests/             #   90+ tests, falsification verde
├── skills/                # 56 SKILL.md (17 contenido + 14 negocio + 25 ingeniería)
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
