# 🏁 MACH Race 2026 - Guía Completa del Proyecto

## 📋 Resumen Ejecutivo

**MACH-ORCHESTRATOR** es un sistema agéntico que automatiza el ciclo completo de desarrollo de software (ADLC) usando LangGraph, con checkpoints Human-in-the-Loop (HITL) vía Slack para aprobaciones humanas entre fases.

### ¿Qué hace?
- Orquesta 7 agentes especializados (PRD, UX, ARQ, DEV, QA, INFRA, SEC)
- Cada agente genera entregables específicos (documentos Markdown)
- Pausa entre fases para aprobación humana vía Slack
- Integra con Jira para tracking de tickets
- Expone dashboard web para monitoreo en tiempo real

### Stack Tecnológico
```
Backend:  Python 3.12 + LangGraph + FastAPI + Groq (LLMs)
Frontend: Vue.js 3 + Vite + TailwindCSS
DB:       SQLite (checkpoints) + ChromaDB (RAG)
Integr.:  Slack SDK + Jira API + GitHub API
Deploy:   Docker Compose
```

---

## 🏗️ Arquitectura del Sistema

### Flujo Principal (Secuencial)
```
START → PRD → UX → ARQ → DEV → QA → INFRA → SEC → END
         ↓     ↓     ↓     ↓     ↓      ↓      ↓
      [HITL] [HITL] [HITL] [HITL] [HITL] [HITL] [HITL]
```

Cada fase tiene 3 nodos:
1. **`run_{fase}`** - Ejecuta el agente LLM
2. **`hitl_notify_{fase}`** - Envía DM de Slack con botones
3. **`hitl_{fase}`** - Pausa con `interrupt()` hasta aprobación

### Componentes Clave

| Componente | Ubicación | Propósito |
|------------|-----------|-----------|
| **Estado Global** | `state/cycle_state.py` | Estado compartido entre todos los nodos |
| **Grafo LangGraph** | `graph/mach_graph.py` | Definición del flujo y routing |
| **Agentes** | `nodes/{agente}/` | 7 agentes especializados + orquestador |
| **API Webhook** | `api/slack_webhook.py` | Recibe callbacks de Slack |
| **Dashboard Vue** | `frontend/` | Interfaz web moderna (Race Control) |
| **Dashboard Legacy** | `dashboard/` | Interfaz Streamlit (deprecado) |
| **Herramientas** | `tools/` | Integración Slack, Jira, GitHub |

---

## 📁 Estructura de Carpetas Detallada

```
📦 MACH-ORCHESTRATOR/
├── 🐍 **BACKEND PYTHON**
│   ├── main.py                     # 🚀 Punto de entrada principal
│   ├── config/settings.py          # ⚙️ Variables de entorno
│   ├── state/cycle_state.py        # 📊 Estado global del ciclo
│   ├── graph/mach_graph.py         # 🔄 Definición del grafo LangGraph
│   │
│   ├── nodes/                      # 🤖 Agentes y nodos
│   │   ├── orchestrator_node.py    # 🎯 Orquestador principal
│   │   ├── hitl_node.py           # ⏸️ Checkpoints humanos
│   │   ├── helper.py              # 🛠️ Utilidades LLM
│   │   ├── prd/prd_node.py        # 📋 Agente PRD
│   │   ├── ux/ux_node.py          # 🎨 Agente UX
│   │   ├── arch/arch_node.py      # 🏛️ Agente Arquitectura
│   │   ├── dev/dev_node.py        # 💻 Agente Desarrollo
│   │   ├── qa/qa_node.py          # 🧪 Agente QA
│   │   ├── infra/infra_node.py    # ☁️ Agente Infraestructura
│   │   └── sec/sec_node.py        # 🔒 Agente Seguridad
│   │
│   ├── api/                       # 🌐 APIs y webhooks
│   │   ├── slack_webhook.py       # 📱 Webhook Slack
│   │   ├── rag_routes.py          # 🧠 Endpoints RAG
│   │   └── control.py             # 🎮 Control del ciclo
│   │
│   ├── tools/                     # 🔧 Integraciones externas
│   │   ├── slack_tools.py         # 📱 Herramientas Slack
│   │   ├── jira_tools.py          # 🎫 Herramientas Jira
│   │   └── github_tools.py        # 🐙 Herramientas GitHub
│   │
│   └── rag/                       # 🧠 Sistema RAG
│       ├── chroma_store.py        # 💾 Base vectorial
│       ├── rag_helper.py          # 🔍 Búsqueda semántica
│       └── templates/             # 📚 Plantillas por agente
│
├── 🖥️ **FRONTEND VUE.JS**
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── App.vue            # 🏠 Componente raíz
│   │   │   ├── main.js            # ⚡ Punto de entrada
│   │   │   ├── components/        # 🧩 Componentes reutilizables
│   │   │   │   ├── NavBar.vue     # 🧭 Navegación
│   │   │   │   └── RaceTrack.vue  # 🏁 Timeline visual
│   │   │   ├── views/             # 📄 Páginas principales
│   │   │   │   ├── RaceDashboard.vue    # 📊 Dashboard principal
│   │   │   │   ├── NewCycle.vue         # ➕ Crear nuevo ciclo
│   │   │   │   ├── PromptEditor.vue     # ✏️ Editor de prompts
│   │   │   │   └── KnowledgeBase.vue    # 📚 Base de conocimiento
│   │   │   └── stores/            # 🗄️ Estado global (Pinia)
│   │   │       └── cycleStore.js  # 📊 Store del ciclo
│   │   ├── package.json           # 📦 Dependencias Node.js
│   │   └── vite.config.js         # ⚙️ Configuración Vite
│
├── 🐳 **DOCKER & DEPLOY**
│   ├── docker-compose.yml         # 🐳 Orquestación contenedores
│   ├── Dockerfile                 # 🐳 Imagen backend
│   ├── frontend/Dockerfile        # 🐳 Imagen frontend
│   └── start_dev.sh              # 🚀 Script desarrollo local
│
├── 📊 **DATOS Y OUTPUTS**
│   ├── outputs/                   # 📄 Entregables generados
│   │   ├── PRDSPECS.md           # 📋 Especificaciones PRD
│   │   ├── UXSPECS.md            # 🎨 Especificaciones UX
│   │   ├── ARQSPECS.md           # 🏛️ Especificaciones Arquitectura
│   │   └── ...                   # 📄 Otros entregables
│   ├── rag_data/                 # 🧠 Base vectorial ChromaDB
│   └── data/                     # 💾 Base de datos SQLite
│
└── 📚 **DOCUMENTACIÓN**
    ├── README.md                  # 📖 Documentación principal
    ├── CLAUDE.md                  # 🤖 Guía para Claude
    ├── GUIA_PROYECTO.md          # 📋 Esta guía
    └── requirements.txt           # 📦 Dependencias Python
```

---

## 🔄 Flujo de Ejecución Detallado

### 1. Inicio del Ciclo
```bash
python main.py
```
1. Genera `thread_id` único
2. Crea estado inicial con challenge
3. Construye grafo LangGraph
4. Ejecuta `orchestrator_init_node`

### 2. Ejecución de Agentes
Cada agente sigue este patrón:
```
run_{agente} → hitl_notify_{agente} → hitl_{agente}
     ↓                ↓                    ↓
  Genera         Envía DM Slack      Pausa con interrupt()
 entregable      con botones         hasta aprobación
```

### 3. Checkpoint HITL (Human-in-the-Loop)
1. **Notify**: Envía DM a revisor con botones "Aprobar/Rechazar"
2. **Interrupt**: Pausa grafo con `interrupt()`
3. **Webhook**: Recibe callback de Slack cuando usuario hace click
4. **Resume**: Reanuda grafo con decisión del usuario

### 4. Routing Post-HITL
- **Aprobar**: `current_phase` avanza → siguiente agente
- **Rechazar**: `current_phase` se mantiene → mismo agente con feedback

---

## 🛠️ Dónde Modificar Cada Cosa

### 🤖 Agregar/Modificar Agentes

**Crear nuevo agente:**
```
1. Crear carpeta: nodes/mi_agente/
2. Crear nodo: nodes/mi_agente/mi_agente_node.py
3. Crear prompt: nodes/mi_agente/mi_agente_prompt.md
4. Registrar en: graph/mach_graph.py
5. Agregar estado: state/cycle_state.py
```

**Modificar agente existente:**
- **Lógica**: `nodes/{agente}/{agente}_node.py`
- **Prompt**: `nodes/{agente}/{agente}_prompt.md`
- **Estado**: `state/cycle_state.py` (si necesita nuevos campos)

### 📱 Modificar Integración Slack

**Mensajes y notificaciones:**
- `tools/slack_tools.py` - Funciones de envío
- `nodes/hitl_node.py` - Lógica HITL
- `api/slack_webhook.py` - Manejo de callbacks

**Configuración:**
- `.env` - Tokens y secrets
- `config/settings.py` - Variables de entorno

### 🎫 Modificar Integración Jira

**Creación de tickets:**
- `tools/jira_tools.py` - Funciones CRUD
- `nodes/orchestrator_node.py` - Creación de Epic
- Cada agente puede crear tickets específicos

### 🖥️ Modificar Frontend

**Páginas principales:**
- `frontend/src/views/` - Páginas completas
- `frontend/src/components/` - Componentes reutilizables

**Estado global:**
- `frontend/src/stores/cycleStore.js` - Estado Pinia

**Estilos:**
- `frontend/src/style.css` - CSS global
- `frontend/tailwind.config.js` - Configuración Tailwind

### 🔄 Modificar Flujo del Grafo

**Orden de fases:**
- `graph/mach_graph.py` - Edges y conditional routing
- `state/cycle_state.py` - Enum `PhaseName`

**Lógica de routing:**
- `graph/mach_graph.py` - Función `_route_hitl()`
- `nodes/hitl_node.py` - Lógica de aprobación/rechazo

### 🧠 Modificar Sistema RAG

**Plantillas de conocimiento:**
- `rag/templates/{agente}/` - Documentos por agente
- `rag/seed.py` - Carga inicial de datos

**Búsqueda semántica:**
- `rag/rag_helper.py` - Lógica de búsqueda
- `rag/chroma_store.py` - Configuración ChromaDB

---

## ⚙️ Configuración y Variables

### Variables de Entorno Críticas
```env
# LLMs
GROQ_API_KEY=gsk_...                    # 🔑 API Groq (obligatorio)

# Slack
SLACK_BOT_TOKEN=xoxb-...                # 🤖 Token del bot
SLACK_SIGNING_SECRET=...                # 🔐 Secret para webhooks
SLACK_TEAM_CHANNEL=C0XXXXXXX            # 📢 Canal del equipo

# Jira
JIRA_SERVER=https://org.atlassian.net   # 🏢 Servidor Jira
JIRA_EMAIL=email@company.com            # 📧 Email usuario
JIRA_API_TOKEN=ATATT...                 # 🔑 Token API

# Sistema
WEBHOOK_BASE_URL=http://localhost:8000  # 🌐 URL pública webhook
CHECKPOINTER=sqlite                     # 💾 Tipo de persistencia
SQLITE_PATH=./mach_cycle.db            # 📁 Ruta base datos
```

### Modos de Operación
```env
# Desarrollo (sin gastar tokens)
TEST_MODE=true

# Producción (LLMs reales)
TEST_MODE=false

# Persistencia
CHECKPOINTER=memory    # Sin persistencia
CHECKPOINTER=sqlite    # Con persistencia
```

---

## 🚀 Comandos de Desarrollo

### Instalación Inicial
```bash
# Backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### Desarrollo Local
```bash
# Opción 1: Docker (recomendado)
docker-compose up --build

# Opción 2: Manual (2 terminales)
# Terminal 1: Webhook
uvicorn api.slack_webhook:app --reload --port 8000

# Terminal 2: Ciclo
python main.py

# Terminal 3: Frontend (opcional)
cd frontend && npm run dev
```

### Desarrollo con Tunnel (Slack)
```bash
# Usar script automático
bash start_dev.sh

# O manual
cloudflared tunnel --url http://localhost:8000
# Copiar URL a .env y configurar en Slack App
```

### Testing
```bash
# Modo test (sin tokens)
TEST_MODE=true python main.py

# Solo webhook
python main.py webhook

# Webhook + ciclo
python main.py both
```

---

## 🔍 Debugging y Troubleshooting

### Problemas Comunes

**1. Error al arrancar - Variables faltantes**
```bash
# Solución: Completar .env
cp .env.example .env
# Editar .env con valores reales
```

**2. Slack no reanuda el flujo**
```bash
# Verificar:
- SLACK_SIGNING_SECRET correcto
- URL webhook pública accesible
- Proceso webhook corriendo
- thread_id preservado en botones
```

**3. Dashboard no encuentra estado**
```bash
# Verificar:
- CHECKPOINTER=sqlite en .env
- SQLITE_PATH apunta al mismo archivo
- thread_id correcto en consulta
```

**4. Frontend no conecta con backend**
```bash
# Verificar:
- Backend corriendo en puerto 8000
- Proxy configurado en vite.config.js
- CORS habilitado en FastAPI
```

### Logs Útiles
```bash
# Docker logs
docker-compose logs -f mach-api
docker-compose logs -f mach-frontend

# Estado contenedores
docker-compose ps

# Logs aplicación
tail -f /tmp/cf_tunnel.log  # Cloudflare tunnel
```

---

## 📊 Monitoreo y Observabilidad

### Dashboard Web (Race Control)
- **URL**: http://localhost:5173
- **Funciones**: Timeline visual, estado en tiempo real, editor prompts

### API Endpoints
```
GET  /health                    # Estado del servicio
GET  /deliverables/{filename}   # Descargar entregables
POST /slack/interactive         # Webhook Slack
GET  /api/cycles/{thread_id}    # Estado del ciclo
```

### LangSmith (Opcional)
```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=mach-orchestrator
```

---

## 🎯 Casos de Uso Frecuentes

### Agregar Nueva Fase
1. Crear agente en `nodes/nueva_fase/`
2. Agregar a `PhaseName` en `state/cycle_state.py`
3. Registrar en `graph/mach_graph.py`
4. Configurar HITL en `nodes/hitl_node.py`

### Cambiar Orden de Fases
1. Modificar edges en `graph/mach_graph.py`
2. Actualizar conditional routing
3. Ajustar timeline en frontend

### Personalizar Mensajes Slack
1. Editar templates en `tools/slack_tools.py`
2. Modificar botones y modales
3. Ajustar lógica en `api/slack_webhook.py`

### Agregar Nueva Integración
1. Crear herramientas en `tools/nueva_integracion.py`
2. Agregar variables en `config/settings.py`
3. Integrar en nodos relevantes

---

## 📚 Recursos Adicionales

### Documentación Técnica
- `README.md` - Documentación completa
- `CLAUDE.md` - Guía específica para Claude
- `docs/` - Diagramas y documentación técnica

### Dependencias Clave
- **LangGraph**: Framework de grafos para LLMs
- **FastAPI**: Framework web moderno
- **Vue.js 3**: Framework frontend reactivo
- **Pinia**: Gestión de estado Vue
- **TailwindCSS**: Framework CSS utility-first

### Enlaces Útiles
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Vue.js 3 Docs](https://vuejs.org/)
- [Slack API Docs](https://api.slack.com/)
- [Jira API Docs](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)

---

## ✅ Checklist de Desarrollo

### Antes de Empezar
- [ ] Python 3.12 instalado
- [ ] Node.js 18+ instalado
- [ ] Docker Desktop corriendo
- [ ] Archivo `.env` configurado
- [ ] Credenciales Groq, Slack, Jira válidas

### Para Modificaciones
- [ ] Entender el flujo actual
- [ ] Identificar componentes afectados
- [ ] Hacer cambios incrementales
- [ ] Probar en modo `TEST_MODE=true`
- [ ] Verificar integración completa

### Para Deploy
- [ ] Build frontend: `npm run build`
- [ ] Test Docker: `docker-compose up --build`
- [ ] Verificar health checks
- [ ] Configurar URLs públicas
- [ ] Monitorear logs

---

*Esta guía te ayudará a navegar y modificar el proyecto MACH-ORCHESTRATOR de manera eficiente. ¡Mantén esta referencia a mano durante el desarrollo!* 🚀