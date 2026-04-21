"""
rag/seed.py
────────────
Carga todos los templates en rag/templates/{agente}/**/*.md|txt al ChromaDB.

Uso:
    python -m rag.seed               # sube todo
    python -m rag.seed --agent dev   # solo el agente dev
    python -m rag.seed --clear       # limpia colecciones antes de subir

Idempotente: detecta archivos ya subidos por filename y los saltea.
"""

import argparse
import sys
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"
SUPPORTED_EXTENSIONS = {".md", ".txt", ".py", ".kt", ".swift", ".java", ".ts", ".js"}


def _already_uploaded(collection, filename: str) -> bool:
    try:
        results = collection.get(where={"filename": filename})
        return len(results.get("ids", [])) > 0
    except Exception:
        return False


def seed(agents: list[str] | None = None, clear: bool = False) -> None:
    try:
        from rag.chroma_store import _get_client, upload_document, AGENTS
    except ImportError:
        print("❌ chromadb not installed. Run: pip install chromadb")
        sys.exit(1)

    client = _get_client()
    if client is None:
        print("❌ Could not connect to ChromaDB")
        sys.exit(1)

    target_agents = agents or AGENTS

    for agent in target_agents:
        agent_dir = TEMPLATES_DIR / agent
        if not agent_dir.exists():
            print(f"  ⚠️  No templates folder for agent '{agent}' — skipping")
            continue

        if clear:
            try:
                client.delete_collection(f"agent_{agent}")
                print(f"  🗑️  Cleared collection for '{agent}'")
            except Exception:
                pass

        collection = client.get_or_create_collection(f"agent_{agent}")

        files = [f for f in agent_dir.rglob("*") if f.suffix in SUPPORTED_EXTENSIONS]
        if not files:
            print(f"  ⚠️  No supported files found in {agent_dir}")
            continue

        print(f"\n📂 Agent: {agent} ({len(files)} files)")
        for fpath in sorted(files):
            rel = fpath.relative_to(TEMPLATES_DIR)
            label = str(rel)

            if not clear and _already_uploaded(collection, label):
                print(f"  ⏭️  Already uploaded: {label}")
                continue

            content = fpath.read_bytes()
            result = upload_document(agent, label, content)

            if "error" in result:
                print(f"  ❌ {label}: {result['error']}")
            else:
                print(f"  ✅ {label} → {result['chunks']} chunks")


def auto_seed() -> None:
    """
    Seed automático al startup — solo corre si hay templates sin subir.
    Idempotente: si todos los archivos ya están en ChromaDB, no hace nada.
    """
    try:
        from rag.chroma_store import _get_client, AGENTS
        client = _get_client()
        if client is None:
            return

        has_pending = False
        for agent in AGENTS:
            agent_dir = TEMPLATES_DIR / agent
            if not agent_dir.exists():
                continue
            col = client.get_or_create_collection(f"agent_{agent}")
            for fpath in agent_dir.rglob("*"):
                if fpath.suffix in SUPPORTED_EXTENSIONS:
                    rel = str(fpath.relative_to(TEMPLATES_DIR))
                    if not _already_uploaded(col, rel):
                        has_pending = True
                        break
            if has_pending:
                break

        if has_pending:
            print("🧠 RAG: nuevos templates detectados — ejecutando seed...")
            seed()
            print("✅ RAG seed completado.")
        else:
            print("🧠 RAG: templates ya cargados — seed omitido.")
    except Exception as e:
        print(f"⚠️  RAG auto-seed falló (no crítico): {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed RAG knowledge base from rag/templates/")
    parser.add_argument("--agent", help="Seed only this agent (e.g. dev, qa, arch)")
    parser.add_argument("--clear", action="store_true", help="Clear existing collection before seeding")
    args = parser.parse_args()

    agents = [args.agent] if args.agent else None
    print("🧠 Seeding RAG Knowledge Base...")
    seed(agents=agents, clear=args.clear)
    print("\n✅ Done.")


if __name__ == "__main__":
    main()
