from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config_loader import bootstrap_project, read_text
from src.ingestion import auto_ingest
from src.llm_client import build_default_client


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean raw idol-memory text into a pending archive.")
    parser.add_argument("input_path", nargs="?", default="data/raw/input.txt", help="path to raw text input")
    args = parser.parse_args()

    bootstrap_project(ROOT)
    input_path = ROOT / args.input_path if not Path(args.input_path).is_absolute() else Path(args.input_path)
    raw_text = read_text(input_path).strip()
    if not raw_text:
        print(f"`{input_path}` 还是空的，先把公开文本或主观记忆贴进去。")
        return 1

    llm_client = build_default_client()
    if not llm_client.available():
        print("LLM unavailable. Using rule-based ingestion fallback.")
        print("如需启用 OpenAI-compatible API，请设置 OPENAI_API_KEY 或 IDOL_SKILL_API_KEY。")
    records, preview_path = auto_ingest(ROOT, raw_text, llm_client=llm_client)
    print("Pending archive saved.")
    print(f"Records: {len(records)}")
    print(f"Preview: {preview_path}")
    print("请运行 `python scripts/confirm_ingestion.py` 进行确认封存。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
