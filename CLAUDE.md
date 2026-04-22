# MACH Race 2026 — MACH-ORCHESTRATOR

## Proyecto
Ciclo ADLC agéntico para MACHBank. LangGraph orquesta 7 agentes especializados
con checkpoints Human-in-the-Loop via Slack. Jira para tracking. FastAPI para webhooks.

## Stack
- Python 3.12 · LangGraph 1.0+ · FastAPI · Pydantic v2
- `langchain-groq` (Llama 3 vía Groq) · `langchain-anthropic` (reservado P3)
- `slack-sdk` · `jira` (python-jira) · `uvicorn` · `streamlit`

## Claude Code Skills

Instalar antes de trabajar en este proyecto:

```bash
# LangGraph — expertise en grafos, nodos, checkpointers, patrones HITL
claude mcp add langgraph

# LangSmith tracing — agregar/consultar trazas
claude mcp add langsmith-trace

# Caveman — comunicación comprimida, menos tokens
claude mcp add caveman
```

Verificar instaladas: `/find-skills` en Claude Code.

## Arquitectura
```
state/cycle_state.py          → CycleState (TypedDict compartido entre todos los nodos)
graph/mach_graph.py           → StateGraph: build_graph(), get_graph_config()
nodes/orchestrator_node.py    → init, route, finalize
nodes/hitl_node.py            → make_hitl_notify_node(phase) + make_hitl_node(phase)
nodes/helper.py               → load_prompt(), save_output(), create_llm(), llm_invoke(), get_phase_instructions()
nodes/<agente>/<agente>_node.py  → 7 nodos LLM reales (Groq)
nodes/<agente>/<agente>_prompt.md → prompts editables sin tocar Python
outputs/                      → entregables generados: PRDSPECS.md, ARQSPECS.md, etc.
tools/slack_tools.py          → notify_team(), notify_reviewer(), update_hitl_msg()
tools/jira_tools.py           → create_epic/story/task(), update_issue_status()
api/slack_webhook.py          → POST /slack/interactive + /view/{filename} + /deliverables/
dashboard/app.py              → Streamlit dashboard en tiempo real
dashboard/components/         → componentes UI separados por sección
config/settings.py            → todas las env vars (no hardcodear credenciales)
main.py                       → run_cycle(challenge) — punto de entrada
docs/diagrama_adlc.md         → tabla humano/agente por fase + diagrama Mermaid
docs/grafo_langgraph.png      → grafo real exportado desde LangGraph
docs/export_graph.py          → regenera grafo_langgraph.png si cambia el grafo
```

## Flujo secuencial ADLC

```
PRD → UX → ARQ → DEV → QA → INFRA → SEC → DONE
```
Cada fase: `run_{fase}` → `hitl_notify_{fase}` (DM Slack) → `hitl_{fase}` (interrupt)
- **Approve** → `current_phase` avanza → conditional edge → siguiente agente
- **Reject + feedback** → `current_phase` se mantiene → conditional edge → mismo agente

Ver diagrama completo: `docs/diagrama_adlc.md` · Grafo visual: `docs/grafo_langgraph.png`

## Convenciones de código

**Estado del grafo**
- Cada nodo retorna `dict` con solo los campos que modifica — nunca el estado completo
- Los campos `Annotated[list, operator.add]` en CycleState permiten append concurrente
- Nunca pasar datos entre nodos por fuera del estado

**Nodos LangGraph**
- Firma: `def nombre_node(state: CycleState) -> dict | Command`
- Nodos HITL retornan `Command(update={...}, goto="siguiente_nodo")`
- El `thread_id` siempre viene de `state["thread_id"]`, nunca generarlo dentro del nodo

**Herramientas externas (Slack, Jira)**
- Errores de Slack/Jira no son fatales — loggear con `print("[Slack/Jira] ...")` y continuar
- No usar `raise` en `slack_tools.py` ni `jira_tools.py` — el ciclo no debe romperse por estas

**Async / Sync**
- FastAPI handlers: `async def`
- Nodos LangGraph y tools: `def` síncrono (LangGraph maneja el loop)
- `_resume_graph()` en el webhook es síncrono dentro de un background task de FastAPI

**Tipado**
- Strict type hints en todas las funciones
- Usar `str | None` (union syntax Python 3.10+), no `Optional[str]`
- Los `TypedDict` van en `state/` — no definir tipos inline en nodos

## Comandos frecuentes
```bash
# Setup
pip install -r requirements.txt
cp .env.example .env  # Crítico: GROQ_API_KEY, SLACK_BOT_TOKEN, JIRA_API_TOKEN

# Correr el ciclo (requiere webhook corriendo en otra terminal)
python main.py

# Servidor webhook + entregables en /deliverables/
uvicorn api.slack_webhook:app --reload --port 8000

# Dashboard Streamlit (requiere CHECKPOINTER=sqlite en .env)
streamlit run dashboard/app.py --server.port 8501

# Exponer webhook a Slack en dev — un solo comando:
# (arranca cloudflared, captura URL, actualiza .env, levanta uvicorn)
# Instalar cloudflared: winget install Cloudflare.cloudflared
bash start_dev.sh
# → Imprime la URL para pegar en Slack App > Interactivity > Request URL

# Modo test (sin gastar tokens Groq)
TEST_MODE=true python main.py

# Tests (cuando existan)
pytest tests/ -v
```

## Variables de entorno requeridas
Ver `.env.example`. Críticas para arrancar:
`GROQ_API_KEY`, `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `JIRA_API_TOKEN`

Para el dashboard: `CHECKPOINTER=sqlite`, `DASHBOARD_URL=http://localhost:8501`
Para testing sin tokens: `TEST_MODE=true`

## Modelo por agente
| Agente | Modelo | Razón |
|---|---|---|
| Speckit (orchestrator_init) | `llama-3.3-70b-versatile` | Razonamiento complejo — genera plan maestro del challenge |
| PRD, UX, ARQ, DEV, QA, INFRA, SEC | `llama-3.3-70b-versatile` | Groq free tier, sin rate limits agresivos |
| Orchestrator (routing) | `llama-3.1-8b-instant` | Routing simple, modelo ligero y rápido |
| Dev (P3) | Claude Code (subprocess) | Escribe y ejecuta código real |

> Modelos en `config/settings.py`. `create_llm(model)` en `nodes/helper.py` es el único punto para cambiar proveedor.
> Speckit usa `MODEL_SPECKIT` (env var `MODEL_SPECKIT`). Para P3 cambiar a `claude-sonnet-4-6`.

## Flujo Speckit (planificación al inicio del ciclo)

El orquestador usa un LLM para generar un plan maestro antes de ejecutar los agentes.
Esto da a cada agente instrucciones específicas para el challenge en curso.

```
orchestrator_init_node
  │
  ├── llm_invoke(MODEL_SPECKIT, ORCHESTRATOR_SYSTEM_PROMPT, PLAN_PROMPT_TEMPLATE)
  │     → retorna JSON con plan_phases[{phase, instructions, key_outputs, ...}]
  │     → fallback a plan de respaldo si JSON inválido
  │     → TEST_MODE=true usa stub_content sin llamar al LLM
  │
  └── plan_phases persiste en CycleState (checkpointer)

Cada agente (prd, ux, arch, dev, qa, infra, sec):
  │
  ├── get_phase_instructions(state, "fase") → extrae instructions de plan_phases
  └── load_prompt(..., orchestrator_instructions=...) → inyecta en prompt .md
```

**Por qué speckit en el orquestador y no por nodo**

Speckit genera el *plan de qué construir*. Cada agente genera el *cómo ejecutarlo*. Son capas distintas — mezclarlas duplica trabajo sin beneficio neto.

| Criterio | Single entry (orquestador) | Por nodo |
|---|---|---|
| Rol | Plan maestro coherente para todo el ciclo | Redundante — cada agente ya genera su spec |
| Costo LLM | 1 call extra al inicio | +7 calls (uno por fase) |
| Coherencia entre fases | Un solo contexto, visión global | Cada fase tiene vista parcial del plan |
| HITL rejection | Plan maestro no se regenera (ok) | Spec se regenera en re-run (costoso) |
| Complejidad del grafo | Ninguna | +7 nodos o lógica adicional por nodo |

Los agentes ya tienen mecanismo propio para adaptarse al contexto acumulado (`load_prompt()` + `_get_last_feedback()`). Speckit por nodo agregaría una meta-capa sobre lo que los agentes ya hacen.

**Convenciones speckit**
- `get_phase_instructions()` en `nodes/helper.py` — único punto de extracción
- Cada `<agente>_prompt.md` tiene sección `## Instrucciones del orquestador` con `{orchestrator_instructions}`
- Si `plan_phases` vacío (primer arranque antes de init), retorna `""` → prompt usa fallback `"Sin instrucciones adicionales."`
- Para cambiar modelo speckit: `MODEL_SPECKIT` en `config/settings.py` o env var

## Flujo HITL
1. Agente termina → guarda output en `state`
2. `hitl_<fase>_node` llama `notify_reviewer()` → DM Slack con botones
3. `interrupt()` pausa el grafo — estado persiste en checkpointer
4. Revisor hace click → `POST /slack/interactive` → `_resume_graph(thread_id, payload)`
5. Grafo reanuda con `Command(resume=payload)` → routing según `decision`

## Fases y dependencias
```
PRD → UX → ARQ → DEV → QA → INFRA → SEC → DONE
```
Cada flecha tiene un checkpoint HITL individual. Si se rechaza, el agente re-corre con
`hitl_decisions[-1]["feedback"]` inyectado en su prompt.

## No hacer
- No modificar `CycleState` sin actualizar `initial_state()` en `state/cycle_state.py`
- No usar `InMemorySaver` en producción — cambiar a `SqliteSaver`
- No hardcodear `thread_id` — siempre viene de `state["thread_id"]`
- No hacer `graph.invoke()` sin pasar `config = get_graph_config(thread_id)`
- No usar `MODEL_ORCHESTRATOR` para speckit — es 8b-instant, solo sirve para routing
- No agregar `get_phase_instructions()` dentro de los nodos — siempre via `nodes/helper.py`

## @imports para contexto adicional
@state/cycle_state.py
@graph/mach_graph.py
