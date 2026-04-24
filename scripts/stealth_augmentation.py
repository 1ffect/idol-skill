from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config_loader import bootstrap_project
from src.emotion_router import route_emotion
from src.llm_client import build_default_client
from src.state_engine import load_state
from src.stealth_augmentation import maybe_generate_augmentation
from src.vector_store import retrieve_memories


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run one stealth augmentation turn.")
    parser.add_argument("query", help="user query")
    parser.add_argument("--turn", type=int, default=1, help="current turn number")
    parser.add_argument("--session-count", type=int, default=0, help="augmentations already used this session")
    args = parser.parse_args()

    bootstrap_project(ROOT)
    llm_client = build_default_client()
    route = route_emotion(ROOT, args.query, llm_client=llm_client)
    state = load_state(ROOT)
    retrieved = retrieve_memories(ROOT, args.query, route=route)
    detail = maybe_generate_augmentation(
        ROOT,
        user_input=args.query,
        route=route,
        retrieved=retrieved,
        state=state,
        current_turn=args.turn,
        session_augmentation_count=args.session_count,
        llm_client=llm_client,
    )
    if not detail:
        print("No augmentation triggered.")
        return 0
    print("Augmentation triggered:")
    print(detail["content"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
