from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .config_loader import read_json, write_json

DEFAULT_STATE = {
    "fatigue": 0,
    "attachment": 0,
    "nostalgia": 0,
    "memory_glow": 0,
    "resonance": 0,
    "archive_stability": 100,
    "last_interaction": None,
    "interaction_count": 0,
    "last_augmentation_turn": -999,
    "unlocked_tiers": ["public_archive"],
    "fan_type": None,
    "stage_persona": "stage_alpha",
    "private_persona": "caregiver",
    "bubble_drop_count_today": 0,
    "bubble_drop_day": None,
    "last_bubble_drop_at": None,
    "last_degradation_notice_at": None,
}

DELTA_BY_MODE = {
    "tired_comfort": {"fatigue": 10, "resonance": 2, "archive_stability": 1},
    "nostalgia": {"nostalgia": 10, "memory_glow": 8, "resonance": 4, "archive_stability": -2},
    "daily_bubble": {"attachment": 3, "resonance": 3, "memory_glow": 2},
    "career_motivation": {"fatigue": 3, "attachment": 2, "resonance": 2, "memory_glow": 1},
    "scandal_noise": {"fatigue": 8, "nostalgia": 5, "resonance": 1, "archive_stability": -5},
}

FAN_TYPE_CHOICES = {
    "A": ("caregiver_fan", "想照顾 Ta：妈粉"),
    "B": ("career_fan", "想看 Ta 赢：事业粉"),
    "C": ("comfort_fan", "想被 Ta 哄：陪伴粉"),
    "D": ("stage_fan", "只爱舞台：舞台粉"),
    "E": ("archive_fan", "喜欢考古：记忆粉"),
}

FAN_TYPE_LABELS = {value[0]: value[1] for value in FAN_TYPE_CHOICES.values()}


def load_state(root: Path) -> dict:
    """Load state and backfill newly introduced state keys."""
    state = read_json(root / "data" / "user_state.json", default=DEFAULT_STATE)
    for key, value in DEFAULT_STATE.items():
        state.setdefault(key, value)
    return state


def _cap(value: int) -> int:
    return max(0, min(100, int(value)))


def _apply_decay(state: dict) -> dict:
    last_seen = state.get("last_interaction")
    if not last_seen:
        return state
    try:
        last_time = datetime.fromisoformat(last_seen)
    except ValueError:
        return state
    delta_days = max(0, (datetime.now() - last_time).days)
    if delta_days <= 0:
        return state

    for key in ["fatigue", "attachment", "nostalgia"]:
        state[key] = _cap(state.get(key, 0) - delta_days * 2)
    for key in ["memory_glow", "resonance"]:
        state[key] = _cap(state.get(key, 0) - delta_days)
    state["archive_stability"] = _cap(state.get("archive_stability", 100) - delta_days)
    return state


def save_state(root: Path, state: dict) -> dict:
    """Persist state after backfilling missing keys."""
    for key, value in DEFAULT_STATE.items():
        state.setdefault(key, value)
    write_json(root / "data" / "user_state.json", state)
    return state


def update_state(root: Path, mode: str, *, decay_enabled: bool = True) -> dict:
    """Apply per-turn emotion deltas and persist the updated user state."""
    state = load_state(root)
    if decay_enabled:
        state = _apply_decay(state)

    for key, delta in DELTA_BY_MODE.get(mode, {}).items():
        state[key] = _cap(state.get(key, 0) + delta)

    state["interaction_count"] = int(state.get("interaction_count", 0) + 1)
    state["last_interaction"] = datetime.now().isoformat(timespec="seconds")
    return save_state(root, state)


def register_augmentation(root: Path, current_turn: int) -> dict:
    """Persist the most recent augmentation turn to enforce spacing rules."""
    state = load_state(root)
    state["last_augmentation_turn"] = int(current_turn)
    return save_state(root, state)


def set_fan_type(root: Path, fan_type: str) -> dict:
    """Persist a normalized fan type on user state."""
    state = load_state(root)
    if fan_type in FAN_TYPE_LABELS:
        state["fan_type"] = fan_type
    return save_state(root, state)


def ensure_fan_type(root: Path, *, input_fn=input, output_fn=print) -> dict:
    """Prompt once for the user's fan type if it has not been set yet."""
    state = load_state(root)
    if state.get("fan_type") in FAN_TYPE_LABELS:
        return state

    output_fn("你是哪一种喜欢 Ta 的方式？")
    output_fn("A. 想照顾 Ta：妈粉")
    output_fn("B. 想看 Ta 赢：事业粉")
    output_fn("C. 想被 Ta 哄：陪伴粉")
    output_fn("D. 只爱舞台：舞台粉")
    output_fn("E. 喜欢考古：记忆粉")
    while True:
        try:
            choice = input_fn("选择 A-E（默认 E）: ").strip().upper() or "E"
        except EOFError:
            choice = "E"
        fan_type, _label = FAN_TYPE_CHOICES.get(choice, FAN_TYPE_CHOICES["E"])
        state["fan_type"] = fan_type
        save_state(root, state)
        output_fn(f"已记录：{FAN_TYPE_LABELS[fan_type]}")
        return state


def fan_type_label(fan_type: str | None) -> str:
    return FAN_TYPE_LABELS.get(fan_type or "", "喜欢考古：记忆粉")


def adjust_state(root: Path, **deltas: int) -> dict:
    """Apply arbitrary state deltas and save the result."""
    state = load_state(root)
    for key, delta in deltas.items():
        state[key] = _cap(state.get(key, 0) + delta)
    return save_state(root, state)


def state_hint(state: dict) -> str:
    hints: list[str] = []
    if state.get("fatigue", 0) >= 60:
        hints.append("fatigue high: reply shorter, softer, less instructive.")
    if state.get("attachment", 0) >= 50:
        hints.append("attachment high: sound more natural and familiar, but never cross boundaries.")
    if state.get("nostalgia", 0) >= 50:
        hints.append("nostalgia high: add a little memory-glow or safe augmentation detail if retrieval is weak.")
    if state.get("memory_glow", 0) >= 60:
        hints.append("memory glow high: archive fragments can feel brighter, but never confuse atmosphere with fact.")
    if state.get("archive_stability", 100) <= 40:
        hints.append("archive stability low: allow a soft degradation notice, but never create fear or false memory.")
    if not hints:
        hints.append("state balanced: keep a calm, restrained companion tone.")
    return "\n".join(f"- {hint}" for hint in hints)
