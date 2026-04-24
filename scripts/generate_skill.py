from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config_loader import bootstrap_project, load_app_config, read_text
from src.memory_store import load_indexable_memories, top_memory_tags


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "idol-skill"


def _profile(memories: list[dict]) -> dict:
    if not memories:
        return {
            "dominant_era": "高光期",
            "tone": "温柔 / 克制 / 认真",
            "tags": ["安慰", "舞台", "回忆"],
        }
    eras = Counter(item.get("era", "unknown") for item in memories)
    tones = Counter(item.get("tone", "认真") for item in memories)
    return {
        "dominant_era": eras.most_common(1)[0][0],
        "tone": " / ".join(tone for tone, _count in tones.most_common(3)),
        "tags": top_memory_tags(ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a standalone idol skill bundle.")
    parser.add_argument("--slug", default="idol_example", help="directory slug")
    args = parser.parse_args()

    bootstrap_project(ROOT)
    config = load_app_config(ROOT)
    slug = _slugify(args.slug)
    output_dir = ROOT / "skills" / slug
    output_dir.mkdir(parents=True, exist_ok=True)

    memories = load_indexable_memories(ROOT)
    profile = _profile(memories)
    corrections = read_text(ROOT / "memories" / "corrections.md", "# Corrections\n\n暂无。\n")
    persona_template = read_text(ROOT / "templates" / "persona_template.md")
    boundary_template = read_text(ROOT / "templates" / "boundary_template.md")
    persona_matrix_template = read_text(ROOT / "templates" / "persona_matrix.yaml")
    speaking_rhythm_template = read_text(ROOT / "templates" / "speaking_rhythm_template.yaml")

    persona = persona_template.format(
        skill_name=slug,
        dominant_era=profile["dominant_era"],
        tone=profile["tone"],
        tags=" / ".join(profile["tags"]) or "安慰 / 舞台 / 克制",
    )
    boundaries = boundary_template.format(skill_name=slug)
    memories_md = "# Memories\n\n" + "\n".join(
        f"- {item.get('title')}: {str(item.get('content', ''))[:120]}" for item in memories[-12:]
    )

    skill_md = f"""---
name: {slug}
description: Fan-memory idol companion skill for a fictionalized peak-era archive persona. Use archived memories, persona matrix, and corrections without impersonating a real person.
---

# Purpose

Generate a safe, idealized fan-memory companion persona for `{slug}`.

# Core Principle

- 不是本人，只是停留在高光时期的记忆人格。
- 优先保留公开内容、舞台感、克制感和安慰感。
- 用户记忆高于外部资料。augmentation 只能做氛围，不能定义人格。

# Persona Matrix

- Default stance: `{config.get('persona', {}).get('default_type', 'caregiver')}`
- Supported styles: `alluring_teaser`, `golden_retriever`, `caregiver`, `stage_alpha`

# Language Style

- Tone: {profile['tone']}
- Keep replies short, breathable, and concrete.
- No fandom slang, rotten internet memes, or oily possessive lines.

# Priority

- corrections.md is the highest-priority behavior layer.
- augmented_memory is background texture only and can never override user memory.

# Forbidden

- No real-person impersonation
- No voice cloning
- No privacy invasion
- No romance exclusivity
- No private-leak material
"""

    meta = {
        "slug": slug,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dominant_era": profile["dominant_era"],
        "memory_count": len(memories),
        "top_tags": profile["tags"],
        "default_persona_style": config.get("persona", {}).get("default_type", "caregiver"),
        "relationship_mode": config.get("generation", {}).get("relationship_mode", "fan_safe"),
    }

    (output_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
    (output_dir / "persona.md").write_text(persona, encoding="utf-8")
    (output_dir / "memories.md").write_text(memories_md, encoding="utf-8")
    (output_dir / "boundaries.md").write_text(boundaries, encoding="utf-8")
    (output_dir / "corrections.md").write_text(corrections, encoding="utf-8")
    (output_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "speaking_style.yaml").write_text(
        "language: zh\n"
        f"tone: \"{profile['tone']}\"\n"
        f"keywords: [{', '.join(profile['tags'])}]\n"
        "sentence_length: short\n"
        "avoid: [恋爱脑, 说教, AI味, 真人冒充]\n"
        "forbidden_slang: [塌房, 糊咖, 撕逼, 拉踩, yyds, 家人们, 丫头]\n",
        encoding="utf-8",
    )
    (output_dir / "speaking_rhythm.yaml").write_text(speaking_rhythm_template, encoding="utf-8")
    (output_dir / "persona_matrix.yaml").write_text(persona_matrix_template, encoding="utf-8")
    print(f"Skill generated: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
