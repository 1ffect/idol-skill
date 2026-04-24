from __future__ import annotations

from pathlib import Path
from typing import Any

from .archive_unlock import allowed_memory_types
from .config_loader import read_json

ROOM_MENU = [
    ("today_bubble", "今日泡泡"),
    ("debut_night", "出道夜"),
    ("after_stage", "打歌后台"),
    ("late_night_bubble", "深夜泡泡"),
    ("noise_shield", "黑热搜隔离舱"),
    ("practice_room", "练习室地板"),
    ("letter_to_summer", "写给那个夏天的信"),
    ("if_timeline", "IF Timeline：如果那个夏天没有结束"),
]

DEFAULT_SCENE = {
    "scene_id": "today_bubble",
    "title": "今日泡泡",
    "opening_line": "今天这间房先亮一下。",
    "atmosphere_words": ["克制", "夏夜", "走廊灯"],
    "allowed_persona_types": ["alluring_teaser", "golden_retriever", "caregiver", "stage_alpha"],
    "allowed_memory_types": ["core", "dynamic", "emotional"],
    "banned_outputs": ["system_push", "guilt_trip", "real_chat_screenshot"],
    "ambient_profile": "backstage_aircon",
    "visual_card_profile": "late_night_hallway",
    "safety_notes": ["not_real_person", "app_open_only", "no_private_memory_fabrication"],
}

FAN_RECOMMENDATIONS = {
    "career_fan": ["after_stage", "noise_shield", "if_timeline"],
    "caregiver_fan": ["today_bubble", "late_night_bubble", "practice_room"],
    "comfort_fan": ["late_night_bubble", "today_bubble", "letter_to_summer"],
    "stage_fan": ["debut_night", "after_stage", "noise_shield"],
    "archive_fan": ["debut_night", "practice_room", "letter_to_summer"],
}


def load_scene(root: Path, scene_id: str) -> dict[str, Any]:
    path = root / "bias_room" / "scenes" / f"{scene_id}.json"
    scene = read_json(path, default=DEFAULT_SCENE)
    scene.setdefault("scene_id", scene_id)
    return scene


def room_menu() -> list[tuple[str, str]]:
    return ROOM_MENU.copy()


def scene_from_choice(choice: str) -> str | None:
    try:
        index = int(choice.strip()) - 1
    except ValueError:
        return None
    if 0 <= index < len(ROOM_MENU):
        return ROOM_MENU[index][0]
    return None


def recommended_scenes(state: dict[str, Any]) -> list[str]:
    return FAN_RECOMMENDATIONS.get(state.get("fan_type"), FAN_RECOMMENDATIONS["archive_fan"])


def render_scene_intro(scene: dict[str, Any], state: dict[str, Any]) -> str:
    lines = [
        f"## {scene.get('title', '房间')}",
        scene.get("opening_line", "这间房已经亮起来了。"),
        f"Atmosphere: {' / '.join(scene.get('atmosphere_words', [])) or 'quiet'}",
    ]
    if scene.get("scene_id") in recommended_scenes(state):
        lines.append("这间房今天正适合你。")
    return "\n".join(lines)


def allowed_scene_memory_types(scene: dict[str, Any], state: dict[str, Any]) -> list[str]:
    return allowed_memory_types(state, requested=scene.get("allowed_memory_types"))
