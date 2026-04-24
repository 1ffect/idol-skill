from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .config_loader import load_app_config, read_json


def load_trigger_for_today(root: Path) -> dict | None:
    config = load_app_config(root)
    if not config.get("app", {}).get("trigger_enabled", True):
        return None

    today = datetime.now().strftime("%m-%d")
    anniversary = read_json(root / "triggers" / "anniversary.json", default={})
    milestones = read_json(root / "triggers" / "milestones.json", default={})
    return anniversary.get(today) or milestones.get(today)


def opening_line(root: Path) -> str:
    trigger = load_trigger_for_today(root)
    if not trigger:
        return "档案已开启。"
    return trigger.get("opening_line") or "档案已开启。"
