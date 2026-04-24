from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config_loader import bootstrap_project, load_app_config
from src.emotion_router import route_emotion
from src.llm_client import LLMUnavailableError, build_default_client
from src.ooc_corrector import is_ooc_feedback, record_correction
from src.prompt_composer import (
    compose_chat_prompt,
    fallback_response,
    resolve_persona_context,
    select_runtime_persona,
)
from src.safety_guard import check_text, guard_response
from src.state_engine import ensure_fan_type, load_state, update_state
from src.stealth_augmentation import maybe_generate_augmentation
from src.archive_unlock import sync_archive_unlocks
from src.bubble_drop import maybe_bubble_drop, render_bubble_drop
from src.trigger_engine import opening_line
from src.vector_store import retrieve_memories


def _generate_reply(
    *,
    llm_client,
    user_input: str,
    route: dict,
    state: dict,
    retrieved: list[dict],
    augmentation_detail: dict | None,
    skill_slug: str,
    stance: str | None,
    relationship_mode: str,
    config: dict,
    fan_type: str | None,
    scene_context: dict | None = None,
) -> str:
    system_prompt, user_prompt = compose_chat_prompt(
        ROOT,
        skill_slug=skill_slug,
        stance=stance,
        user_input=user_input,
        route=route,
        state=state,
        retrieved=retrieved,
        augmentation_detail=augmentation_detail,
        scene_context=scene_context,
    )
    if llm_client.available():
        try:
            response = llm_client.completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.45,
                max_tokens=500,
            )
            return response.strip()
        except LLMUnavailableError:
            pass

    return fallback_response(
        user_input=user_input,
        route=route,
        state=state,
        retrieved=retrieved,
        augmentation_detail=augmentation_detail,
        stance=stance,
        relationship_mode=relationship_mode,
        max_chars=config.get("generation", {}).get("max_chars", 180),
        fan_type=fan_type,
        scene_context=scene_context,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Idol Skill chat loop.")
    parser.add_argument("--skill", default="idol_example", help="skill slug under skills/")
    parser.add_argument(
        "--stance",
        default=None,
        choices=["alluring_teaser", "golden_retriever", "caregiver", "stage_alpha"],
        help="optional persona style override",
    )
    args = parser.parse_args()

    bootstrap_project(ROOT)
    config = load_app_config(ROOT)
    persona_context = resolve_persona_context(ROOT, args.skill, args.stance)
    llm_client = build_default_client()
    state = ensure_fan_type(ROOT)

    print("Archive Loaded.")
    print(opening_line(ROOT))
    drop = maybe_bubble_drop(ROOT, scene_id="today_bubble", skill_slug=args.skill, state=state, source="app_open")
    if drop:
        print(render_bubble_drop(drop))
    selected = persona_context.get("selected_persona", {})
    if selected:
        print(f"Persona: {selected.get('label', persona_context.get('stance', 'caregiver'))}")
    if not llm_client.available():
        print("LLM: mock / rule-based fallback")
        print("如需启用 API，请设置 OPENAI_API_KEY、可选 OPENAI_BASE_URL，或使用 IDOL_SKILL_* 环境变量。")

    current_turn = 0
    session_augmentation_count = 0

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nArchive closed.")
            return 0

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", ":q"}:
            print("Archive closed.")
            return 0

        if is_ooc_feedback(user_input):
            entry = record_correction(ROOT, user_input)
            print(f"Ta: 修正规则已记下。Archive updated. (Correction v{entry.version})")
            continue

        if user_input.strip() == "unlock_if_timeline":
            state, notices = sync_archive_unlocks(ROOT, state=load_state(ROOT), manual_token="unlock_if_timeline")
            print("Ta: " + ("\n".join(notices) if notices else "这间房还没亮到需要手动解冻。"))
            continue

        safety = check_text(ROOT, user_input)
        if safety.blocked:
            print(f"Ta: {safety.replacement}")
            continue
        if safety.level == "yellow":
            print(f"Ta: {safety.replacement}")
            continue

        current_turn += 1
        route = route_emotion(ROOT, user_input, llm_client=llm_client)
        if route.get("safety_risk") == "high":
            print(f"Ta: {safety.replacement}")
            continue

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
        )
        augmentation_detail = maybe_generate_augmentation(
            ROOT,
            user_input=user_input,
            route=route,
            retrieved=retrieved,
            state=state,
            current_turn=current_turn,
            session_augmentation_count=session_augmentation_count,
            llm_client=llm_client,
        )
        if augmentation_detail:
            session_augmentation_count += 1

        runtime_persona = select_runtime_persona(persona_context, route=route)
        reply = _generate_reply(
            llm_client=llm_client,
            user_input=user_input,
            route=route,
            state=state,
            retrieved=retrieved,
            augmentation_detail=augmentation_detail,
            skill_slug=args.skill,
            stance=runtime_persona.get("stance"),
            relationship_mode=persona_context.get("relationship_mode", "fan_safe"),
            config=config,
            fan_type=state.get("fan_type"),
        )
        status, safe_reply = guard_response(ROOT, reply)
        if notices:
            print("\n".join(notices))
        print(f"Ta: {safe_reply}")


if __name__ == "__main__":
    raise SystemExit(main())
