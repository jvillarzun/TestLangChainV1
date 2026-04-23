# Prompt para generar PPT animada en Gamma.app / Beautiful.ai / ChatGPT

Copia y pega este prompt en [gamma.app](https://gamma.app), [beautiful.ai](https://beautiful.ai), o ChatGPT con canvas/artifacts para generar la presentación.

---

## PROMPT

```
Genera una presentación profesional de 12 slides sobre un sistema de orquestación agéntica para desarrollo de software llamado "MACH Race 2026 — MACH-ORCHESTRATOR".

ESTILO VISUAL:
- Fondo oscuro (#0B0F1A), texto claro (#E2E8F0)
- Acentos en violeta (#7C3AED), rosa (#EC4899), verde (#10B981), cyan (#06B6D4)
- Tipografía Inter o similar sans-serif moderna
- Iconos emoji como elementos visuales principales
- Estilo tech/startup, minimalista, con gradientes sutiles
- Animaciones de entrada por elemento (fade-in + slide)

SLIDES:

SLIDE 1 — PORTADA
Título: "MACH Race 2026"
Subtítulo: "Orquestación Agéntica del Ciclo ADLC"
Badges: LangGraph · FastAPI · Groq · OpenAI · Gemini · ChromaDB
Fondo con gradiente violeta sutil

SLIDE 2 — EL PROBLEMA
Título: "El ciclo de desarrollo es lento y fragmentado"
3 pain points con iconos:
- ⏱️ Semanas entre especificación y código
- 🔄 Feedback loops manuales entre equipos
- 📋 Documentación desactualizada al entregar
Mensaje: "¿Y si cada fase tuviera un agente especializado?"

SLIDE 3 — LA SOLUCIÓN
Título: "8 Agentes Especializados, 1 Orquestador"
Pipeline horizontal con iconos y flechas:
🎯 Orquestador → 📋 PRD → 🎨 UX → 🏛️ Arquitecto → 💻 Dev → 🧪 QA → ☁️ Infra → 🔒 Security → ✅ DONE
Debajo: "Cada agente genera entregables reales, con aprobación humana entre fases"

SLIDE 4 — HUMAN-IN-THE-LOOP
Título: "Control Humano en Cada Fase"
Diagrama: Agente genera → Slack DM al revisor → Botones Aprobar/Rechazar
- Approve → avanza a siguiente fase
- Reject → agente re-ejecuta con feedback inyectado
Destacar: "El humano siempre tiene la última palabra"

SLIDE 5 — MULTI-LLM
Título: "El Modelo Correcto para Cada Tarea"
Tabla visual:
| Agente | Modelo | Proveedor |
| Orquestador | llama-3.1-8b-instant | Groq |
| PRD, UX, QA, Infra, Sec | llama-3.3-70b | Groq |
| Arquitecto | gemini-2.5-flash | Google |
| Dev | gpt-4o-mini | OpenAI |
Mensaje: "A/B testing de modelos desde el dashboard"

SLIDE 6 — RAG & KNOWLEDGE BASE
Título: "Cada Agente Tiene Su Propia Base de Conocimiento"
Flujo: Prompt → Template Matcher (archivos completos) + ChromaDB (chunks semánticos) → LLM → Artefacto
3 capas: ⚙️ Prompt editable · 📐 Templates reales · 🧠 RAG por agente
Ejemplo: "Si pides tarjeta de crédito, el Dev recibe el template HTML completo como base"

SLIDE 7 — DEV AGENT: SELF-HEALING (slide estrella)
Título: "💻 Dev Agent — Se Auto-Corrige"
Flujo horizontal:
🤖 LLM genera → 🔎 Validador (12 patrones) → 📦 Parser → 🔄 [Self-Healing Loop: 🚨 Error → 🔧 Re-invoca LLM → ✅ Re-valida] → 🐙 GitHub PR → ⏸ HITL
Destacar el loop con borde punteado amarillo
Stats: 3 capas validación · 3 auto-correcciones · 12 patrones detectados

SLIDE 8 — GITHUB INTEGRATION
Título: "Del Código al Pull Request — Automático"
Flujo: Dev Agent genera archivos → Parser extrae → Branch feat/adlc-{id} → Commit → PR con ENGINEERING_PLAN
Screenshot o mockup de un PR en GitHub
Mensaje: "Zero manual git — el agente hace push y abre PR"

SLIDE 9 — DASHBOARD: RACE CONTROL
Título: "Monitoreo en Tiempo Real"
4 features con screenshots/mockups:
- 🏁 Race Track: timeline visual del progreso
- ✏️ Editor de Prompts: editar prompts de agentes en vivo
- 🧠 Knowledge Base: subir docs, probar RAG, A/B de modelos
- 🔄 Iteración: preview HTML + feedback → regenerar
Stack: Vue.js 3 + Vite + TailwindCSS

SLIDE 10 — ESPECIALISTAS
Título: "Agentes Especializados por Stack"
Grid:
Dev: 🌐 Web (React, Vue, Next) · 📱 Android (Kotlin Compose) · 🍎 iOS (SwiftUI) · ⚙️ Backend (FastAPI, Node)
Architect: ☁️ Cloud Native · 📱 Mobile Arch · 🔗 Event-Driven
UX: 📱 Mobile UX · 🌐 Web UX · 💰 Fintech UX
Mensaje: "El RAG y templates se adaptan automáticamente al stack"

SLIDE 11 — ROADMAP / POSIBILIDADES
Título: "Evolución del Sistema"
4 cards con impacto:
- 🔀 Agentes Paralelos — UX+Arch en paralelo (Alto impacto)
- 🧪 QA con Tests Reales — Playwright + Jest (Muy alto)
- 🧠 RAG Dinámico — Aprende de ciclos anteriores (Muy alto)
- 📋 Compliance Agent — PCI-DSS, GDPR para fintech (Alto)

SLIDE 12 — CIERRE
Título: "MACH Race 2026"
Subtítulo: "De la idea al Pull Request — orquestado por agentes"
Stats grandes: 8 Agentes · 7 HITL · 3 LLMs · 12 Validaciones · Auto-Healing
Call to action o contacto
```

---

## Dónde usarlo

| Herramienta | URL | Notas |
|-------------|-----|-------|
| **Gamma.app** | https://gamma.app | Pega el prompt → genera PPT animada con AI. Mejor resultado. |
| **Beautiful.ai** | https://beautiful.ai | Diseño automático profesional. |
| **ChatGPT + Canvas** | https://chat.openai.com | Pide "genera una presentación" con el prompt. |
| **Tome.app** | https://tome.app | Genera slides con AI desde texto. |
| **Google Slides + Gemini** | slides.google.com | Usa Gemini para generar contenido slide por slide. |

## Tips

- En Gamma.app: selecciona tema "Dark" y estilo "Tech/Startup"
- Agrega los diagramas HTML como screenshots en los slides 7 y 3
- Los archivos HTML están en:
  - `docs/arquitectura-ppt.html` → para slide 3
  - `docs/self-healing-ppt.html` → para slide 7
