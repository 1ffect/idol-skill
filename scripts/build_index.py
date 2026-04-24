from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config_loader import bootstrap_project
from src.memory_store import load_indexable_memories
from src.vector_store import build_index


def main() -> int:
    bootstrap_project(ROOT)
    memories = load_indexable_memories(ROOT)
    result = build_index(ROOT, memories)
    print(f"Index built. backend={result['backend']} count={result['count']}")
    if result.get("embedder_error"):
        print(f"Embedding fallback note: {result['embedder_error']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
