# MACH Race 2026 - MACH-ORCHESTRATOR

Orquestador agéntico del ciclo ADLC para Hackathon MACHBank usando LangGraph, FastAPI, Slack, Jira y Streamlit (hasta el momento).

El proyecto ejecuta un flujo de desarrollo por fases con Human-in-the-Loop (HITL) entre entregables. Cada fase genera artefactos, notifica revisores por Slack, pausa el grafo con checkpoints y reanuda la ejecución cuando una persona aprueba o rechaza el resultado.

## Qué hace

- Orquesta un ciclo ADLC con LangGraph y estado persistente por `thread_id`
- Ejecuta agentes especializados por fase: PRD, UX, ARQ, DEV, QA, INFRA y SEC
- Usa checkpoints HITL con `interrupt()` para aprobación humana vía Slack
- Crea y actualiza tickets en Jira durante el ciclo
- Publica entregables Markdown en `outputs/`
- Expone un dashboard en Streamlit para inspeccionar el estado del ciclo

## Flujo del ciclo

El ciclo es completamente secuencial. Cada agente tiene su propio checkpoint HITL independiente:

```text
START
  → orchestrator_init
  → run_prd   → hitl_notify_prd  → hitl_prd
  → run_ux    → hitl_notify_ux   → hitl_ux
  → run_arch  → hitl_notify_arch → hitl_arch
  → run_dev   → hitl_notify_dev  → hitl_dev
  → run_qa    → hitl_notify_qa   → hitl_qa
  → run_infra → hitl_notify_infra → hitl_infra
  → run_sec   → hitl_notify_sec  → hitl_sec
  → finalize
  → END
```

Cada checkpoint HITL son dos nodos separados:

- `hitl_notify_{fase}`: envía el DM de Slack y guarda `ts + channel` en el estado. Se ejecuta una sola vez; no se repite en el replay.
- `hitl_{fase}`: llama a `interrupt()` y espera la decisión. Al reanudar, procesa la respuesta y actualiza `current_phase`.

El routing post-HITL usa conditional edges que leen `current_phase`:
- Si aprueban: `current_phase` avanza → el edge va al siguiente agente.
- Si rechazan: `current_phase` se mantiene → el edge vuelve al mismo agente con el feedback inyectado.

## Stack

- Python 3.12
- LangGraph 1.x
- FastAPI + Uvicorn
- Slack SDK
- python-jira
- Streamlit (dashboard legacy)
- Vue.js 3 + Vite + TailwindCSS (frontend moderno)
- Pydantic v2
- LangChain + Groq

## Estructura principal

```text
main.py                    # Punto de entrada del ciclo
config/settings.py         # Variables de entorno y modelos
graph/mach_graph.py        # Definición del StateGraph
state/cycle_state.py       # Estado compartido del ciclo
api/slack_webhook.py       # Webhook para botones y modales de Slack
nodes/                     # Nodos del orquestador, agentes e HITL
tools/slack_tools.py       # Notificaciones y mensajes interactivos
tools/jira_tools.py        # Integración con Jira
dashboard/app.py           # Dashboard Streamlit (legacy)
frontend/                  # Dashboard Vue.js moderno (Race Control)
outputs/                   # Entregables generados
```

## Prerrequisitos

- Python 3.12 instalado
- Un workspace con este repositorio clonado
- Credenciales válidas para Groq, Slack y Jira si vas a correr el flujo real
- `ngrok` o una URL pública equivalente si Slack debe llamar tu webhook local

## Instalación SIN Docker

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuración

Crea tu archivo `.env` a partir del ejemplo:

```bash
cp .env.example .env
```

### Variables obligatorias

Aunque uses `TEST_MODE=true`, hoy el proyecto importa varias variables de Slack y Jira en `config/settings.py` al arrancar. Por eso debes definirlas igual para evitar errores de importación.

```env
GROQ_API_KEY=gsk_...

SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
SLACK_TEAM_CHANNEL=C0XXXXXXX
SLACK_USER_PO=U0XXXXXXX
SLACK_USER_ARCHITECT=U0YYYYYYY
SLACK_USER_DEV_LEAD=U0ZZZZZZZ
SLACK_USER_QA_LEAD=U0AAAAAAA
SLACK_USER_DEVOPS=U0BBBBBBB

JIRA_SERVER=https://your-org.atlassian.net
JIRA_EMAIL=your-email@machbank.com
JIRA_API_TOKEN=ATATT...
JIRA_PROJECT_KEY=MACH

WEBHOOK_BASE_URL=http://localhost:8000
WEBHOOK_PORT=8000
DASHBOARD_URL=http://localhost:8501
```

### Variables recomendadas para desarrollo

```env
TEST_MODE=true
CHECKPOINTER=memory
```

### Variables recomendadas para desarrollo con persistencia y dashboard

```env
TEST_MODE=true
CHECKPOINTER=sqlite
SQLITE_PATH=./mach_cycle.db
```

### LangSmith

Opcional, pero útil para observabilidad:

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=mach-orchestrator
```

## Cómo correr el proyecto

### Opción 1: flujo normal en dos terminales

Terminal 1, webhook de Slack:

```bash
source .venv/bin/activate
uvicorn api.slack_webhook:app --reload --port 8000
```

Terminal 2, ciclo principal:

```bash
source .venv/bin/activate
python main.py
```

Qué ocurre:

- `python main.py` crea un `thread_id`
- Inicializa el estado del ciclo
- Construye el grafo de LangGraph
- Corre hasta el primer checkpoint HITL
- Envía un DM de Slack al revisor de la fase
- Queda pausado hasta recibir aprobación o rechazo

### Opción 2: webhook y ciclo en un solo proceso

```bash
source .venv/bin/activate
python main.py both
```

Esto levanta el webhook en background y luego arranca el ciclo.

### Opción 3: solo webhook

```bash
source .venv/bin/activate
python main.py webhook
```

### Opción 4: con Docker Compose (recomendado para demo/producción)

Levanta todos los servicios en contenedores:

```bash
docker-compose up -d --build
```

Esto arranca:

- **mach-api**: FastAPI backend en puerto 8000
- **mach-frontend**: Vue.js frontend (Race Control) en puerto 5173
- **sqlite volume**: volumen compartido `mach-data` para persistencia

Acceso a los servicios:

```text
Backend API:   http://localhost:8000
Frontend UI:   http://localhost:5173
Logs en vivo:  docker-compose logs -f
```

Ver estado de los contenedores:

```bash
docker-compose ps
docker-compose logs mach-frontend
```

Detener:

```bash
docker-compose down
```

**Notas importantes para Docker:**

- El archivo `.env` DEBE estar presente en la raíz del proyecto. Los contenedores lo leen en startup.
- El frontend Vue.js se construye optimizado para producción con nginx.
- El proxy `/api` y `/deliverables` del frontend apunta automáticamente a `mach-api:8000` dentro de Docker.
- Para exponer el webhook a Slack, usa Cloudflare Tunnel o ngrok afuera del contenedor:

```bash
cloudflared tunnel --url http://localhost:8000
```

Luego actualiza en `.env`:

```env
WEBHOOK_BASE_URL=https://tu-tunnel.trycloudflare.com
```

Y configura en Slack App > Interactivity > Request URL:

```text
https://tu-tunnel.trycloudflare.com/slack/interactive
```

## Dashboard Streamlit (Legacy)

Para usar el dashboard Streamlit entre procesos necesitas persistencia real. Configura:

```env
CHECKPOINTER=sqlite
SQLITE_PATH=./mach_cycle.db
```

Luego ejecútalo:

```bash
source .venv/bin/activate
streamlit run dashboard/app.py --server.port 8501
```

El dashboard permite:

- Consultar el estado por `thread_id`
- Ver fase actual
- Ver decisiones HITL
- Ver entregables generados
- Ver datos de Jira

## Frontend Dashboard (Race Control)

Nueva UI moderna construida con Vue.js 3, Vite y TailwindCSS.

### Instalación

```bash
cd frontend
npm install
```

### Desarrollo

```bash
npm run dev
```

Por defecto corre en `http://localhost:5173`

### Build para producción

```bash
npm run build
npm run preview
```

### Características

- **Race Track Visual**: Timeline animado mostrando progreso de fases
- **Editor de Prompts**: Editar prompts de agentes en vivo
- **New Cycle**: Interfaz para iniciar nuevos ciclos ADLC
- **Estado en tiempo real**: Consume API del backend para mostrar estado del ciclo
- **Responsive**: Diseño adaptativo con TailwindCSS

### Requisitos

- Node.js 18+ / npm 9+
- Backend corriendo en `http://localhost:8000` (configurable en `vite.config.js`)

## Integración con Slack en local

Si vas a usar botones reales de Slack contra tu máquina local:

1. Levanta el webhook en el puerto 8000.
2. Expón ese puerto con `ngrok`:

```bash
ngrok http 8000
```

3. Copia la URL pública a tu `.env`:

```env
WEBHOOK_BASE_URL=https://tu-subdominio.ngrok.io
```

4. Configura en tu Slack App:

```text
Interactivity Request URL:
https://tu-subdominio.ngrok.io/slack/interactive
```

5. Verifica que el bot tenga permisos para enviar DMs y abrir modales.

## Entregables generados

Los agentes guardan artefactos Markdown en `outputs/`. Algunos nombres esperados en el flujo son:

- `PRDSPECS.md`
- `UXSPECS.md`
- `ARQSPECS.md`
- `DEVSPECS.md`
- `QASCPECS.md`
- `INFESPEOS.md`
- `DEVSECOPS.md`

Además, FastAPI expone esos archivos en:

```text
http://localhost:8000/deliverables/<archivo>
```

## Modo de prueba

El helper de LLM soporta `TEST_MODE=true`. En ese modo, las llamadas a modelos retornan contenido stub y no consumen tokens.

```env
TEST_MODE=true
```

Esto sirve para validar:

- Flujo del grafo
- Checkpoints HITL
- Slack
- Jira
- Dashboard

## Cambios recientes (último commit)

Commit `36fc077` — _ciclo lineal y fix slack_:

- **Ciclo secuencial**: se eliminaron los wrappers paralelos `run_ux_arch_parallel` y `run_infra_sec_parallel`. Ahora cada agente (`run_ux`, `run_arch`, `run_infra`, `run_sec`) tiene su propio nodo independiente.
- **HITL split en dos nodos**: cada checkpoint pasa de ser un solo nodo a dos — `hitl_notify_{fase}` envía el DM y `hitl_{fase}` hace el `interrupt()`. Esto resuelve el bug de DMs duplicados en el replay de LangGraph.
- **Routing via conditional edges**: los nodos HITL ya no usan `Command(goto=...)` para rutear. El routing se hace con `add_conditional_edges` que leen `current_phase`. Approve avanza la fase, reject la mantiene.
- **`PhaseName` granular**: los valores en `CycleState` cambiaron de `"ux_arch"` / `"infra_sec"` a `"ux"`, `"arch"`, `"infra"`, `"sec"` como fases independientes.
- **`hitl_slack_channel`**: nuevo campo en `CycleState` que guarda el canal del DM para poder actualizar el mensaje después de la decisión.
- **Dashboard granular**: `dashboard/constants.py` ahora muestra 9 fases separadas en la timeline.
- **`PHASE_HITL_CONFIG` actualizado**: config separada para UX, ARQ, INFRA y SEC con revisores y entregables propios.

## Estado actual y limitaciones conocidas

- El orquestador en [nodes/orchestrator_node.py](nodes/orchestrator_node.py) usa un plan hardcodeado tipo stub en lugar de invocar el modelo del orquestador.
- Aunque `TEST_MODE=true` evita llamadas al LLM en los nodos que usan `nodes/helper.py`, las credenciales de Slack y Jira siguen siendo necesarias al importar configuración.
- El checkpointer por defecto es `memory`. Si reinicias el proceso, pierdes el estado pausado del ciclo.
- Para reanudar ciclos entre procesos o usar el dashboard, usa `CHECKPOINTER=sqlite`.
- Los nodos `run_ux` y `run_arch` corren secuencialmente (no en paralelo real), igual que `run_infra` y `run_sec`. El grafo los ejecuta uno después del otro.

## Ejemplo de arranque rápido

```bash
cp .env.example .env
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.slack_webhook:app --reload --port 8000
```

En otra terminal:

```bash
source .venv/bin/activate
python main.py
```

## Troubleshooting

### Falla al arrancar por variables de entorno faltantes

Completa las variables de Slack y Jira en `.env`. Varias se leen con `os.environ[...]` y lanzan excepción si no existen.

### Slack no reanuda el flujo

- Verifica `SLACK_SIGNING_SECRET`
- Verifica que la URL pública apunte a `/slack/interactive`
- Revisa que el `thread_id` se esté preservando en los botones
- Confirma que el proceso del webhook siga vivo

### El dashboard no encuentra el estado

- Asegúrate de usar `CHECKPOINTER=sqlite`
- Revisa que `SQLITE_PATH` apunte al mismo archivo usado por el ciclo
- Confirma que estás consultando el `thread_id` correcto

### El ciclo pierde contexto al reiniciar

Eso es esperado con `CHECKPOINTER=memory`. Cambia a `sqlite`.

## Comandos útiles

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar ciclo
python main.py

# Ejecutar solo webhook
python main.py webhook

# Ejecutar webhook + ciclo
python main.py both

# Ejecutar dashboard Streamlit (legacy)
streamlit run dashboard/app.py --server.port 8501

# Ejecutar frontend Vue.js (Race Control)
cd frontend && npm run dev

# Build frontend para producción
cd frontend && npm run build

# Exponer webhook local
ngrok http 8000
```

## Convenciones importantes del proyecto

- Cada nodo retorna solo los campos del estado que modifica
- El `thread_id` siempre viene del estado, no se genera dentro de los nodos
- Slack y Jira no deben romper el ciclo si fallan; se loguea y se continúa
- Los handlers de FastAPI son `async`, pero los nodos y tools son síncronos
- No uses `graph.invoke()` sin pasar `get_graph_config(thread_id)`

## Próximos pasos recomendados

1. Completar un `.env` real de desarrollo.
2. Mover el orquestador desde stub a llamada real al modelo.
3. Fijar `CHECKPOINTER=sqlite` como configuración por defecto para desarrollo.
4. Agregar tests automatizados para el flujo HITL y el webhook.