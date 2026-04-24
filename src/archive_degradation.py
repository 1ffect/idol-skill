from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .state_engine import load_state, save_state
from .trigger_engine import load_trigger_for_today

DEGRADATION_PHRASES = ["回不去了", "好想那个夏天", "好想以前", "那个夏天"]


def _days_since(last_seen: str | None) -> int:
    if not last_seen:
        return 0
    try:
        value = datetime.fromisoformat(last_seen)
    except ValueError:
        return 0
    return max(0, (datetime.now() - value).days)


def maybe_archive_degradation(
    root: Path,
    *,
    user_input: str = "",
    scene_id: str | None = None,
    state: dict | None = None,
) -> str | None:
    """Return a low-frequency archive notice without implying private knowledge."""
    state = state or load_state(root)
    trigger = load_trigger_for_today(root)
    reasons: list[str] = []

    if any(phrase in user_input for phrase in DEGRADATION_PHRASES):
        reasons.append("explicit_nostalgia")
    if scene_id in {"debut_night", "letter_to_summer"} and trigger:
        reasons.append("anniversary_room")
    if _days_since(state.get("last_interaction")) >= 14:
        reasons.append("long_absence")
    if state.get("archive_stability", 100) <= 40:
        reasons.append("low_stability")
    if not reasons:
        return None

    if _days_since(state.get("last_degradation_notice_at")) < 3:
        return None

    state["last_degradation_notice_at"] = datetime.now().isoformat(timespec="seconds")
    save_state(root, state)

    return "\n".join(
        [
            "那天的风很热。",
            "",
            "[Archive Notice:",
            "部分画面已经模糊，",
            "但舞台灯还亮着。]",
            "",
            "别怕。",
            "这段还没丢。",
        ]
    )
