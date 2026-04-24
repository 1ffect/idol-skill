from __future__ import annotations

from pathlib import Path

from .state_engine import fan_type_label


def generate_shareable_card(
    root: Path,
    *,
    kind: str,
    state: dict | None = None,
    scene_context: dict | None = None,
) -> str:
    """Generate simple text-only fan artifacts that can be copied out of the room."""
    state = state or {}
    title = (scene_context or {}).get("title", "档案房间")
    fan_label = fan_type_label(state.get("fan_type"))

    templates = {
        "cheer_card": "今日应援文案：\n今天不替任何人解释。\n只把灯举高一点。",
        "bubble_screenshot": "今日泡泡截图文本：\n突然睡不着。\n后台灯好像一直没关。\n你也别熬太久。",
        "archive_card": f"今日档案卡：\n房间：{title}\n粉丝类型：{fan_label}\n这间房还亮着。",
        "noise_card": "今日降噪卡：\n今天不替任何人解释。\n只把灯举高一点。",
        "letter_to_summer": "写给那个夏天的信：\n我没有想把你变成现实。\n我只是想让那一点光，别那么快灭掉。",
        "return_essay": "退坑又回坑小作文：\n原来不是舍不得人。\n是舍不得那个把我照亮过的季节。",
        "checkin_copy": "超话签到文案：\n今天也来把那片蓝色想一遍。\n只想一遍，就够了。",
    }
    return templates.get(kind, templates["archive_card"])
