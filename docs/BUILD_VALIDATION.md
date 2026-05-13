# Garantía de Compilación y Preview - Sistema de Build Validation

Este sistema agrega validación automática de builds y auto-sanación al Dev Agent.

## 🎯 Características

### 1. Validación de Build
- Ejecuta `npm run build` en frontend
- Ejecuta tests o compilación en backend
- Captura errores de compilación

### 2. Bucle de Auto-Sanación
- Si el build falla, reinvoca al LLM con el error exacto
- Máximo 3 intentos de corrección
- Guarda cada intento en `outputs/DEVSPECS_healing_attempt_N.md`

### 3. Preview Server
- Inicia `npm run dev` en puerto 3001
- Expone URL de preview en el estado
- Disponible en el dashboard para revisión en vivo

## 🚀 Setup Requerido

### Paso 1: Instalar Node.js en el Contenedor

Actualiza `Dockerfile`:

```dockerfile
FROM python:3.12-slim

# Instalar Node.js 20.x
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Verificar instalación
RUN node --version && npm --version

# ... resto del Dockerfile
```

### Paso 2: Configurar Repos Locales

Opción A - Clonar al iniciar contenedor (recomendado):

```yaml
# docker-compose.yml
services:
  mach-api:
    volumes:
      - mach-repos:/tmp/repos
    environment:
      - ENABLE_BUILD_VALIDATION=true
    entrypoint: 
      - /bin/bash
      - -c
      - |
        # Clonar repos si no existen
        if [ ! -d "/tmp/repos/mach-backend-test-hackathon" ]; then
          git clone https://github.com/${GITHUB_USERNAME}/mach-backend-test-hackathon.git /tmp/repos/mach-backend-test-hackathon
        fi
        if [ ! -d "/tmp/repos/mach-frontend-test-hackathon" ]; then
          git clone https://github.com/${GITHUB_USERNAME}/mach-frontend-test-hackathon.git /tmp/repos/mach-frontend-test-hackathon
        fi
        # Iniciar servidor
        uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  mach-repos:
```

Opción B - Montar repos desde host:

```yaml
services:
  mach-api:
    volumes:
      - ~/projects/mach-backend-test-hackathon:/tmp/repos/mach-backend-test-hackathon
      - ~/projects/mach-frontend-test-hackathon:/tmp/repos/mach-frontend-test-hackathon
```

### Paso 3: Habilitar Validación

```bash
# En .env
ENABLE_BUILD_VALIDATION=true
```

## 📊 Flujo de Trabajo

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Dev Agent genera código                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Self-Healing Loop inicia                                │
│    ├─ Clona/actualiza repos                                │
│    ├─ Aplica archivos generados                            │
│    └─ Ejecuta npm run build                                │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
    Build OK?               Build FAIL?
         │                       │
         │                       ▼
         │          ┌─────────────────────────────┐
         │          │ Extrae error de stderr      │
         │          │ Reinvoca LLM con feedback   │
         │          │ "Tu código falló con: ..."  │
         │          └──────────┬──────────────────┘
         │                     │
         │                     ▼
         │              (Intento 2/3)
         │                     │
         │          ┌──────────┴──────────┐
         │          │                     │
         │          ▼                     ▼
         │     Build OK?            Build FAIL?
         │          │                     │
         │          │              (Intento 3/3)
         │          │                     │
         └──────────┴─────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Subir PRs a GitHub                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Iniciar Preview Server (npm run dev -p 3001)            │
│    └─ Exponer preview_url en estado                        │
└─────────────────────────────────────────────────────────────┘
```

## 🎨 Integración con Dashboard Vue

El endpoint `/api/cycle/status` ahora incluye `preview_url`.

Sugerencia para `frontend/src/views/RaceDashboard.vue`:

```vue
<template>
  <!-- ... código existente ... -->
  
  <!-- Botón de Preview -->
  <div v-if="store.status?.preview_url" class="preview-section">
    <a 
      :href="store.status.preview_url" 
      target="_blank"
      class="preview-button"
    >
      👁️ Ver Preview en Vivo
    </a>
    <p class="preview-note">
      El servidor de preview puede tardar unos segundos en arrancar
    </p>
  </div>
</template>

<style scoped>
.preview-button {
  display: inline-block;
  padding: 12px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  text-decoration: none;
  border-radius: 8px;
  font-weight: 600;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.preview-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
}

.preview-note {
  margin-top: 8px;
  font-size: 0.875rem;
  color: #6b7280;
}
</style>
```

## 🧪 Testing

### Test Manual Básico

```bash
# 1. Rebuilder contenedores con Node.js
podman compose build

# 2. Iniciar con validación habilitada
export ENABLE_BUILD_VALIDATION=true
podman compose up

# 3. Ejecutar un ciclo desde el dashboard
# 4. Monitorear logs:
podman logs -f mach-api

# Deberías ver:
# 🔄 [Self-Healing] Iniciando bucle de auto-sanación...
# 🔨 [Validando Frontend] ...
# ✅ [Self-Healing] Build validado exitosamente!
# 🚀 [Preview] Iniciando servidor de preview...
# 👁️  Preview disponible: http://localhost:3001
```

### Test de Auto-Sanación

Introduce un error deliberado en `dev_prompt.md` para forzar al agente a generar código roto:

```markdown
Genera código con un error de sintaxis deliberado para probar el auto-healing.
```

El sistema debería:
1. Detectar el error de build
2. Reinvocar al LLM con el error
3. Corregir automáticamente

## ⚠️ Limitaciones Actuales

1. **Procesos Huérfanos**: El preview server queda corriendo sin supervisión. Solución: usar PM2 o supervisor.

2. **Un Solo Preview**: Solo soporta un preview activo a la vez. Solución: usar puertos dinámicos.

3. **No Health Checks**: No verifica si el servidor realmente arrancó. Solución: agregar retry con curl.

4. **Cleanup Manual**: Los repos clonados y procesos quedan en /tmp. Solución: script de limpieza.

## 🔮 Mejoras Futuras

- [ ] Integración con Playwright para tests E2E automáticos
- [ ] Screenshots automáticos del preview
- [ ] Visual regression testing con Percy/Chromatic
- [ ] Preview en ambientes efímeros (Vercel/Netlify previews)
- [ ] Notificación Slack cuando el preview esté listo
