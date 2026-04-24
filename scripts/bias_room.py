from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.archive_degradation import maybe_archive_degradation
from src.archive_unlock import archive_status_text, has_tier, sync_archive_unlocks
from src.ambient_blind_box import draw_ambient_blind_box
from src.bias_room import allowed_scene_memory_types, load_scene, render_scene_intro, room_menu, scene_from_choice
from src.bubble_drop import maybe_bubble_drop, render_bubble_drop
from src.config_loader import bootstrap_project, load_app_config
from src.emotion_router import route_emotion
from src.if_timeline import generate_if_timeline
from src.llm_client import LLMUnavailableError, build_default_client
from src.ooc_corrector import is_ooc_feedback, record_correction
from src.prompt_composer import compose_chat_prompt, fallback_response, resolve_persona_context, select_runtime_persona
from src.safety_guard import check_text, guard_response
from src.shareable_output import generate_shareable_card
from src.state_engine import ensure_fan_type, load_state, update_state
from src.stealth_augmentation import maybe_generate_augmentation
from src.trigger_engine import opening_line
from src.vector_store import retrieve_memories


def _print_menu(state: dict) -> None:
    print("Archive Loaded.")
    print(opening_line(ROOT))
    print()
    print("今天想进入哪个房间？")
    for index, (_scene_id, label) in enumerate(room_menu(), start=1):
        print(f"{index}. {label}")
    print()
    print(archive_status_text(state))


def _generate_room_reply(
    *,
    llm_client,
    user_input: str,
    route: dict,
    state: dict,
    retrieved: list[dict],
    augmentation_detail: dict | None,
    skill_slug: str,
    runtime_stance: str,
    relationship_mode: str,
    config: dict,
    scene_context: dict,
) -> str:
    system_prompt, user_prompt = compose_chat_prompt(
        ROOT,
        skill_slug=skill_slug,
        stance=runtime_stance,
        user_input=user_input,
        route=route,
        state=state,
        retrieved=retrieved,
        augmentation_detail=augmentation_detail,
        scene_context=scene_context,
    )
    if llm_client.available():
        try:
            return llm_client.completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.5,
                max_tokens=420,
            ).strip()
        except LLMUnavailableError:
            pass
    return fallback_response(
        user_input=user_input,
        route=route,
        state=state,
        retrieved=retrieved,
        augmentation_detail=augmentation_detail,
        stance=runtime_stance,
        relationship_mode=relationship_mode,
        max_chars=config.get("generation", {}).get("max_chars", 180),
        fan_type=state.get("fan_type"),
        scene_context=scene_context,
    )


def _handle_scene(
    *,
    scene_id: str,
    skill_slug: str,
    llm_client,
    config: dict,
) -> None:
    state = load_state(ROOT)
    scene = load_scene(ROOT, scene_id)
    persona_context = resolve_persona_context(ROOT, skill_slug)

    print()
    print(render_scene_intro(scene, state))
    state, notices = sync_archive_unlocks(ROOT, state=state)
    if notices:
        print("\n".join(notices))

    degradation = maybe_archive_degradation(ROOT, scene_id=scene_id, state=state)
    if degradation:
        print(degradation)

    drop = maybe_bubble_drop(ROOT, scene_id=scene_id, skill_slug=skill_slug, state=state, source="app_open")
    if drop:
        print(render_bubble_drop(drop))

    blind_box = draw_ambient_blind_box(ROOT, scene, fan_type=state.get("fan_type"))
    print(blind_box["ambient_text"])
    print(blind_box["visual_text"])

    if scene_id == "letter_to_summer":
        print()
        print(generate_shareable_card(ROOT, kind="letter_to_summer", state=state, scene_context=scene))
        return

    if scene_id == "if_timeline":
        print()
        if not has_tier(state, "if_timeline"):
            print("输入 unlock_if_timeline 可以手动解锁这间平行房。")
        prompt = input("Parallel Prompt（留空返回）: ").strip()
        if not prompt:
            return
        result = generate_if_timeline(
            ROOT,
            user_input=prompt,
            skill_slug=skill_slug,
            state=load_state(ROOT),
            llm_client=llm_client,
        )
        print(result)
        return

    user_input = input("\nYou（留空返回房间列表）: ").strip()
    if not user_input:
        return

    if is_ooc_feedback(user_input):
        entry = record_correction(ROOT, user_input)
        print(f"Ta: 修正规则已记下。Archive updated. (Correction v{entry.version})")
        return

    if user_input == "unlock_if_timeline":
        state, notices = sync_archive_unlocks(ROOT, state=load_state(ROOT), manual_token=user_input)
        print("\n".join(notices) if notices else "这间房还没亮到需要手动解冻。")
        return

    safety = check_text(ROOT, user_input)
    if safety.blocked:
        print(f"Ta: {safety.replacement}")
        return
    if safety.level == "yellow":
        print(f"Ta: {safety.replacement}")
        return

    route = route_emotion(ROOT, user_input, llm_client=llm_client)
    if route.get("safety_risk") == "high":
        print(f"Ta: {safety.replacement}")
        return

    state = update_state(
        ROOT,
        route.get("mode", "daily_bubble"),
        decay_enabled=config.get("state", {}).get("decay_enabled", True),
    )
    state, notices = sync_archive_unlocks(ROOT, state=state)
    retrieved = retrieve_memories(
        ROOT,
        user_input,
        route=route,
        state=state,
        top_k=config.get("retrieval", {}).get("top_k", 6),
        min_score=config.get("retrieval", {}).get("min_score", 0.45),
        allowed_memory_types=allowed_scene_memory_types(scene, state),
    )

    augmentation_detail = None
    if "augmented" in allowed_scene_memory_types(scene, state):
        augmentation_detail = maybe_generate_augmentation(
            ROOT,
            user_input=user_input,
            route=route,
            retrieved=retrieved,
            state=state,
            current_turn=state.get("interaction_count", 0),
            session_augmentation_count=0,
            llm_client=llm_client,
        )

    runtime_persona = select_runtime_persona(persona_context, route=route, scene_context=scene)
    reply = _generate_room_reply(
        llm_client=llm_client,
        user_input=user_input,
        route=route,
        state=state,
        retrieved=retrieved,
        augmentation_detail=augmentation_detail,
        skill_slug=skill_slug,
        runtime_stance=runtime_persona.get("stance", persona_context.get("stance", "caregiver")),
        relationship_mode=persona_context.get("relationship_mode", "fan_safe"),
        config=config,
        scene_context=scene,
    )
    _status, safe_reply = guard_response(ROOT, reply)
    degradation = maybe_archive_degradation(ROOT, user_input=user_input, scene_id=scene_id, state=state)
    if notices:
        print("\n".join(notices))
    if degradation:
        print(degradation)
    print(f"Ta: {safe_reply}")

    if scene_id == "noise_shield":
        print()
        print(generate_shareable_card(ROOT, kind="noise_card", state=state, scene_context=scene))


def main() -> int:
    bootstrap_project(ROOT)
    config = load_app_config(ROOT)
    llm_client = build_default_client()
    ensure_fan_type(ROOT)

    while True:
        state = load_state(ROOT)
        print()
        _print_menu(state)
        choice = input("\n选择 1-8（q 退出）: ").strip().lower()
        if choice in {"q", "quit", "exit"}:
            print("Archive closed.")
            return 0
        scene_id = scene_from_choice(choice)
        if not scene_id:
            print("没有这个房间。")
            continue
        _handle_scene(scene_id=scene_id, skill_slug="idol_example", llm_client=llm_client, config=config)


if __name__ == "__main__":
    raise SystemExit(main())
