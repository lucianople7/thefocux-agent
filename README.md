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

Instala el CLI global `focux` + `focux-web`, 57 skills, 11 roles y el BRAIN.
Luego: `Copy-Item .env.example .env` y añade tu API key (DeepSeek, Qwen,
OpenAI, o `auto` vía OmniRoute con free tiers).

Sin pip también puedes hacer el CLI global portable en cualquier máquina:

```bash
focux install                 # launchers portables en ~/.thefocux/bin (PATH)
focux install --mcp           # + registra el brain MCP a nivel usuario:
                              #   Codex (~/.codex/config.toml)
                              #   Claude Code (~/.claude.json, merge seguro)
                              #   Cursor (~/.cursor/mcp.json)
focux doctor                  # verifica qué agentes tienen el MCP registrado
```

## THE FOCUX BRAIN — el mejorador de agentes y negocios

No solo un agente: una **capa de gobierno** que cualquier agente adopta para
cualquier negocio. Monta el brain en un directorio con un comando:

```bash
focux attach ./mi-negocio --workspace mi-negocio   # + espacio de memoria propio
focux doctor --target ./mi-negocio   # verifica la instalación end-to-end
focux                              # ESTADO MAESTRO: todo en una mirada
focux daily                        # el ritual diario: VER->ENFOQUE->ESTRATEGIA
                                   #   ->OPORTUNIDADES->VIGILANCIA
```

**Los poderes que otorga a cualquier agente o negocio** (manifiesto completo
en [`docs/POWERS.md`](docs/POWERS.md)):

1. **VER el mundo real** — `absorb`: datos de GitHub/HF/X como hechos
2. **Metas que se miden** — `objective`: KPIs, gaps, momentum
3. **Inteligencia dirigida** — `focus` + `ask`: solo hacia las metas reales
4. **Estrategia con evidencia** — `drive` + `insights`: propuestas gateadas
5. **Experiencia mundial** — `expert`: playbooks + revisión PASS/REVISE
6. **Trabajo que sobrevive** — `work`: frame→plan→execute→verify→verified
7. **Seguridad que no negocia** — money-gate + constitución + auditoría
8. **Mejora continua** — `evolve` + `daily`: momentum, nunca vibes
9. **Adopción universal** — `attach` + `install` + MCP (19 tools)

Cada negocio attached declara su **workspace** (`.focux-workspace`, por
defecto el nombre del directorio): la memoria se separa por negocio, y
cualquier comando (`focux absorb`, `focux evolve`, `focux run`) que corras
dentro de ese árbol **detecta el workspace automáticamente** — sin flags.

Cualquier agente (Codex, Claude Code, Cursor, Aider, Copilot, Gemini CLI,
CowAgent, el futuro) que trabaje en ese directorio lee `AGENTS.md` +
`skills/focux-brain` y opera con la identidad, la inmunidad y la mejora de
THE FOCUX — sin cambiar su runtime. `focux attach` instala, además del
contrato universal, la configuración nativa de cada agente:

- **Claude Code** → `.mcp.json` (servidor MCP `thefocux` registrado)
- **Codex** → `.codex/config.toml` (sección `[mcp_servers.thefocux]` añadida)
- **Cursor** → `.cursor/mcp.json` + regla `.cursor/rules/focux.mdc`
- **Aider** → `.aider.conf.yml` (auto-lectura de `AGENTS.md`)
- **Copilot** → `.github/copilot-instructions.md`
- **Gemini CLI** → lee `AGENTS.md` nativamente (sin archivo extra)

Idempotente y no destructivo: re-ejecutar nunca pisa tus configs (JSON se
fusiona, TOML se añade); `--force` refresca solo lo que THE FOCUX posee.

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

focux doctor        # brain diagnostics (skills, gates, provider, MCP, survival)
focux doctor --target ./neg  # + verifica el workspace attached end-to-end
focux attach ./neg --workspace mi-negocio  # UNIVERSAL + memoria por negocio
                    # + configs nativas (claude/codex/cursor/aider/copilot) + MCP
focux install       # CLI global portable en ~/.thefocux/bin (+ --mcp)
focux ask '<cualquier pregunta>'  # ANYTHING interface: el brain con contexto dirigido
focux insights      # analista de oportunidades: señales reales -> oportunidades gateadas
focux map           # PROJECT MAP: mapea el proyecto a un grafo consultable (local, stdlib)
focux map explain '<concepto>'   # nodo + conexiones EXTRACTED/INFERRED
focux map path '<a>' '<b>'       # trayectoria hop-by-hop entre dos conceptos
focux lesson '<que aprendiste>'  # memoria de trabajo: lecciones
focux reflect       # agrega las lecciones en .focux/lessons.md
focux harness <dir> # HARNESS: hace agent-native CUALQUIER software (CLI-Anything)
focux harness run <name> -- --help   # usa el CLI generado (--json)
focux harness refine <name> "<focus>" # gap analysis: expande cobertura
focux audit         # salud completa: doctor + work + attached (--json)
focux mcp           # ejecuta el bridge MCP (19 tools) sobre stdio
focux modules       # sistema modular: 25 órganos registrados + integrity check
focux evolve        # evolución diaria: analiza lo ejecutado, propone mejoras
focux absorb        # absorbe DATOS REALES (github/huggingface/x) a la memoria
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

`focux modules` lista los 25 órganos del brain (money-gate, constitution,
soul, voice, content, memory, tools, eval, survival, heartbeat, selfmod,
orchestrator, evolution, repurpose, offer, ingest, attach, install,
objectives, experts, workflow, focus, mcp-bridge, webui...) con versión
semver y dependencias. `integrity_check` **prueba que cada módulo importa y
que el falsification del money-gate sigue verde** — un módulo nuevo no puede
romper el sistema inmune en silencio.

## Absorción de datos reales — el cerebro que ve el mundo

`focux absorb` alimenta ANALIZAR con señales REALES, no vibes:

```bash
focux absorb --sources github,huggingface --query "ai agent" --workspace research
```

- **GitHub** — qué crece: repos del tema ordenados por estrellas (API pública)
- **Hugging Face** — qué viene: modelos y datasets en tendencia (API pública)
- **X** — qué funciona en el nicho: requiere `X_BEARER_TOKEN` opcional; sin
  token **degrada con honestidad** (reporta "token required", jamás inventa datos)

Todo se guarda como eventos de memoria (`absorb:github`, `absorb:huggingface`,
`absorb:x:error`) para que el brain ANALICE con datos de verdad. Además, cada
borrador que genera el agente recibe **automáticamente** un bloque
`## Absorbed signals (REAL data)` con lo último absorbido (repo + estrellas,
modelo + descargas) — sin keywords de recuperación, sin truncamiento: los
datos reales son un hecho con el que el brain razona. La ingesta es solo
lectura: ningún sensor ejecuta acciones, y el money-gate sigue mandando.

## Objective Brain — inteligencia real HACIA los objetivos

El brain no solo dice NO (sistema inmune): **empuja el negocio hacia metas
medibles**. Define un objetivo, el brain analiza el gap con datos reales,
propone acciones concretas (gateadas) y mide el avance:

```bash
focux objective add "Publicar 3 piezas sobre agentes IA" --kpi piezas --target 3 --deadline 2026-12-31
focux objective drive          # INTELIGENCIA: gap + señales reales -> plan gateado (LLM)
focux objective status         # progreso, gap, overdue, momentum (delta)
focux objective set <id> --current 2   # MEDIR tras ejecutar
```

Cómo funciona el `drive`: junta los objetivos con sus gaps, el tier de
supervivencia, los **datos REALES absorbidos** y los procedimientos; el LLM
(cualquier proveedor) propone **una acción concreta por objetivo basada en
evidencia**; cada propuesta pasa por el money-gate **antes** de entrar al
plan — el brain propone con inteligencia pero **nunca auto-autoriza**:
research → ALLOW, publicar → REVIEW, cobrar → REVIEW. El humano aprueba los
REVIEW, ejecuta, mide (`set --current`), y el brain ajusta con momentum real.

## Expert Panel — experiencia mundial aplicada

El brain no solo gobierna: **es experto**. Lleva playbooks de nivel mundial
por dominio (`playbooks/`) y un panel de expertos consultable:

```bash
focux expert list                          # 5 expertos + sus playbooks
focux expert ask content "3 hooks para un post con los datos absorbidos"
focux expert review content "<borrador>"   # calidad: PASS / REVISE
```

- **Playbooks** (`playbooks/*.md`): sistemas operativos de nivel mundial —
  content (hooks que convierten, storytelling, CTAs), social (algoritmos por
  plataforma, cadencia, loop de crecimiento), ecommerce (unit economics,
  oferta, AOV/LTV/CAC), monetization (escalera, pricing, honestidad),
  opportunities (señal → validación → lanzamiento → medir).
- **`ask`** — consulta al experto del dominio: responde como especialista
  mundial, fundamentado en su playbook + **señales reales absorbidas** +
  objetivos activos (acción READ, gateada).
- **`review`** — control de calidad ANTES de publicar/vender: pre-check
  determinista (borradores vacíos → REVISE sin LLM) + juez LLM estricto por
  checklist del dominio (hook, cta, evidence, offer, price, validation...).
  Verdict = calidad, nunca permiso: el money-gate y el humano mandan.

## Work Harness — trabajo durable que sobrevive a las sesiones

Mentalidad adoptada del patrón Automaton (MIT): el trabajo que **excede una
ventana de contexto** o necesita acuerdo previo pasa por etapas explícitas con
estado durable en el proyecto (`.focux/work/`): SPEC.md, PLAN.md, ROADMAP.md,
current.json — sobrevive a resets de contexto, reinicios y cambios multi-paso.

```bash
focux work status             # honestidad al iniciar sesion: que toca ahora
focux work frame '<objetivo>' # SPEC.md (borrador); TU lo apruebas = product review
focux work approve            # ningun modelo suplanta tu juicio de producto
focux work plan               # PLAN.md con pasos gateados
focux work review             # engineering review OPCIONAL (plan -> reviewed)
focux work execute            # cada paso pasa por el money-gate ANTES
focux work verify             # checks reales -> verified (terminal, harness off)
focux work resume             # re-entrar desde una sesion fresca
focux work validate           # consistencia del estado
```

Reglas del harness (paridad Automaton completa):
- **`status` también avisa de DERIVA** — contrato attached que se desvió de la
  fuente (AGENTS.md/skill faltantes o desactualizados): "DRIFT warnings" +
  sugerencia `focux attach --force`. La historia `.focux` nunca se toca.
- **`install --uninstall`** — quita launchers + MCP de usuario y **preserva
  la historia durable** (work, focus, map, harnesses, lessons).

Reglas del harness:
- **Lo que cabe en una sesión se hace directo** — el harness lo dice al
  inicio de sesión ("DO IT DIRECTLY") en vez de dejarte adivinando.
- **`verified` es terminal**: el harness se desengancha y las siguientes
  sesiones abren **en silencio** hasta tu próximo objetivo.
- **El humano aprueba el SPEC** a la salida de `frame`: esa es la revisión
  de producto; ningún modelo la suplanta.
- **`execute` gatea cada paso** (content→REVIEW, monetization→REVIEW,
  research→ALLOW): la disciplina del brain sigue activa dentro del harness.
- `verify` corre checks reales: dominio `code` → pytest del proyecto;
  dominio `content` → el Expert Panel debe dar PASS.

## FOCUS — inteligencia dirigida SOLO a nuestras metas reales

Cualquier agente (Codex, Claude Code, Cursor, OpenCode...) que entre a un
proyecto attached es **mucho más inteligente** el primer segundo: lee el
pack de foco y sabe nuestras metas reales, sus gaps, la evidencia y dónde
está el trabajo. Su inteligencia se dirige SOLO ahí.

```bash
focux focus                      # el pack: metas + gaps + evidencia + estado
focux focus --revenue 300 --cost 2000 --cash 500   # + tier de supervivencia
```

- **Determinista, sin LLM**: los números salen de la memoria; nada se inventa.
- **Dirigido, no genérico**: solo lo que sirve a los objetivos activos. Si no
  hay metas, el pack lo DICE ("intelligence without goals is noise").
- **Tres vías de entrega**: `focux focus` (consola), `.focux/focus.md`
  (archivo que todo agente lee al iniciar sesión; se refresca en cada
  comando), y la tool MCP **`focux_focus`** (cualquier agente la llama al
  arrancar). El metaskill lo ordena: *"Be smart ONLY toward the real goals."*

## Agent-first: el brain completo vía MCP — 22 tools

Cualquier agente (Codex, Claude Code, Cursor...) consulta el brain entero como
tools MCP (`mcp_bridge.py`, registrado en Codex como `thefocux`) — **fluido,
sin parsear prosa**:

- `focux_focus` — inteligencia dirigida: metas reales + gaps + evidencia
- `focux_gate` — decide ALLOW/REVIEW/DENY antes de actuar
- `focux_objective_add / set / status` — define y mide metas
- `focux_drive` — la pasada de inteligencia (gap → plan gateado)
- `focux_expert_ask / review` — expertos mundiales + calidad PASS/REVISE
- `focux_absorb` — datos reales (github/huggingface/x) → memoria
- `focux_graph_explain / path / query` — el mapa del proyecto (local, stdlib)
- `focux_work_status` — dónde está el trabajo por etapas
- `focux_survival` / `focux_heartbeat` — tier + ritmo del negocio
- `focux_signals` / `focux_memory` — evidencia y memoria compartida
- `focux_roles` / `focux_learn` / `focux_selfmod` / `focux_redact`

**CLI igual de fluido**: todo comando acepta `--json` (machine-readable,
nada de prosa). Exit codes: 0 ok, 1 falló/REVIEW, 2 error de uso; en `--json`
los errores llegan como `{"error": "..."}`.

`focux doctor` ejecuta un **handshake real** contra el bridge (`--selfcheck`:
initialize → tools/list → gate call) y verifica workspaces attached con
`--target`.

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
python -m focux skills                 # 57 skills cargados
python -m focux agents                 # 11 roles de negocio con horarios
python -m focux agents --run planning  # ejecutar un rol (gateado)
python -m focux run "publish a post about AI" --pillar content   # gate: REVIEW
python -m focux repl                   # sesión interactiva con gates
python -m focux run "analizar el nicho" --pillar research --draft # ALLOW + draft
```

## Orquestador: 11 roles de negocio con horarios

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
├── focux.py               # CLI: run | repl | skills | absorb | multiply | install
├── runtime/               # runtime propio: agente, LLM, skills (sin shell)
│   ├── ingest.py          #   sensores reales: github/huggingface/x -> memoria
│   ├── attach.py          #   instalador universal: brain en cualquier agente
│   ├── install.py         #   CLI global portable: launchers + MCP de usuario
│   ├── objectives.py      #   Objective Brain: metas medibles + drive (LLM gateado)
│   ├── experts.py         #   Expert Panel: playbooks mundiales + ask + review
│   ├── workflow.py        #   Work Harness: etapas durables frame->...->verified
│   ├── focus.py           #   FOCUS: inteligencia dirigida solo a las metas
│   ├── repurpose.py       #   multiplier: 1 pieza -> 20+ activos
│   ├── offer.py           #   escalera de 5 peldaños: atención -> ingresos
│   ├── evolution.py       #   ciclo diario: analiza -> propone mejoras
│   └── modules.py         #   registro modular (25 órganos) + integrity check
├── playbooks/             # conocimiento experto mundial (5 dominios)
├── policy/                # DNA determinista, NO LLM en rutas de decisión
│   ├── money_gate.py      #   approval boundary (ALLOW/REVIEW/DENY)
│   ├── constitution.py    #   3 leyes inmutables como código
│   ├── focux_soul.py      #   SOUL.md validation + injection defense
│   ├── focux_voice.py     #   voice profile (entrevista + absence signals)
│   ├── focux_content.py   #   content matrix + hook generator
│   ├── focux_cli.py       #   capa CLI agente-nativa (gating)
│   └── tests/             #   90+ tests, falsification verde
├── skills/                # 57 SKILL.md (contenido + negocio + ingeniería)
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
