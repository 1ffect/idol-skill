from __future__ import annotations

from pathlib import Path
from typing import Any

from .config_loader import read_json
from .state_engine import fan_type_label, load_state, save_state

DEFAULT_ARCHIVE_TIERS = {
    "tiers": [
        {
            "id": "public_archive",
            "name": "公开档案",
            "unlock_condition": "default",
            "available_memory_types": ["core", "dynamic"],
            "required_resonance": 0,
            "required_memory_glow": 0,
            "simulation": False,
        },
        {
            "id": "emotional_archive",
            "name": "情绪档案",
            "unlock_condition": "resonance >= 30",
            "available_memory_types": ["emotional"],
            "required_resonance": 30,
            "required_memory_glow": 0,
            "simulation": False,
        },
        {
            "id": "parallel_fragments",
            "name": "平行碎片",
            "unlock_condition": "memory_glow >= 60",
            "available_memory_types": ["augmented"],
            "required_resonance": 0,
            "required_memory_glow": 60,
            "simulation": True,
        },
        {
            "id": "if_timeline",
            "name": "如果那个夏天没有结束",
            "unlock_condition": "resonance >= 80 or unlock_if_timeline",
            "available_memory_types": ["core", "dynamic", "emotional", "augmented"],
            "required_resonance": 80,
            "required_memory_glow": 0,
            "manual_token": "unlock_if_timeline",
            "simulation": True,
        },
    ]
}

FAN_TYPE_NOTICE_LINES = {
    "caregiver_fan": "不是更靠近了，是这间房更稳了一点。",
    "career_fan": "灯没有变成奖杯，但它确实又亮了一点。",
    "comfort_fan": "今天这间房更暖了一点。",
    "stage_fan": "舞台边缘的光又清楚了一点。",
    "archive_fan": "一些原本模糊的地方，慢慢有了轮廓。",
}


def load_archive_tiers(root: Path) -> dict[str, Any]:
    return read_json(root / "bias_room" / "archive_tiers.json", default=DEFAULT_ARCHIVE_TIERS)


def _tier_unlocked(state: dict[str, Any], tier: dict[str, Any], manual_token: str | None) -> bool:
    if tier.get("id") == "public_archive":
        return True
    if tier.get("manual_token") and manual_token == tier.get("manual_token"):
        return True
    required_resonance = int(tier.get("required_resonance", 0))
    required_memory_glow = int(tier.get("required_memory_glow", 0))
    matched = True
    if required_resonance > 0:
        matched = matched and state.get("resonance", 0) >= required_resonance
    if required_memory_glow > 0:
        matched = matched and state.get("memory_glow", 0) >= required_memory_glow
    return matched and (required_resonance > 0 or required_memory_glow > 0)


def render_unlock_notice(tier: dict[str, Any], fan_type: str | None) -> str:
    extra = FAN_TYPE_NOTICE_LINES.get(fan_type or "", "这间房间更亮了一点。")
    lines = [
        "Archive Notice:",
        "一段新的记忆开始解冻。",
        "这间房间更亮了一点。",
        f"已解锁：{tier.get('name', tier.get('id', '新档案'))}",
        extra,
    ]
    if tier.get("simulation"):
        lines.append("这不代表现实，只代表一块被允许发光的平行碎片。")
    return "\n".join(lines)


def sync_archive_unlocks(
    root: Path,
    *,
    state: dict[str, Any] | None = None,
    manual_token: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Unlock archive tiers based on resonance, memory glow, or explicit manual token."""
    state = state or load_state(root)
    tiers = load_archive_tiers(root).get("tiers", [])
    unlocked = list(state.get("unlocked_tiers", [])) or ["public_archive"]
    notices: list[str] = []

    for tier in tiers:
        tier_id = tier.get("id")
        if not tier_id or tier_id in unlocked:
            continue
        if _tier_unlocked(state, tier, manual_token):
            unlocked.append(tier_id)
            notices.append(render_unlock_notice(tier, state.get("fan_type")))

    state["unlocked_tiers"] = unlocked
    save_state(root, state)
    return state, notices


def has_tier(state: dict[str, Any], tier_id: str) -> bool:
    return tier_id in set(state.get("unlocked_tiers", []))


def allowed_memory_types(state: dict[str, Any], requested: list[str] | None = None) -> list[str]:
    """Resolve room-available memory types using unlocked archive tiers."""
    types: list[str] = []
    if has_tier(state, "public_archive"):
        types.extend(["core", "dynamic"])
    if has_tier(state, "emotional_archive"):
        types.append("emotional")
    if has_tier(state, "parallel_fragments"):
        types.append("augmented")
    if has_tier(state, "if_timeline"):
        for item in ["core", "dynamic", "emotional", "augmented"]:
            if item not in types:
                types.append(item)
    if requested:
        requested_set = set(requested)
        types = [item for item in types if item in requested_set]
    seen: set[str] = set()
    deduped: list[str] = []
    for item in types:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped or ["core", "dynamic"]


def archive_status_text(state: dict[str, Any]) -> str:
    return (
        f"Fan Type: {fan_type_label(state.get('fan_type'))}\n"
        f"Memory Glow: {state.get('memory_glow', 0)}\n"
        f"Resonance: {state.get('resonance', 0)}\n"
        f"Archive Stability: {state.get('archive_stability', 100)}\n"
        f"Unlocked: {', '.join(state.get('unlocked_tiers', ['public_archive']))}"
    )
