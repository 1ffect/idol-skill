from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config_loader import bootstrap_project, load_app_config
from src.emotion_router import route_emotion
from src.vector_store import retrieve_memories


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve related archived memories.")
    parser.add_argument("query", help="user query")
    parser.add_argument("--top-k", type=int, default=None)
    args = parser.parse_args()

    bootstrap_project(ROOT)
    config = load_app_config(ROOT)
    route = route_emotion(ROOT, args.query)
    items = retrieve_memories(
        ROOT,
        args.query,
        route=route,
        top_k=args.top_k or config.get("retrieval", {}).get("top_k", 6),
        min_score=config.get("retrieval", {}).get("min_score", 0.45),
    )
    if not items:
        print("没有检索到足够相关的记忆。")
        return 0
    for index, item in enumerate(items, start=1):
        print(
            f"{index}. {item.get('title')} | score={item.get('score')} | "
            f"type={item.get('memory_type', 'dynamic')} | era={item.get('era')} | "
            f"tags={'/'.join(item.get('tags', [])) or '无'}"
        )
        print(f"   {str(item.get('content', ''))[:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
