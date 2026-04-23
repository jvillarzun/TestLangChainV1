# Garantía de Compilación y Preview — Quick Start

Este archivo resume cómo activar el sistema de build validation.

## ⚡ 1-Minuto Setup

```bash
# 1. Agregar Node.js al Dockerfile (antes de COPY)
RUN apt-get update && apt-get install -y curl git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 2. Habilitar en .env
ENABLE_BUILD_VALIDATION=true

# 3. Rebuild y restart
podman compose build
podman compose up
```

## 🧪 Test Manual

```bash
# Ejecutar un ciclo desde el dashboard
# Monitorear logs:
podman logs -f mach-api | grep "Self-Healing"

# Deberías ver:
# 🔄 [Self-Healing] Iniciando bucle...
# 🔨 [Validando Frontend]...
# ✅ Build validado exitosamente!
# 🚀 [Preview] Preview disponible: http://localhost:3001
```

## 📖 Docs Completas

Ver [BUILD_VALIDATION.md](./BUILD_VALIDATION.md) para:
- Setup de repos locales
- Configuración de Docker Compose
- Integración con dashboard Vue.js
- Troubleshooting

## ⚙️ Flags de Control

| Variable | Default | Descripción |
|----------|---------|-------------|
| `ENABLE_BUILD_VALIDATION` | `false` | Activa validación + auto-sanación |
| `TEST_MODE` | `false` | Skip LLM calls |
| `MOCK_EARLY_AGENTS` | `false` | Usa mocks para PRD/UX |

## 🎯 Qué Hace

1. **Validación**: Ejecuta `npm run build` después de generar código
2. **Auto-Sanación**: Si falla, reinvoca LLM con error (máx 3 intentos)
3. **Preview Server**: Inicia `npm run dev -p 3001` si build pasa
4. **Estado Persistido**: `preview_url` disponible en `/api/cycle/status`

## ⚠️ Requisitos

- Node.js 18+ en el contenedor
- Repos clonados en `/tmp/repos/` o montados desde host
- Dependencias npm instaladas (`npm install`)

Sin estos, el sistema funciona con advertencias pero no validará.
