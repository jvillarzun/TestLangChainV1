# Mocks — Agentes ADLC

Esta carpeta contiene documentos estáticos para simular la salida de agentes PRD y UX sin gastar tokens en pruebas del Dev Agent.

## Uso

1. **Activar mocks:**
   ```bash
   export MOCK_EARLY_AGENTS=true
   ```

2. **Ejecutar ciclo ADLC:**
   ```bash
   python main.py
   ```

3. **Logs esperados:**
   ```
   📋 PRD-AGENT: Generando PRDSPECS.md...
   ⚡ [PRD] Usando mock estático. Saltando LLM.
      💾 Mock guardado en outputs/PRDSPECS.md
      ✅ PRDSPECS.md mock (5420 chars)

   🎨 UX-AGENT: Generando UXSPECS.md...
   ⚡ [UX] Usando mock estático. Saltando LLM.
      💾 Mock guardado en outputs/UXSPECS.md
      ✅ UXSPECS.md mock (6850 chars)
   ```

## Archivos

| Archivo | Descripción | Usado por |
|---------|-------------|-----------|
| `mock_prdspecs.md` | Product Requirements simulado | `nodes/prd/prd_node.py` |
| `mock_uxspecs.md` | UX Specifications simulado | `nodes/ux/ux_node.py` |

## Personalización

Edita los archivos `.md` en esta carpeta para cambiar el contenido mock según tu caso de prueba.

## Desactivar Mocks

```bash
unset MOCK_EARLY_AGENTS
# O en .env
MOCK_EARLY_AGENTS=false
```

---

**Ventajas de este approach:**
- ⚡ Ahorra tokens de Groq en fases tempranas
- 🚀 Acelera pruebas iterativas del Dev Agent
- 🎯 Permite probar el ciclo completo sin esperar generación LLM
- 📝 Contenido predecible para debugging

**Cuándo usarlo:**
- ✅ Pruebas del Dev/QA/Infra Agents
- ✅ Testing del flujo HITL
- ✅ Debugging del grafo LangGraph
- ❌ NO usar en producción o demos finales
