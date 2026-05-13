# Migración a Google Gemini 1.5 Flash — Guía de Implementación

## ✅ Cambios Aplicados

### 1. Dependencias
**Archivo**: `requirements.txt`

✅ **Ya instalado**: `langchain-google-genai>=2.0.0` (línea 4)

**Comando para instalar** (si necesitas actualizar el entorno):
```bash
pip install langchain-google-genai>=2.0.0
```

**Para Docker**, el paquete ya está en requirements.txt, así que solo necesitas:
```bash
podman compose build --no-cache mach-api
```

---

### 2. Configuración — `config/settings.py`

**Cambios realizados**:

```python
# Líneas 22-24 — API Keys actualizadas
GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "") if not TEST_MODE else "test"  # legacy, no usado
ANTHROPIC_API_KEY: str | None = os.environ.get("ANTHROPIC_API_KEY")  # reservado para P3 dev-agent
GOOGLE_API_KEY: str = os.environ.get("GOOGLE_API_KEY", "") if not TEST_MODE else "test"  # Motor LLM principal

# Líneas 26-34 — Modelos cambiados a Gemini
MODEL_ORCHESTRATOR = "gemini-1.5-flash"       # routing simple, modelo ligero y rápido
MODEL_PRD          = "gemini-1.5-flash"       # generación de PRD
MODEL_UX           = "gemini-1.5-flash"       # diseño de UX
MODEL_ARCHITECT    = "gemini-1.5-flash"       # arquitectura y engineering plan
MODEL_DEV          = "gemini-1.5-flash"       # generación de código
MODEL_QA           = "gemini-1.5-flash"       # testing y QA
MODEL_INFRA        = "gemini-1.5-flash"       # infraestructura
MODEL_SECURITY     = "gemini-1.5-flash"       # seguridad
```

**Qué cambió**:
- ✅ `GOOGLE_API_KEY` ahora es el motor principal (antes era "reservado")
- ✅ Todos los modelos cambiados de `llama-3.3-70b-versatile` → `gemini-1.5-flash`
- ✅ `GROQ_API_KEY` marcado como legacy (para rollback si es necesario)

---

### 3. Inicialización del LLM — `nodes/helper.py`

**Cambios realizados**:

```python
def create_llm(model: str) -> Any:
    """
    Crea instancia LLM. Único lugar para cambiar proveedor.
    
    Actualmente: Google Gemini 1.5 Flash vía LangChain.
    Parámetros optimizados para Gemini:
    - temperature=0.2: Balance entre creatividad y determinismo
    - convert_system_message_to_human=True: Recomendado por Google para mejor compatibilidad
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    from config.settings import GOOGLE_API_KEY
    
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.2,
        convert_system_message_to_human=True,  # Convierte system messages a formato que Gemini espera
    )
```

**Qué cambió**:
- ✅ Import: `ChatGroq` → `ChatGoogleGenerativeAI`
- ✅ API Key: `GROQ_API_KEY` → `GOOGLE_API_KEY`
- ✅ Parámetros optimizados para Gemini:
  - `temperature=0.2` (default en Groq era implícito)
  - `convert_system_message_to_human=True` (crítico para Gemini)
- ✅ Documentación actualizada

**La función `llm_invoke` NO requiere cambios** — sigue retornando `response.content` correctamente.

---

### 4. Variables de Entorno — `.env`

**Cambio aplicado**:

```bash
# ── LLMs ──────────────────────────────────────────────────────────────────────
GROQ_API_KEY=gsk_...  # legacy, no usado
ANTHROPIC_API_KEY=    # reservado para P3 dev-agent
GOOGLE_API_KEY=AIza...YOUR_GEMINI_API_KEY_HERE  # Motor LLM principal
```

**⚠️ ACCIÓN REQUERIDA**: Obtén tu API key de Google Gemini:

1. Ve a https://aistudio.google.com/app/apikey
2. Inicia sesión con tu cuenta de Google
3. Crea un nuevo proyecto (si no tienes uno)
4. Genera una API Key
5. Copia la key (empieza con `AIza...`)
6. Pégala en `.env` reemplazando `AIza...YOUR_GEMINI_API_KEY_HERE`

---

## 🚀 Despliegue

### Opción 1: Desarrollo local (sin Docker)

```bash
# 1. Instalar/actualizar dependencias
pip install -r requirements.txt

# 2. Configurar API key en .env
nano .env  # O tu editor preferido
# Pegar tu GOOGLE_API_KEY real

# 3. Reiniciar servidor
pkill -f uvicorn  # Matar proceso anterior
uvicorn api.slack_webhook:app --reload --port 8000
```

---

### Opción 2: Docker (Recomendado para producción)

```bash
# 1. Configurar API key en .env (mismo paso que arriba)
nano .env

# 2. Rebuild contenedor con nueva dependencia
podman compose build --no-cache mach-api

# 3. Reiniciar servicios
podman compose down
podman compose up -d

# 4. Verificar logs
podman logs -f mach-api
```

**Deberías ver**:
```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**NO deberías ver errores de API key** como:
```
❌ google.api_core.exceptions.Unauthenticated: 401 API key not valid
```

---

## 🧪 Testing

### Test rápido de la migración

```bash
# Test 1: Verificar que el servidor arranca sin errores
curl http://localhost:8000/health
# Esperado: {"status":"ok","service":"MACH Race Slack Webhook"}

# Test 2: Verificar que GOOGLE_API_KEY se carga
podman exec mach-api env | grep GOOGLE_API_KEY
# Esperado: GOOGLE_API_KEY=AIza...

# Test 3: Iniciar un ciclo desde el dashboard
# Ve a http://localhost:5173
# Inicia un nuevo challenge
# Monitorea logs:
podman logs -f mach-api | grep -E "PRD-AGENT|UX-AGENT|Gemini"
```

**Logs esperados con Gemini**:
```
📋 [PRD-AGENT] Generando PRDSPECS.md...
   🤖 Invocando Gemini 1.5 Flash...
   ✅ PRDSPECS.md generado (5234 chars)
```

---

## 🔄 Rollback (si algo falla)

Si Gemini no funciona y necesitas volver a Groq temporalmente:

```bash
# 1. Editar config/settings.py
# Cambiar todas las líneas MODEL_* de "gemini-1.5-flash" a "llama-3.3-70b-versatile"

# 2. Editar nodes/helper.py
# Reemplazar ChatGoogleGenerativeAI por ChatGroq
from langchain_groq import ChatGroq
from config.settings import GROQ_API_KEY
return ChatGroq(model=model, api_key=GROQ_API_KEY)

# 3. Reiniciar
podman compose restart mach-api
```

---

## 📊 Ventajas de Gemini 1.5 Flash sobre Groq/Llama

| Aspecto | Groq (Llama 3.3) | Gemini 1.5 Flash |
|---------|------------------|------------------|
| **Ventana de contexto** | 8K tokens | 1M tokens |
| **Formato de salida** | Inconsistente | Más confiable con JSON/Markdown |
| **Costo** | Free tier limitado | $0.075 / 1M input tokens |
| **Latencia** | Ultra-rápida (Groq hardware) | Rápida (Google TPU) |
| **Multimodal** | Solo texto | Texto + imágenes |
| **Rate limits** | Agresivos en free tier | Generosos (15 RPM) |

**Para tu caso de uso** (generación de código, PRDs, arquitectura):
- ✅ **Mejor seguimiento de instrucciones** (importante para parsers)
- ✅ **Contexto masivo** (puede ver repos completos)
- ✅ **Mejor con código** (entrenado con Codey)

---

## ⚠️ Troubleshooting

### Error: "401 API key not valid"
**Causa**: API key incorrecta o no configurada
**Solución**: Verifica que `.env` tenga `GOOGLE_API_KEY=AIza...` con una key real

### Error: "429 Quota exceeded"
**Causa**: Superaste el límite de rate (15 RPM en free tier)
**Solución**: 
- Activa billing en Google Cloud Console
- O agrega `time.sleep(5)` entre llamadas a LLM

### Error: "ImportError: cannot import name 'ChatGoogleGenerativeAI'"
**Causa**: Paquete no instalado
**Solución**: `pip install langchain-google-genai`

### Gemini devuelve respuestas incompletas
**Causa**: `max_output_tokens` muy bajo
**Solución**: Agregar en `create_llm()`:
```python
return ChatGoogleGenerativeAI(
    model=model,
    google_api_key=GOOGLE_API_KEY,
    temperature=0.2,
    max_output_tokens=8192,  # Aumenta el límite
    convert_system_message_to_human=True,
)
```

---

## 🎯 Próximos Pasos Recomendados

1. ✅ **Obtener API key de Gemini** (https://aistudio.google.com/app/apikey)
2. ✅ **Actualizar .env** con la key real
3. ✅ **Rebuild Docker** (`podman compose build --no-cache mach-api`)
4. ✅ **Restart services** (`podman compose up -d`)
5. ✅ **Ejecutar test end-to-end** (iniciar ciclo completo desde dashboard)
6. 📊 **Monitorear performance** (comparar latencia y calidad vs Groq)
7. 💰 **Activar billing** si planeas usar en producción (free tier es limitado)

---

## 📝 Resumen Ejecutivo

**Archivos modificados**: 3
- ✅ `config/settings.py` — API key + modelos
- ✅ `nodes/helper.py` — Inicialización LLM
- ✅ `.env` — Placeholder para API key

**Archivos NO modificados**:
- ✅ `requirements.txt` — Ya tenía langchain-google-genai
- ✅ Todos los nodos (prd, ux, arch, dev, qa, etc.) — Son agnósticos al proveedor
- ✅ `llm_invoke()` — Funciona igual con cualquier modelo LangChain

**Acción única requerida**: Configurar `GOOGLE_API_KEY` real en `.env`

La migración está **100% lista** — solo falta tu API key de Google.
