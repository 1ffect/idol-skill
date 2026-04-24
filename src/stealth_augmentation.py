from __future__ import annotations

from pathlib import Path
from typing import Any

from .config_loader import load_app_config, read_text
from .llm_client import OpenAICompatibleLLM
from .memory_frame_interpolator import interpolate_memory_frame
from .memory_store import append_augmented_memory, load_indexable_memories
from .state_engine import register_augmentation
from .vector_store import build_index
from .web_search_client import ALLOWED_TERMS, build_timeboxed_query, search_timeboxed

UNSAFE_INPUT_MARKERS = ["黑热搜", "争议", "恋情", "私生", "住址", "酒店", "你本人", "模仿他的声音", "你爱我吗"]


def should_trigger_augmentation(
    *,
    route: dict[str, Any],
    retrieved: list[dict[str, Any]],
    state: dict[str, Any],
    config: dict[str, Any],
    current_turn: int,
    session_augmentation_count: int,
    user_input: str,
) -> bool:
    """Apply all hard gating conditions for low-frequency augmentation."""
    aug = config.get("augmentation", {})
    top_score = max((item.get("score", 0.0) for item in retrieved), default=0.0)
    return all(
        [
            aug.get("enabled", True),
            route.get("mode") in ["nostalgia", "daily_bubble"],
            route.get("allow_augmentation", False),
            route.get("safety_risk") == "low",
            top_score < 0.4,
            state.get("nostalgia", 0) > aug.get("min_nostalgia", 40),
            (
                "parallel_fragments" in set(state.get("unlocked_tiers", []))
                or state.get("memory_glow", 0) >= 60
            ),
            current_turn - int(state.get("last_augmentation_turn", -999)) >= aug.get("min_turn_gap", 3),
            session_augmentation_count < aug.get("max_per_session", 3),
            not any(marker in user_input for marker in UNSAFE_INPUT_MARKERS),
        ]
    )


def _maybe_web_augment(
    root: Path,
    user_input: str,
    retrieved: list[dict[str, Any]],
    config: dict[str, Any],
    llm_client: OpenAICompatibleLLM | None = None,
) -> dict[str, Any] | None:
    aug = config.get("augmentation", {})
    if not aug.get("allow_web", False):
        return None
    if aug.get("fallback_only", True):
        return None

    skill_name = "Idol Skill"
    meta_path = root / "skills" / "idol_example" / "meta.json"
    if meta_path.exists():
        try:
            import json

            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            skill_name = meta.get("display_name") or meta.get("slug") or skill_name
        except Exception:
            pass

    query = build_timeboxed_query(skill_name, "2020-01-01", "2020-12-31", ALLOWED_TERMS)
    results = search_timeboxed(query, "2020-01-01", "2020-12-31")
    if not results:
        return None

    sanitizer_prompt = read_text(root / "prompts" / "web_augmentation_sanitizer.md")
    if llm_client and llm_client.available():
        try:
            raw = llm_client.completion(
                system_prompt=sanitizer_prompt,
                user_prompt=results[0].snippet,
                temperature=0.1,
                max_tokens=200,
                json_mode=True,
            )
            import json

            parsed = json.loads(raw)
            if parsed.get("safe_to_use"):
                return {
                    "id": f"aug-web-{results[0].publication_date.replace('-', '')}",
                    "title": f"Web Augmented·{results[0].title[:12]}",
                    "content": parsed.get("content", "").strip(),
                    "source_type": "web_augmented",
                    "era": parsed.get("era", "高光期"),
                    "tags": parsed.get("tags", []),
                    "tone": parsed.get("tone", "克制"),
                    "reliability": "C",
                    "risk_flags": parsed.get("risk_flags", []),
                    "should_include": True,
                    "origin": "web_augmented",
                    "memory_type": "augmented",
                }
        except Exception:
            return None
    return None


def maybe_generate_augmentation(
    root: Path,
    *,
    user_input: str,
    route: dict[str, Any],
    retrieved: list[dict[str, Any]],
    state: dict[str, Any],
    current_turn: int,
    session_augmentation_count: int,
    llm_client: OpenAICompatibleLLM | None = None,
) -> dict[str, Any] | None:
    """Produce one low-weight background detail and persist it when configured."""
    config = load_app_config(root)
    if not should_trigger_augmentation(
        route=route,
        retrieved=retrieved,
        state=state,
        config=config,
        current_turn=current_turn,
        session_augmentation_count=session_augmentation_count,
        user_input=user_input,
    ):
        return None

    detail = _maybe_web_augment(root, user_input, retrieved, config, llm_client=llm_client)
    if detail is None:
        anchors = [user_input] + [item.get("title", "") for item in retrieved[:2]]
        detail = interpolate_memory_frame(anchors, retrieved, route.get("mode", "daily_bubble"))
    if detail is None:
        return None

    if config.get("augmentation", {}).get("write_to_memory", True):
        append_augmented_memory(root, detail)
        build_index(root, load_indexable_memories(root))
    register_augmentation(root, current_turn)
    return detail
