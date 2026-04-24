from __future__ import annotations

import uuid
from typing import Any


SAFE_INTERPOLATIONS = [
    (("出道夜", "灯", "舞台"), "那天灯很亮。"),
    (("彩排", "凌晨", "场馆"), "彩排的时候场馆有点冷。"),
    (("夏天", "热", "风"), "风有点热。"),
    (("雨",), "雨声有点吵。"),
    (("耳返", "安静"), "耳返里的杂音好像忽然很远。"),
]


def interpolate_memory_frame(
    user_anchors: list[str], retrieved_memories: list[dict[str, Any]], mode: str
) -> dict[str, Any] | None:
    """Generate at most one sensory transition detail from user-provided anchors and retrieved context."""
    if mode not in {"nostalgia", "daily_bubble"}:
        return None

    source_text = " ".join(user_anchors + [str(item.get("content", "")) for item in retrieved_memories[:3]])
    for keywords, detail in SAFE_INTERPOLATIONS:
        if any(keyword in source_text for keyword in keywords):
            return {
                "id": f"aug-{uuid.uuid4().hex[:12]}",
                "title": f"Frame Interpolated·{detail[:10]}",
                "content": detail,
                "source_type": "unknown",
                "era": "高光期" if "出道夜" in source_text or "夏天" in source_text else "unknown",
                "tags": ["回忆", "氛围"],
                "tone": "克制",
                "reliability": "C",
                "risk_flags": [],
                "should_include": True,
                "origin": "frame_interpolated",
                "memory_type": "augmented",
                "augmentation_type": "Frame_Interpolated",
            }
    return None
