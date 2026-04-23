import json
import re
import os

from state.cycle_state import CycleState
from nodes.helper import _get_last_feedback, load_prompt, save_output, llm_invoke, create_llm
from tools.jira_tools import create_task
from tools.slack_tools import notify_team
from tools.github_tools import create_branch_and_push, open_pull_request
from config.settings import MODEL_DEV, REPO_BE_NAME, REPO_FE_NAME

# Flag para habilitar validación de build (requiere setup adicional)
ENABLE_BUILD_VALIDATION = os.environ.get("ENABLE_BUILD_VALIDATION", "false").lower() == "true"
MAX_HEALING_ATTEMPTS = 3

def _parse_generated_files(content: str) -> list[dict]:
    """
    Extrae archivos usando el NUEVO FORMATO de bloques Markdown.
    Busca patrones: ## FILE: {repo}/{path} seguido de ```{lang} ... ```
    Retorna lista de dicts: [{"repo": ..., "path": ..., "content": ...}]
    """
    print(f"\n🔍 [DEV Parser] Parseando archivos con NUEVO formato Markdown...")
    print(f"   Longitud del contenido: {len(content)} chars")
    
    files = []
    # Patrón: ## FILE: backend/src/file.js\n```javascript\n...código...\n```
    pattern = r"##\s*FILE:\s*([^/\s]+)/([^\n]+)\s*```[a-z]*\s*\n(.*?)\n```"
    matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        repo = match.group(1).strip()
        path = match.group(2).strip()
        file_content = match.group(3)
        
        print(f"   ✅ Encontrado: {repo}/{path} ({len(file_content)} chars)")
        
        files.append({
            "repo": repo,
            "path": path,
            "content": file_content,
        })
    
    if not files:
        print(f"⚠️  [DEV Parser] NO se encontraron archivos con formato Markdown")
        print(f"   Intentando fallback a formato JSON antiguo...")
        # Fallback al formato JSON antiguo por compatibilidad
        match = re.search(r"```json\s*(\{.*?\"files\".*?\})\s*```", content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                files = data.get("files", [])
                print(f"   ✅ Fallback JSON exitoso: {len(files)} archivos")
            except json.JSONDecodeError as e:
                print(f"   ❌ Fallback JSON falló: {e}")
                return []
        else:
            print(f"   ❌ Tampoco se encontró formato JSON - retornando lista vacía")
            return []
    
    print(f"\n✅ [DEV Parser] Total archivos parseados: {len(files)}")
    for i, f in enumerate(files, 1):
        print(f"   {i}. {f['repo']}/{f['path']} ({len(f['content'])} chars)")
    
    return files


def _push_files_and_open_pr(
    repo_name: str,
    branch: str,
    files: list[dict],
    challenge_name: str,
    github_plan: str,
) -> str | None:
    """Sube los archivos a la rama y abre PR. Retorna URL del PR."""
    print(f"\n🚀 [DEV] _push_files_and_open_pr()")
    print(f"    Repo: {repo_name}")
    print(f"    Rama: {branch}")
    print(f"    Archivos: {len(files)}")
    print(f"    Challenge: {challenge_name}")
    
    if not files:
        print(f"⚠️  [DEV] Lista de archivos vacía - abortando")
        return None
    
    changes = [{"path": f.get("path", ""), "content": f.get("content", "")} for f in files]
    print(f"📦 [DEV] Preparados {len(changes)} cambios para commit")
    
    print(f"\n📤 [DEV] Llamando a create_branch_and_push()...")
    commit_sha = create_branch_and_push(
        repo_name=repo_name,
        branch_name=branch,
        changes=changes,
        commit_message=f"feat({challenge_name}): ADLC auto-generated code",
    )
    
    if not commit_sha:
        print(f"❌ [DEV] create_branch_and_push FALLÓ - no se pudo hacer push a {repo_name}")
        return None
    
    print(f"✅ [DEV] Push exitoso! Commit SHA: {commit_sha[:8]}...")

    pr_body = (
        f"## ADLC Auto-generated PR\n\n"
        f"**Challenge:** {challenge_name}\n\n"
        f"### Engineering Plan\n```json\n{github_plan}\n```\n\n"
        f"### Archivos modificados\n"
        + "\n".join(f"- `{f.get('path', 'unknown')}`" for f in files)
    )
    
    print(f"\n🔗 [DEV] Llamando a open_pull_request()...")
    pr_url = open_pull_request(
        repo_name=repo_name,
        branch_name=branch,
        title=f"feat({challenge_name}): ADLC implementation",
        body=pr_body,
    )
    
    if pr_url:
        print(f"✅ [DEV] PR creado exitosamente: {pr_url}")
    else:
        print(f"❌ [DEV] open_pull_request FALLÓ - no se pudo abrir PR")
    
    return pr_url


def _self_healing_loop(
    state: CycleState,
    initial_content: str,
    system_prompt: str,
) -> tuple[str, list[dict]]:
    """
    Bucle de auto-sanación: valida build y reintenta con feedback si falla.
    También detecta cuando el LLM ignora el formato de salida.
    
    Returns:
        (final_content: str, generated_files: list[dict])
    """
    if not ENABLE_BUILD_VALIDATION:
        print("\n⚠️  [Self-Healing] Validación de build deshabilitada (ENABLE_BUILD_VALIDATION=false)")
        return initial_content, _parse_generated_files(initial_content)
    
    print(f"\n🔄 [Self-Healing] Iniciando bucle de auto-sanación (máx {MAX_HEALING_ATTEMPTS} intentos)")
    
    from nodes.dev.build_validator import setup_repo, validate_frontend_build, validate_backend_build
    
    branch = f"feat/adlc-{state['thread_id'][:8]}"
    current_content = initial_content
    
    for attempt in range(1, MAX_HEALING_ATTEMPTS + 1):
        print(f"\n🔄 [Intento {attempt}/{MAX_HEALING_ATTEMPTS}]")
        
        # Parsear archivos del contenido actual
        generated_files = _parse_generated_files(current_content)
        
        # ── Auto-Sanación del Parser (Formato Incorrecto) ────────────────────
        if not generated_files and len(current_content) > 100:
            print("\n⚠️  [Self-Healing] Parser no encontró archivos pero hay contenido")
            print("   🔄 El LLM probablemente ignoró el formato - forzando reintento...")
            
            if attempt < MAX_HEALING_ATTEMPTS:
                error_feedback = """## 🚨 ERROR CRÍTICO DE FORMATO

**Tu respuesta anterior NO SIGUIÓ el formato requerido.**

El parser NO pudo extraer ningún archivo de tu output. Esto significa que:
- NO usaste el formato de bloques Markdown especificado
- O envolviste el código en formato incorrecto
- O agregaste texto extra fuera de los bloques

**FORMATO OBLIGATORIO (cada archivo):**
```
## FILE: repo/ruta/archivo.ext
```extension
código aquí
```
```

**EJEMPLO CORRECTO:**
```
## FILE: backend/src/api.js
```javascript
const express = require('express');
module.exports = express.Router();
```
```

**REGLAS CRÍTICAS:**
1. Header exacto: `## FILE: repo/path`
2. Bloque de código con extensión correcta
3. Código completo dentro del bloque
4. NO agregues explicaciones fuera de los bloques
5. NO uses formato JSON

**AHORA GENERA NUEVAMENTE TODOS LOS ARCHIVOS USANDO EL FORMATO CORRECTO.**
"""
                healing_prompt = system_prompt + "\n\n" + error_feedback
                
                try:
                    print(f"   🔄 Reintentando con instrucciones de formato...")
                    llm = create_llm(MODEL_DEV)
                    from langchain_core.messages import SystemMessage, HumanMessage
                    response = llm.invoke([
                        SystemMessage(content=healing_prompt),
                        HumanMessage(content="Genera TODOS los archivos usando el formato Markdown especificado (## FILE: repo/path)."),
                    ])
                    current_content = response.content
                    save_output(f"DEVSPECS_format_healing_{attempt}.md", current_content)
                    print(f"   💾 Guardado intento de corrección de formato en outputs/")
                    continue  # Volver al inicio del loop para re-parsear
                except Exception as e:
                    print(f"   ❌ Error invocando LLM para corrección de formato: {e}")
                    return current_content, []
            else:
                print(f"\n⚠️  [Self-Healing] Máximo de intentos - parser sigue sin encontrar archivos")
                return current_content, []
        
        if not generated_files:
            print("   ⚠️  No se encontraron archivos generados - abortando auto-sanación")
            return current_content, generated_files
        
        # Frontend-Only: Solo procesar archivos del frontend
        fe_files = [f for f in generated_files if (
            f.get("repo") == "frontend" or 
            f.get("repo") == "fe" or 
            REPO_FE_NAME in f.get("repo", "")
        )]
        
        # ── Validar Frontend ─────────────────────────────────────────────
        fe_valid = True
        fe_error = ""
        if fe_files:
            print(f"\n🔨 [Validando Frontend] {len(fe_files)} archivos...")
            fe_repo_path = setup_repo(REPO_FE_NAME, branch, fe_files)
            if fe_repo_path:
                fe_valid, fe_error = validate_frontend_build(fe_repo_path)
            else:
                print("   ⚠️  No se pudo preparar repo frontend - saltando validación")
        
        # ── Resultado ────────────────────────────────────────────────────
        if fe_valid:
            print(f"\n✅ [Self-Healing] Build validado exitosamente en intento {attempt}!")
            return current_content, generated_files
        
        # ── Si falló, reintentar con feedback ────────────────────────────
        if attempt < MAX_HEALING_ATTEMPTS:
            print(f"\n❌ [Self-Healing] Build falló - reintentando con feedback del error...")
            
            # Construir mensaje de error
            error_feedback = "## 🚨 ERRORES DE COMPILACIÓN\n\n"
            error_feedback += "Tu código generó los siguientes errores al compilar:\n\n"
            error_feedback += f"### Frontend Error:\n```\n{fe_error[:1000]}\n```\n\n"
            
            error_feedback += "\n**INSTRUCCIONES:**\n"
            error_feedback += "1. Analiza el error cuidadosamente\n"
            error_feedback += "2. Identifica la causa raíz (syntax error, import faltante, tipo incorrecto, etc.)\n"
            error_feedback += "3. Corrige TODOS los archivos afectados\n"
            error_feedback += "4. Devuelve el código COMPLETO corregido\n"
            error_feedback += "5. NO agregues comentarios tipo 'aquí va el código' - ESCRIBE el código completo\n"
            
            # Reinvocar LLM con el error
            healing_prompt = system_prompt + "\n\n" + error_feedback
            
            try:
                print(f"   🔄 Invocando LLM para auto-sanación...")
                llm = create_llm(MODEL_DEV)
                from langchain_core.messages import SystemMessage, HumanMessage
                response = llm.invoke([
                    SystemMessage(content=healing_prompt),
                    HumanMessage(content="Corrige los errores de compilación y genera nuevamente TODOS los archivos completos."),
                ])
                current_content = response.content
                save_output(f"DEVSPECS_healing_attempt_{attempt}.md", current_content)
                print(f"   💾 Guardado intento {attempt} en outputs/")
            except Exception as e:
                print(f"   ❌ Error invocando LLM: {e}")
                return current_content, generated_files
        else:
            print(f"\n⚠️  [Self-Healing] Máximo de intentos alcanzado - usando última versión")
            print(f"   ⚠️  El código puede tener errores de compilación")
            return current_content, generated_files
    
    return current_content, generated_files


def run_dev_node(state: CycleState) -> dict:
    """Nodo DEV — genera código real y abre PRs en BE y FE repos."""
    print("\n💻 DEV-AGENT: Generando DEVSPECS.md + código para PRs...")

    feedback = _get_last_feedback(state, "dev")
    if feedback:
        print(f"   💬 Re-ejecutando con feedback: {feedback}")

    github_plan = state.get("github_plan") or ""

    # ── Leer contexto del repo Frontend (FRONTEND-ONLY) ──────────────────────
    print("\n📖 [DEV] Leyendo código actual del repositorio Frontend...")
    from tools.github_tools import get_repo_context
    try:
        fe_ctx = get_repo_context(REPO_FE_NAME)
        print(f"   ✅ Frontend: {len(fe_ctx.get('tree', []))} archivos")
        
        # Formatear contexto para el LLM
        fe_context = "Árbol: " + str(len(fe_ctx.get('tree', []))) + " archivos\nArchivos clave:\n"
        for path, content in fe_ctx.get('files', {}).items():
            fe_context += "\n--- " + path + " ---\n" + content[:2000] + "...\n"
    except Exception as e:
        print(f"   ⚠️  No se pudo leer repo (GitHub no disponible): {e}")
        fe_context = "No disponible - GitHub offline"

    try:
        from rag.rag_helper import get_rag_context
        _rag = get_rag_context("dev", f"{state['challenge_name']} {state['challenge_description']}")
    except Exception:
        _rag = None

    system_prompt = load_prompt(
        "dev",
        challenge_name=state["challenge_name"],
        challenge_type=state["challenge_type"],
        challenge_description=state["challenge_description"],
        prd_content=state.get("prd_content") or "",
        arch_content=state.get("arch_content") or "",
        ux_content=state.get("ux_content") or "",
        github_plan=github_plan,
        repo_fe_name=REPO_FE_NAME,
        feedback=feedback or "Sin feedback previo.",
    )
    
    # Inyectar contexto de código actual para evitar sobreescritura
    system_prompt += "\n\n## 📖 Código Actual del Repositorio Frontend (para MODIFY)\n\n"
    system_prompt += "### Frontend — " + REPO_FE_NAME + "\n" + fe_context + "\n\n"
    system_prompt += "**IMPORTANTE**: Cuando modifiques un archivo existente, DEBES incluir TODO el código actual en tu respuesta, fusionando tus cambios con el contenido original mostrado arriba.\n\n"
    
    if _rag:
        system_prompt += "\n\n## Contexto de Knowledge Base (DEV):\n" + _rag
        print(f"   📚 RAG: {len(_rag)} chars de contexto inyectados")
    
    print(f"   📦 Contexto total del prompt: {len(system_prompt)} chars")

    try:
        dev_content = llm_invoke(
            model=MODEL_DEV,
            system_prompt=system_prompt,
            user_message="Genera el DEVSPECS.md completo y el código de TODOS los archivos usando el formato de bloques Markdown especificado (## FILE: repo/path). Recuerda: CERO placeholders, CERO comentarios vacíos, código COMPLETO y funcional.",
            stub_content="# DEVSPECS.md stub — TEST_MODE activo",
        )
    except Exception as e:
        print(f"[DEV-AGENT] Error LLM: {e}")
        notify_team(f"❌ DEV-AGENT falló en ciclo `{state['thread_id'][:8]}`: {e}", state["thread_id"])
        return {"error_phase": "dev", "error_message": str(e), "dev_content": None, "dev_pr_url": None, "dev_pr_urls": []}

    output_path = save_output("DEVSPECS.md", dev_content)
    print(f"   💾 Guardado en {output_path}")

    # ── Auto-sanación con validación de build ─────────────────────────────────
    dev_content, generated_files = _self_healing_loop(state, dev_content, system_prompt)
    
    # Actualizar archivo con versión final
    if dev_content != save_output("DEVSPECS.md", dev_content):
        save_output("DEVSPECS.md", dev_content)

    # ── Extraer archivos generados y subir PRs ────────────────────────────────
    branch = f"feat/adlc-{state['thread_id'][:8]}"
    pr_urls: list[str] = []
    preview_url: str | None = None
    
    # Frontend-Only: Solo procesar archivos del frontend
    fe_files: list[dict] = []

    if generated_files:
        # Filtro robusto: acepta "frontend", "fe", o el nombre completo del repo
        fe_files = [f for f in generated_files if (
            f.get("repo") == "frontend" or 
            f.get("repo") == "fe" or 
            REPO_FE_NAME in f.get("repo", "")
        )]
        
        challenge_name = state["challenge_name"]
        
        print(f"\n📦 [Frontend-Only Architecture]")
        print(f"   Frontend: {len(fe_files)} archivos")

        if fe_files:
            print(f"\n📤 [Subiendo Frontend] {len(fe_files)} archivos a {REPO_FE_NAME}...")
            pr = _push_files_and_open_pr(REPO_FE_NAME, branch, fe_files, challenge_name, github_plan)
            if pr:
                pr_urls.append(pr)
                print(f"   ✅ PR frontend creado: {pr}")
            else:
                print(f"   ⚠️  No se pudo crear PR frontend")
        else:
            print(f"   ⚠️  No se encontraron archivos de frontend - verificar formato del LLM")
    else:
        print("\n⚠️  [Sin archivos generados] No se abrieron PRs")

    # ── Iniciar servidor de preview si está habilitado ────────────────────────
    if ENABLE_BUILD_VALIDATION and fe_files:
        print(f"\n🚀 [Preview Server] Intentando iniciar servidor de preview...")
        from nodes.dev.build_validator import setup_repo, start_preview_server
        
        fe_repo_path = setup_repo(REPO_FE_NAME, branch, fe_files)
        if fe_repo_path:
            success, url = start_preview_server(fe_repo_path, port=3001)
            if success:
                preview_url = url
                print(f"   ✅ Preview disponible: {preview_url}")
            else:
                print(f"   ⚠️  No se pudo iniciar servidor de preview")
        else:
            print(f"   ⚠️  No se pudo preparar repo para preview")
    elif fe_files:
        print(f"\n⚠️  [Preview Server] Validación de build deshabilitada - no se inicia preview")
    
    # ── Crear Jira Task ──────────────────────────────────────────────────────
    task_key = create_task(
        phase="dev",
        summary=f"{state['challenge_name']} — Implementation",
        description=dev_content[:2000],
    )

    notify_team(f"✅ DEV-AGENT completado para `{state['challenge_name']}`.\n\nPRs: {', '.join(pr_urls) if pr_urls else 'Ninguno'}", state["thread_id"])

    print(f"\n{'='*80}")
    print(f"📋 [DEV-AGENT] RESUMEN FINAL")
    print(f"{'='*80}")
    print(f"   ✅ DEVSPECS.md generado ({len(dev_content)} chars)")
    print(f"   🎫 Jira Task: {task_key or 'N/A'}")
    print(f"   🔗 PRs abiertos: {len(pr_urls)}")
    if pr_urls:
        for i, url in enumerate(pr_urls, 1):
            print(f"      {i}. {url}")
    else:
        print(f"   ⚠️  NO SE ABRIERON PRs")
    if preview_url:
        print(f"   👁️  Preview disponible: {preview_url}")
    print(f"{'='*80}\n")

    return {
        "dev_content":     dev_content,
        "dev_pr_url":      pr_urls[0] if pr_urls else None,
        "dev_pr_urls":     pr_urls,
        "preview_url":     preview_url,
        "error_phase":     None,
        "error_message":   None,
        "jira_story_keys": [task_key] if task_key else [],
    }

