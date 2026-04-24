from __future__ import annotations

from pathlib import Path
from typing import Any

from .config_loader import read_json

DEFAULT_AMBIENT_MANIFEST = {
    "profiles": [
        {
            "id": "summer_night_cicadas",
            "title": "夏夜蝉鸣",
            "description": "空气有点黏，远处是夏夜很轻的蝉声。",
            "safe": True,
            "no_human_voice_clone": True,
        },
        {
            "id": "rain_on_window",
            "title": "雨敲窗沿",
            "description": "雨点打在玻璃上，很慢，很密。",
            "safe": True,
            "no_human_voice_clone": True,
        },
        {
            "id": "backstage_aircon",
            "title": "后台空调声",
            "description": "很轻的风声和远处模糊人声。",
            "safe": True,
            "no_human_voice_clone": True,
        },
        {
            "id": "practice_room_floor",
            "title": "练习室地板反光",
            "description": "空房间里有鞋底摩擦地板的回声。",
            "safe": True,
            "no_human_voice_clone": True,
        },
        {
            "id": "empty_venue_after_show",
            "title": "散场后的空场馆",
            "description": "座位都暗下去了，只剩一点低频回响。",
            "safe": True,
            "no_human_voice_clone": True,
        },
        {
            "id": "distant_crowd_muffle",
            "title": "远处模糊人群声",
            "description": "像隔着墙传来的模糊欢呼。",
            "safe": True,
            "no_human_voice_clone": True,
        },
        {
            "id": "stage_low_frequency",
            "title": "舞台低频残响",
            "description": "低频很轻，像场馆还没完全安静下来。",
            "safe": True,
            "no_human_voice_clone": True,
        },
    ]
}

DEFAULT_VISUAL_CARDS = {
    "debut_night_blue_light": {
        "title": "Debut Night",
        "style": "lo-fi polaroid, blurred blue stage lights, no identifiable face",
        "visual": "一张模糊的蓝色光斑卡片。",
        "caption": "那天太亮了。\n亮到后来什么都记不清。",
    },
    "after_stage_empty_seats": {
        "title": "After Stage",
        "style": "empty venue seats, dim aisle lights, no identifiable face",
        "visual": "一张空场馆座位的低饱和卡片。",
        "caption": "散场以后，灯还没全灭。\n好像有人还留在那一刻。",
    },
    "practice_room_reflection": {
        "title": "Practice Room",
        "style": "practice room floor reflection, fluorescent light, no human face",
        "visual": "一张练习室地板反光的卡片。",
        "caption": "地板很冷。\n但光一直稳稳地压在那里。",
    },
    "noise_shield_rain_window": {
        "title": "Noise Shield",
        "style": "rainy window, blurred blue-grey lights, no face",
        "visual": "一张雨夜窗户和模糊路灯的卡片。",
        "caption": "把外面的声音挡住。\n这里只留一点光。",
    },
    "late_night_hallway": {
        "title": "Late Night Bubble",
        "style": "dim hallway light, soft grain, no identifiable face",
        "visual": "一张走廊夜灯泛黄的卡片。",
        "caption": "夜很深。\n但这间房还没完全睡着。",
    },
}


def load_ambient_manifest(root: Path) -> dict[str, Any]:
    return read_json(root / "bias_room" / "ambient" / "ambient_manifest.json", default=DEFAULT_AMBIENT_MANIFEST)


def load_visual_cards(root: Path) -> dict[str, Any]:
    return read_json(root / "bias_room" / "visual_cards" / "visual_card_templates.json", default=DEFAULT_VISUAL_CARDS)


def _ambient_profile(root: Path, ambient_id: str) -> dict[str, Any]:
    profiles = load_ambient_manifest(root).get("profiles", [])
    for profile in profiles:
        if profile.get("id") == ambient_id:
            return profile
    return profiles[0] if profiles else {}


def draw_ambient_blind_box(root: Path, scene: dict[str, Any], *, fan_type: str | None = None) -> dict[str, str]:
    """Return text-only ambient and abstract visual outputs for a scene."""
    ambient_id = scene.get("ambient_profile") or "backstage_aircon"
    visual_id = scene.get("visual_card_profile") or "debut_night_blue_light"
    ambient = _ambient_profile(root, ambient_id)
    visual_cards = load_visual_cards(root)
    visual = visual_cards.get(visual_id, next(iter(visual_cards.values()), {}))

    ambient_text = "\n".join(
        [
            f"[Ambient: {ambient.get('id', ambient_id)}]",
            f"{ambient.get('title', '环境白噪音')}很轻。",
            ambient.get("description", "这里只保存环境，不保存真人声线。"),
        ]
    )

    extra_caption = ""
    if fan_type == "stage_fan" and scene.get("scene_id") in {"debut_night", "after_stage"}:
        extra_caption = "\n那点低频像舞台还没完全退场。"
    elif fan_type == "archive_fan":
        extra_caption = "\n像一张被反复翻看的旧卡片。"

    visual_text = "\n".join(
        [
            f"[Visual Blind Box: {visual.get('title', scene.get('title', 'Scene'))}]",
            visual.get("visual", "一张模糊灯光的卡片。"),
            f"“{visual.get('caption', '这里只保存一点光。')}{extra_caption}”",
        ]
    )

    return {"ambient_text": ambient_text, "visual_text": visual_text}
