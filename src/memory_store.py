from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from .config_loader import append_jsonl, read_jsonl, read_text
from .ingestion import detect_era, detect_tags, detect_tone

LAYER_DEFAULTS = {
    "core": {"source_type": "unknown", "reliability": "B", "origin": "user_defined"},
    "emotional": {"source_type": "unknown", "reliability": "A", "origin": "user_defined"},
    "dynamic": {"source_type": "unknown", "reliability": "A", "origin": "user_provided"},
    "augmented": {"source_type": "web_augmented", "reliability": "C", "origin": "system_augmented"},
}


def _hash_text(*parts: str) -> str:
    return hashlib.md5("||".join(parts).encode("utf-8")).hexdigest()[:12]


def _build_memory_item(
    *,
    title: str,
    content: str,
    memory_type: str,
    source_type: str | None = None,
    reliability: str | None = None,
    origin: str | None = None,
    era: str | None = None,
    tags: list[str] | None = None,
    tone: str | None = None,
) -> dict[str, Any]:
    defaults = LAYER_DEFAULTS[memory_type]
    content = content.strip()
    source_type = source_type or defaults["source_type"]
    return {
        "id": f"{memory_type}-{_hash_text(title, content)}",
        "title": title.strip() or f"{memory_type.title()} Memory",
        "content": content,
        "source_type": source_type,
        "era": era or detect_era(content, source_type),
        "tags": tags or detect_tags(content),
        "tone": tone or detect_tone(content),
        "reliability": reliability or defaults["reliability"],
        "risk_flags": [],
        "should_include": True,
        "origin": origin or defaults["origin"],
        "memory_type": memory_type,
    }


def load_cleaned_memories(root: Path) -> list[dict[str, Any]]:
    """Return canonical user-confirmed dynamic memories from JSONL storage."""
    return read_jsonl(root / "data" / "cleaned" / "memories.jsonl")


def format_memory_markdown(item: dict[str, Any]) -> str:
    tags = ", ".join(item.get("tags", [])) or "无标签"
    risk_flags = ", ".join(item.get("risk_flags", [])) or "none"
    return (
        f"## {item.get('title', 'Untitled')}\n\n"
        f"- ID: {item.get('id', 'unknown')}\n"
        f"- Era: {item.get('era', 'unknown')}\n"
        f"- Source: {item.get('source_type', 'unknown')}\n"
        f"- Tone: {item.get('tone', 'unknown')}\n"
        f"- Reliability: {item.get('reliability', 'C')}\n"
        f"- Memory Type: {item.get('memory_type', 'dynamic')}\n"
        f"- Tags: {tags}\n"
        f"- Risk: {risk_flags}\n\n"
        f"{item.get('content', '').strip()}\n"
    )


def append_memory(root: Path, item: dict[str, Any]) -> None:
    """Append a user-confirmed dynamic memory to JSONL, markdown, and archive log."""
    cleaned_path = root / "data" / "cleaned" / "memories.jsonl"
    archive_log_path = root / "data" / "archive_log.jsonl"
    dynamic_md_path = root / "memories" / "dynamic_memory.md"

    item = {**item, "memory_type": "dynamic", "origin": item.get("origin") or "user_provided"}
    append_jsonl(cleaned_path, item)
    append_jsonl(
        archive_log_path,
        {
            "event": "sealed",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "memory_id": item.get("id"),
            "title": item.get("title"),
            "era": item.get("era"),
            "memory_type": "dynamic",
        },
    )
    with dynamic_md_path.open("a", encoding="utf-8") as handle:
        handle.write("\n" + format_memory_markdown(item) + "\n")


def append_augmented_memory(root: Path, item: dict[str, Any]) -> None:
    """Store a low-weight augmentation detail in augmented memory and archive log."""
    archive_log_path = root / "data" / "archive_log.jsonl"
    augmented_path = root / "memories" / "augmented_memory.md"
    item = {**item, "memory_type": "augmented", "reliability": item.get("reliability") or "C"}
    with augmented_path.open("a", encoding="utf-8") as handle:
        handle.write("\n" + format_memory_markdown(item) + "\n")
    append_jsonl(
        archive_log_path,
        {
            "event": "augmentation",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "memory_id": item.get("id"),
            "title": item.get("title"),
            "era": item.get("era"),
            "memory_type": "augmented",
            "origin": item.get("origin"),
        },
    )


def load_memory_text(path: Path, default: str = "") -> str:
    return read_text(path, default=default)


def _parse_markdown_bullets(text: str, memory_type: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        content = stripped[2:].strip().strip("“”\"")
        if not content or ":" in content[:24]:
            continue
        title = f"{memory_type.title()}·{content[:16]}"
        items.append(_build_memory_item(title=title, content=content, memory_type=memory_type))
    return items


def _parse_markdown_sections(text: str, memory_type: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    blocks = re.split(r"(?m)^##\s+", text)
    for block in blocks[1:]:
        lines = block.strip().splitlines()
        if not lines:
            continue
        title = lines[0].strip()
        metadata: dict[str, str] = {}
        content_lines: list[str] = []
        for line in lines[1:]:
            stripped = line.strip()
            if stripped.startswith("- ID:"):
                metadata["id"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- Era:"):
                metadata["era"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- Source:"):
                metadata["source_type"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- Tone:"):
                metadata["tone"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- Reliability:"):
                metadata["reliability"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- Tags:"):
                metadata["tags"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- ") and not content_lines:
                continue
            elif stripped:
                content_lines.append(stripped.strip("“”\""))
        content = " ".join(content_lines).strip()
        if not content:
            continue
        item = _build_memory_item(
            title=title,
            content=content,
            memory_type=memory_type,
            source_type=metadata.get("source_type"),
            reliability=metadata.get("reliability"),
            era=metadata.get("era"),
            tone=metadata.get("tone"),
            tags=[part.strip() for part in metadata.get("tags", "").split(",") if part.strip()] or None,
        )
        if metadata.get("id"):
            item["id"] = metadata["id"]
        items.append(item)
    return items


def load_indexable_memories(root: Path) -> list[dict[str, Any]]:
    """Load every memory layer used by retrieval with deduplication and memory_type labels."""
    collected: list[dict[str, Any]] = []

    for item in load_cleaned_memories(root):
        collected.append({**item, "memory_type": item.get("memory_type") or "dynamic"})

    layer_files = {
        "core": root / "memories" / "core_memory.md",
        "emotional": root / "memories" / "emotional_memory.md",
        "dynamic": root / "memories" / "dynamic_memory.md",
        "augmented": root / "memories" / "augmented_memory.md",
    }
    for memory_type, path in layer_files.items():
        text = read_text(path)
        if not text:
            continue
        if memory_type in {"core", "emotional"}:
            collected.extend(_parse_markdown_bullets(text, memory_type))
        else:
            collected.extend(_parse_markdown_sections(text, memory_type))

    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in collected:
        key = item.get("id") or _hash_text(item.get("title", ""), item.get("content", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def summarize_memory_layer(root: Path, memory_type: str, limit: int = 8) -> str:
    items = [item for item in load_indexable_memories(root) if item.get("memory_type") == memory_type]
    if not items:
        return f"暂无 {memory_type} 记忆。"
    chosen = items[-limit:] if memory_type in {"dynamic", "augmented"} else items[:limit]
    lines = []
    for item in chosen:
        lines.append(
            f"- {item.get('title', '未命名')} | {item.get('era', 'unknown')} | "
            f"{'/'.join(item.get('tags', [])) or '无标签'}"
        )
    return "\n".join(lines)


def summarize_dynamic_memory(root: Path, limit: int = 8) -> str:
    return summarize_memory_layer(root, "dynamic", limit=limit)


def summarize_augmented_memory(root: Path, limit: int = 6) -> str:
    return summarize_memory_layer(root, "augmented", limit=limit)


def summarize_emotional_memory(root: Path, limit: int = 6) -> str:
    return summarize_memory_layer(root, "emotional", limit=limit)


def top_memory_tags(root: Path, limit: int = 6) -> list[str]:
    memories = load_indexable_memories(root)
    counter: Counter[str] = Counter()
    for item in memories:
        counter.update(item.get("tags", []))
    return [tag for tag, _count in counter.most_common(limit)]


def serialize_retrieved_memories(items: list[dict[str, Any]]) -> str:
    if not items:
        return "暂无命中的封存记忆。"
    blocks = []
    for item in items:
        blocks.append(
            f"- {item.get('title', '未命名')} | score={item.get('score', 0):.3f} | "
            f"type={item.get('memory_type', 'dynamic')} | era={item.get('era', 'unknown')} | "
            f"tags={'/'.join(item.get('tags', [])) or '无'}\n"
            f"  {str(item.get('content', '')).strip()[:120]}"
        )
    return "\n".join(blocks)


def read_json_if_exists(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
