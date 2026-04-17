# MACH Race 2026 — MACH-ORCHESTRATOR

## Proyecto
Ciclo ADLC agéntico para MACHBank. LangGraph orquesta 7 agentes especializados
con checkpoints Human-in-the-Loop via Slack. Jira para tracking. FastAPI para webhooks.

## Stack
- Python 3.12 · LangGraph 1.0+ · FastAPI · Pydantic v2
- `langchain-anthropic` (Claude Opus/Sonnet) · `langchain-google-genai` (Gemini)
- `slack-sdk` · `jira` (python-jira) · `uvicorn`

## Arquitectura
```
state/cycle_state.py     → CycleState (TypedDict compartido entre todos los nodos)
graph/mach_graph.py      → StateGraph: build_graph(), get_graph_config()
nodes/orchestrator_node.py → init, route, finalize
nodes/hitl_node.py       → make_hitl_node(phase) — usa interrupt() de LangGraph
nodes/agent_nodes.py     → 7 agentes stub (reemplazar con LLM real)
tools/slack_tools.py     → notify_team(), notify_reviewer(), update_hitl_msg()
tools/jira_tools.py      → create_epic/story/task(), update_issue_status()
api/slack_webhook.py     → POST /slack/interactive — reanuda el grafo con Command(resume=...)
config/settings.py       → todas las env vars (no hardcodear credenciales)
main.py                  → run_cycle(challenge) — punto de entrada
```

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
cp .env.example .env

# Correr el ciclo
python main.py

# Servidor webhook (terminal separada)
uvicorn api.slack_webhook:app --reload --port 8000

# Exponer webhook a Slack en dev
ngrok http 8000

# Tests (cuando existan)
pytest tests/ -v
```

## Variables de entorno requeridas
Ver `.env.example`. Críticas para arrancar:
`ANTHROPIC_API_KEY`, `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `JIRA_API_TOKEN`

## Modelo por agente
| Agente | Modelo | Razón |
|---|---|---|
| Orchestrator | `claude-opus-4-5-20251101` | Planificación compleja |
| PRD, QA, Infra | `claude-sonnet-4-5-20251101` | Redacción estructurada |
| UX | `gemini-1.5-pro` | Razonamiento visual/layout |
| Architect, Security | `claude-opus-4-5-20251101` | Decisiones con trade-offs |
| Dev | Claude Code (subprocess) | Escribe y ejecuta código real |

## Flujo HITL
1. Agente termina → guarda output en `state`
2. `hitl_<fase>_node` llama `notify_reviewer()` → DM Slack con botones
3. `interrupt()` pausa el grafo — estado persiste en checkpointer
4. Revisor hace click → `POST /slack/interactive` → `_resume_graph(thread_id, payload)`
5. Grafo reanuda con `Command(resume=payload)` → routing según `decision`

## Fases y dependencias
```
PRD → (UX ∥ ARQ) → DEV → QA → (INFRA ∥ SEC) → DONE
```
Cada flecha tiene un checkpoint HITL. Si se rechaza, el agente re-corre con
`hitl_decisions[-1]["feedback"]` inyectado en su prompt.

## No hacer
- No modificar `CycleState` sin actualizar `initial_state()` en `state/cycle_state.py`
- No usar `InMemorySaver` en producción — cambiar a `SqliteSaver`
- No hardcodear `thread_id` — siempre viene de `state["thread_id"]`
- No hacer `graph.invoke()` sin pasar `config = get_graph_config(thread_id)`

## @imports para contexto adicional
@state/cycle_state.py
@graph/mach_graph.py
