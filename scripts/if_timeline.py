from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config_loader import bootstrap_project
from src.if_timeline import generate_if_timeline
from src.llm_client import build_default_client
from src.state_engine import ensure_fan_type, load_state


def main() -> int:
    parser = argparse.ArgumentParser(description="Enter the IF Timeline simulation room.")
    parser.add_argument("prompt", nargs="?", help="parallel timeline prompt")
    parser.add_argument("--skill", default="idol_example", help="skill slug under skills/")
    args = parser.parse_args()

    bootstrap_project(ROOT)
    ensure_fan_type(ROOT)
    llm_client = build_default_client()
    prompt = args.prompt or input("Parallel Prompt: ").strip() or "写一段平行采访片段"
    result = generate_if_timeline(
        ROOT,
        user_input=prompt,
        skill_slug=args.skill,
        state=load_state(ROOT),
        llm_client=llm_client,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
