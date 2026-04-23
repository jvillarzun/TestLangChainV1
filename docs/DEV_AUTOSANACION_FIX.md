# Fix del Sistema de Auto-Sanación — Resumen de Cambios

## 🐛 Problemas Resueltos

### 1. UnboundLocalError en `fe_files` (Línea 345)
**Causa**: Las variables `fe_files` y `be_files` solo se definían dentro del bloque `if generated_files:`, pero luego se usaban fuera (en el check de preview).

**Solución**: Inicialización temprana antes del bloque condicional:
```python
# Inicializar listas de archivos (evita UnboundLocalError más adelante)
be_files: list[dict] = []
fe_files: list[dict] = []

if generated_files:
    be_files = [f for f in generated_files if f.get("repo") == "backend"]
    fe_files = [f for f in generated_files if f.get("repo") == "frontend"]
```

### 2. Parser Fallando Silenciosamente
**Causa**: El LLM ignoraba el formato de bloques Markdown y el parser devolvía lista vacía sin reintentar.

**Solución**: Auto-sanación del parser integrada en `_self_healing_loop()`:
- Detecta cuando `generated_files` está vacío PERO `len(content) > 100`
- Esto indica que el LLM respondió pero no siguió el formato
- Reintenta con un mensaje de error específico sobre formato
- Guarda intentos en `DEVSPECS_format_healing_{attempt}.md`

**Código agregado**:
```python
# ── Auto-Sanación del Parser (Formato Incorrecto) ────────────────────────────────
if not generated_files and len(current_content) > 100:
    print("\n⚠️  [Self-Healing] Parser no encontró archivos pero hay contenido")
    print("   🔄 El LLM probablemente ignoró el formato - forzando reintento...")
    
    if attempt < MAX_HEALING_ATTEMPTS:
        error_feedback = """## 🚨 ERROR CRÍTICO DE FORMATO
        
**Tu respuesta anterior NO SIGUIÓ el formato requerido.**

El parser NO pudo extraer ningún archivo de tu output...
[Instrucciones detalladas del formato correcto]
"""
        # Reinvoca LLM con feedback de formato
```

### 3. Prompt Reforzado con Regla Crítica
**Archivo**: `nodes/dev/dev_prompt.md`

Agregada sección destacada al inicio de "Parte 2 — CÓDIGO GENERADO":

```markdown
🚨 **REGLA CRÍTICA DE FORMATO — SEGUIR EXACTAMENTE O EL PARSER FALLARÁ**

**Cada archivo DEBE seguir este formato de bloques Markdown:**
...
[Instrucciones explícitas con ejemplo]

**Si no sigues este formato exacto, el parser NO podrá extraer los archivos y el ciclo fallará.**
```

## 📊 Flujo de Auto-Sanación Actualizado

```
Dev Agent genera output
         ↓
Parser intenta extraer archivos
         ↓
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
Archivos OK?   Lista vacía + contenido largo?
    │                 │
    │                 ▼
    │         🔄 ERROR DE FORMATO
    │         Reintentar con instrucciones
    │         (máx 3 veces)
    │                 │
    └────────┬────────┘
             ▼
     Archivos extraídos
             ↓
    Validar build (npm run build)
             ↓
    ┌────────┴────────┐
    ▼                 ▼
Build OK?      Build FAIL?
    │                 │
    │                 ▼
    │         🔄 ERROR DE COMPILACIÓN
    │         Reintentar con error del build
    │                 │
    └────────┬────────┘
             ▼
      PRs creados
             ↓
    Preview server iniciado
```

## 🧪 Testing

Para probar las correcciones:

```bash
# 1. Reiniciar contenedores con código actualizado
podman compose restart mach-api

# 2. Iniciar un ciclo desde el dashboard

# 3. Monitorear logs para ver auto-sanación en acción
podman logs -f mach-api | grep -E "Self-Healing|Parser|formato"
```

**Outputs esperados si el LLM ignora el formato:**
```
🔍 [DEV Parser] Parseando archivos con NUEVO formato Markdown...
⚠️  [DEV Parser] NO se encontraron archivos con formato Markdown
❌ Tampoco se encontró formato JSON - retornando lista vacía

🔄 [Self-Healing] Iniciando bucle de auto-sanación...
⚠️  [Self-Healing] Parser no encontró archivos pero hay contenido
🔄 El LLM probablemente ignoró el formato - forzando reintento...
🔄 Reintentando con instrucciones de formato...
💾 Guardado intento de corrección de formato en outputs/

[Segundo intento - parser vuelve a intentar]
✅ [DEV Parser] Total archivos parseados: 5
```

## ✅ Validaciones Agregadas

1. **Inicialización defensiva**: Variables siempre definidas antes de uso
2. **Detección de formato incorrecto**: Parser vacío + contenido = formato malo
3. **Feedback específico**: Mensaje de error detalla exactamente qué formato usar
4. **Logging mejorado**: Cada paso del self-healing se registra
5. **Persistencia de intentos**: Cada intento de corrección se guarda en `outputs/`

## 🎯 Beneficios

- ✅ **Zero crashes**: No más `UnboundLocalError`
- ✅ **Formato autocorregible**: LLM aprende el formato en el segundo intento
- ✅ **Debugging más fácil**: Archivos intermedios guardados
- ✅ **Instrucciones más claras**: Prompt reforzado previene errores
- ✅ **Resiliencia**: Sistema continúa incluso si el parser falla inicialmente
