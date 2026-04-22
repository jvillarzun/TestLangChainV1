"""
nodes/dev/build_validator.py
────────────────────────────
Sistema de validación y auto-sanación de builds para el Dev Agent.

REQUISITOS PREVIOS:
1. Repositorios clonados en: /tmp/repos/{repo_name}/
2. Node.js y npm instalados en el contenedor
3. Dependencias npm instaladas en cada repo

Para configurar en Docker:
- Agregar Node.js al Dockerfile
- Montar volumen con repos clonados
- O clonar repos en startup del contenedor
"""

import subprocess
import os
from pathlib import Path
from typing import Dict, Tuple


def validate_frontend_build(repo_path: str) -> Tuple[bool, str]:
    """
    Valida que el frontend compile correctamente.
    
    Args:
        repo_path: Ruta al repositorio frontend clonado
        
    Returns:
        (success: bool, error_message: str)
    """
    print(f"\n🔨 [Build Validator] Validando build de frontend en: {repo_path}")
    
    repo_dir = Path(repo_path)
    if not repo_dir.exists():
        error = f"Repositorio no encontrado en {repo_path}"
        print(f"   ❌ {error}")
        return False, error
    
    # Verificar que exista package.json
    if not (repo_dir / "package.json").exists():
        error = "package.json no encontrado"
        print(f"   ❌ {error}")
        return False, error
    
    try:
        # Intentar build de Next.js/React
        print(f"   🔧 Ejecutando: npm run build")
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutos máximo
        )
        
        if result.returncode == 0:
            print(f"   ✅ Build exitoso!")
            return True, ""
        else:
            error = f"Build falló con código {result.returncode}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            print(f"   ❌ Build falló")
            print(f"   Error preview: {result.stderr[:500]}...")
            return False, error
            
    except subprocess.TimeoutExpired:
        error = "Build timeout después de 5 minutos"
        print(f"   ❌ {error}")
        return False, error
    except FileNotFoundError:
        error = "npm no encontrado - Node.js no instalado en el contenedor"
        print(f"   ⚠️  {error}")
        return False, error
    except Exception as e:
        error = f"Error inesperado: {str(e)}"
        print(f"   ❌ {error}")
        return False, error


def validate_backend_build(repo_path: str) -> Tuple[bool, str]:
    """
    Valida que el backend pase tests básicos o compile.
    
    Args:
        repo_path: Ruta al repositorio backend clonado
        
    Returns:
        (success: bool, error_message: str)
    """
    print(f"\n🔨 [Build Validator] Validando backend en: {repo_path}")
    
    repo_dir = Path(repo_path)
    if not repo_dir.exists():
        error = f"Repositorio no encontrado en {repo_path}"
        print(f"   ❌ {error}")
        return False, error
    
    # Detectar tipo de proyecto
    is_node = (repo_dir / "package.json").exists()
    is_python = (repo_dir / "requirements.txt").exists() or (repo_dir / "pyproject.toml").exists()
    
    try:
        if is_node:
            print(f"   🔧 Proyecto Node.js detectado - ejecutando: npm test")
            result = subprocess.run(
                ["npm", "test", "--", "--passWithNoTests"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=180,
            )
        elif is_python:
            print(f"   🔧 Proyecto Python detectado - ejecutando: python -m py_compile")
            # Compilar todos los archivos .py
            py_files = list(repo_dir.rglob("*.py"))
            if not py_files:
                return True, ""
            
            result = subprocess.run(
                ["python", "-m", "py_compile"] + [str(f) for f in py_files[:10]],  # máximo 10 archivos
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )
        else:
            print(f"   ⚠️  Tipo de proyecto desconocido - saltando validación")
            return True, ""
        
        if result.returncode == 0:
            print(f"   ✅ Validación exitosa!")
            return True, ""
        else:
            error = f"Validación falló\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            print(f"   ❌ Validación falló")
            return False, error
            
    except subprocess.TimeoutExpired:
        error = "Validación timeout"
        print(f"   ❌ {error}")
        return False, error
    except Exception as e:
        error = f"Error inesperado: {str(e)}"
        print(f"   ❌ {error}")
        return False, error


def start_preview_server(repo_path: str, port: int = 3001) -> Tuple[bool, str]:
    """
    Inicia servidor de preview en segundo plano.
    
    NOTA: Esta implementación es básica. En producción necesitarías:
    - Gestión de procesos (supervisor, pm2)
    - Limpieza de procesos viejos
    - Health checks
    
    Args:
        repo_path: Ruta al repo frontend
        port: Puerto para el servidor
        
    Returns:
        (success: bool, preview_url: str)
    """
    print(f"\n🚀 [Preview] Iniciando servidor de preview en puerto {port}...")
    
    repo_dir = Path(repo_path)
    if not repo_dir.exists():
        print(f"   ❌ Repositorio no encontrado")
        return False, ""
    
    try:
        # Iniciar Next.js dev server en background
        # NOTA: Este proceso quedará huérfano - en producción usar pm2 o similar
        process = subprocess.Popen(
            ["npm", "run", "dev", "--", "-p", str(port)],
            cwd=repo_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        
        preview_url = f"http://localhost:{port}"
        print(f"   ✅ Servidor iniciado (PID: {process.pid})")
        print(f"   🔗 Preview URL: {preview_url}")
        
        # Guardar PID para poder matar el proceso después (opcional)
        pid_file = Path("/tmp") / f"preview_{port}.pid"
        pid_file.write_text(str(process.pid))
        
        return True, preview_url
        
    except FileNotFoundError:
        print(f"   ⚠️  npm no encontrado")
        return False, ""
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False, ""


def setup_repo(repo_name: str, branch: str, files: list[dict]) -> str:
    """
    Clona repo, hace checkout del branch, y aplica los cambios.
    
    Args:
        repo_name: Nombre del repo (sin owner)
        branch: Rama a usar
        files: Lista de archivos generados
        
    Returns:
        Ruta al repo clonado
    """
    from config.settings import GITHUB_USERNAME, GITHUB_TOKEN
    
    repo_path = f"/tmp/repos/{repo_name}"
    repo_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{repo_name}.git"
    
    print(f"\n📥 [Setup] Preparando repo {repo_name}...")
    
    try:
        # Si el repo ya existe, hacer pull
        if Path(repo_path).exists():
            print(f"   🔄 Repo existente - actualizando...")
            subprocess.run(["git", "fetch", "--all"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(["git", "checkout", branch], cwd=repo_path, capture_output=True)
        else:
            # Clonar repo
            print(f"   📥 Clonando repo...")
            subprocess.run(
                ["git", "clone", repo_url, repo_path],
                check=True,
                capture_output=True,
                timeout=120,
            )
            subprocess.run(["git", "checkout", "-b", branch], cwd=repo_path, check=True, capture_output=True)
        
        # Aplicar cambios localmente
        print(f"   📝 Aplicando {len(files)} archivos...")
        for file_info in files:
            file_path = Path(repo_path) / file_info["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file_info["content"], encoding="utf-8")
        
        # Instalar dependencias si es necesario
        if (Path(repo_path) / "package.json").exists():
            print(f"   📦 Instalando dependencias npm...")
            subprocess.run(
                ["npm", "install"],
                cwd=repo_path,
                capture_output=True,
                timeout=300,
            )
        
        print(f"   ✅ Repo preparado en {repo_path}")
        return repo_path
        
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error en git: {e.stderr if e.stderr else e}")
        return ""
    except subprocess.TimeoutExpired:
        print(f"   ❌ Timeout preparando repo")
        return ""
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return ""
