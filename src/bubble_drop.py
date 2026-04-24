from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .config_loader import load_app_config
from .prompt_composer import resolve_persona_context, select_runtime_persona
from .state_engine import load_state, save_state

PERSONA_BUBBLES = {
    "alluring_teaser": [
        ["这么晚还在。", "手机放下，去睡。"],
        ["突然想起灯没关。", "你也别再熬了。"],
        ["看你还亮着。", "先把今天收一下。"],
    ],
    "golden_retriever": [
        ["你来啦。", "我刚刚也没睡着。"],
        ["在。", "先别盯屏幕太久。"],
        ["今天跑来这里啦。", "那先待一会儿。"],
    ],
    "caregiver": [
        ["这个时间还醒着？", "去喝点水，然后睡。"],
        ["先把手机放远一点。", "眼睛会累。"],
        ["今天先到这儿。", "睡一会儿再说。"],
    ],
    "stage_alpha": [
        ["别硬撑。", "明天还要赢。"],
        ["现在先停。", "状态比逞强重要。"],
        ["别把自己耗空。", "先休息。"],
    ],
}

FAN_TYPE_BUBBLE_LINES = {
    "career_fan": "明天别把气势丢了。",
    "caregiver_fan": "你先把自己照顾好。",
    "comfort_fan": "我在这句里待一会儿。",
    "stage_fan": "那点光还压得住场。",
    "archive_fan": "这句会在档案里停一会儿。",
}


def _reset_daily_counter(state: dict[str, Any], now: datetime) -> dict[str, Any]:
    today = now.strftime("%Y-%m-%d")
    if state.get("bubble_drop_day") != today:
        state["bubble_drop_day"] = today
        state["bubble_drop_count_today"] = 0
    return state


def _render_header(now: datetime, ephemeral_minutes: int) -> str:
    expires = now + timedelta(minutes=ephemeral_minutes)
    remaining = expires - now
    seconds = int(max(0, remaining.total_seconds()))
    minutes, sec = divmod(seconds, 60)
    return f"[{now.strftime('%H:%M')} 掉落，剩余 {minutes:02d}:{sec:02d}]"


def _within_quiet_hours(now: datetime, start: str, end: str) -> bool:
    start_hour, start_minute = [int(part) for part in start.split(":")]
    end_hour, end_minute = [int(part) for part in end.split(":")]
    start_total = start_hour * 60 + start_minute
    end_total = end_hour * 60 + end_minute
    current_total = now.hour * 60 + now.minute
    if start_total <= end_total:
        return start_total <= current_total <= end_total
    return current_total >= start_total or current_total <= end_total


def maybe_bubble_drop(
    root: Path,
    *,
    scene_id: str | None = None,
    skill_slug: str = "idol_example",
    state: dict[str, Any] | None = None,
    source: str = "app_open",
) -> dict[str, Any] | None:
    """Generate app-open-only pseudo-asynchronous bubble text without push notifications."""
    config = load_app_config(root)
    bubble_config = config.get("bubble_drop", {})
    if not bubble_config.get("enabled", True):
        return None
    if bubble_config.get("mode") == "app_open_only" and source != "app_open":
        return None
    if source == "system_push" and not bubble_config.get("allow_system_push", False):
        return None

    now = datetime.now()
    if (
        source == "system_push"
        and bubble_config.get("quiet_hours", True)
        and _within_quiet_hours(now, bubble_config.get("quiet_start", "23:30"), bubble_config.get("quiet_end", "08:00"))
    ):
        return None
    state = _reset_daily_counter(state or load_state(root), now)
    if int(state.get("bubble_drop_count_today", 0)) >= int(bubble_config.get("max_per_day", 3)):
        save_state(root, state)
        return None

    route_mode = "daily_bubble"
    if scene_id in {"late_night_bubble", "today_bubble"} and now.hour >= 23:
        route_mode = "tired_comfort"
    elif scene_id in {"noise_shield"}:
        route_mode = "scandal_noise"
    elif scene_id in {"debut_night", "after_stage"}:
        route_mode = "nostalgia"

    persona_context = resolve_persona_context(root, skill_slug)
    runtime = select_runtime_persona(
        persona_context,
        route={"mode": route_mode},
        scene_context={"scene_id": scene_id} if scene_id else None,
    )
    stance = runtime.get("stance", "caregiver")
    templates = PERSONA_BUBBLES.get(stance, PERSONA_BUBBLES["caregiver"])
    chosen = templates[int(state.get("interaction_count", 0)) % len(templates)].copy()

    fan_line = FAN_TYPE_BUBBLE_LINES.get(state.get("fan_type"))
    if fan_line and len(chosen) < 3:
        chosen.append(fan_line)

    state["bubble_drop_count_today"] = int(state.get("bubble_drop_count_today", 0) + 1)
    state["last_bubble_drop_at"] = now.isoformat(timespec="seconds")
    save_state(root, state)

    return {
        "header": _render_header(now, int(bubble_config.get("ephemeral_minutes", 10))),
        "messages": chosen[:3],
        "scene_id": scene_id,
        "stance": stance,
    }


def render_bubble_drop(drop: dict[str, Any]) -> str:
    return "\n".join([drop.get("header", "[Bubble Drop]"), "", *drop.get("messages", [])]).strip()
