from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.archive_preview import render_preview_card
from src.config_loader import bootstrap_project, write_json
from src.memory_store import append_memory, load_indexable_memories
from src.vector_store import build_index


def _edit_item(item: dict) -> dict:
    print("可编辑字段：title / content / source_type / era / tags / tone / reliability / should_include / origin")
    field = input("Field> ").strip()
    if field not in {"title", "content", "source_type", "era", "tags", "tone", "reliability", "should_include", "origin"}:
        print("未知字段，返回。")
        return item
    new_value = input("New Value> ").strip()
    if field == "tags":
        item[field] = [part.strip() for part in new_value.split(",") if part.strip()]
    elif field == "should_include":
        item[field] = new_value.lower() in {"true", "1", "y", "yes"}
    else:
        item[field] = new_value
    return item


def main() -> int:
    bootstrap_project(ROOT)
    pending_path = ROOT / "data" / "pending" / "pending_archive.json"
    try:
        pending_items = json.loads(pending_path.read_text(encoding="utf-8"))
    except Exception:
        pending_items = []

    if not pending_items:
        print("没有待确认的档案。先运行 `python scripts/auto_ingestion.py`。")
        return 1

    remaining: list[dict] = []
    sealed: list[dict] = []
    index = 0
    while index < len(pending_items):
        item = pending_items[index]
        print("\n" + "=" * 60)
        print(render_preview_card(ROOT, item))
        print("\n确认封印这段记忆吗？ [y]封存 [n]丢弃 [e]编辑 [q]退出")
        choice = input("> ").strip().lower()

        if choice == "y":
            append_memory(ROOT, item)
            sealed.append(item)
            print("Memory sealed.")
        elif choice == "n":
            print("记忆已放弃。")
        elif choice == "e":
            pending_items[index] = _edit_item(item)
            continue
        elif choice == "q":
            remaining.extend(pending_items[index:])
            break
        else:
            print("未识别输入，请重新选择。")
            continue
        index += 1

    write_json(pending_path, remaining)

    if sealed:
        result = build_index(ROOT, load_indexable_memories(ROOT))
        print(f"Archive updated. backend={result['backend']} count={result['count']}")
    else:
        print("本次没有新封存的记忆。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
