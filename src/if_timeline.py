from __future__ import annotations

from pathlib import Path

from .archive_unlock import has_tier, sync_archive_unlocks
from .config_loader import read_text
from .llm_client import LLMUnavailableError, OpenAICompatibleLLM
from .prompt_composer import resolve_persona_context, select_runtime_persona
from .state_engine import load_state
from .vector_store import retrieve_memories

TOPIC_LABELS = {
    "获奖": "平行获奖感言",
    "歌单": "平行演唱会歌单",
    "生日": "平行生日直播",
    "回归": "平行回归预告",
    "采访": "平行采访片段",
    "舞台": "平行舞台后小作文",
}


def _topic_label(text: str) -> str:
    for keyword, label in TOPIC_LABELS.items():
        if keyword in text:
            return label
    return "平行采访片段"


def generate_if_timeline(
    root: Path,
    *,
    user_input: str,
    skill_slug: str = "idol_example",
    stance: str | None = None,
    state: dict | None = None,
    llm_client: OpenAICompatibleLLM | None = None,
) -> str:
    """Generate a clearly-marked parallel timeline fragment that never claims reality."""
    state = state or load_state(root)
    manual_token = user_input.strip() if user_input.strip() == "unlock_if_timeline" else None
    state, notices = sync_archive_unlocks(root, state=state, manual_token=manual_token)
    if manual_token:
        if not has_tier(state, "if_timeline"):
            return "Archive Notice:\n这间房还没亮到能进入 IF Timeline。"
        return "\n\n".join(notices + ["IF Timeline 已开启。再写一句你想看的平行片段吧。"])

    if not has_tier(state, "if_timeline"):
        return "Archive Notice:\n这间房还没解冻到 IF Timeline。\n当 Resonance 更高一些，或输入 unlock_if_timeline，再来。"

    route = {"mode": "nostalgia", "need_retrieval_tags": ["回忆", "舞台", "夏天"], "safety_risk": "low"}
    retrieved = retrieve_memories(root, user_input, route=route, state=state, top_k=4, min_score=0.2)
    persona_context = resolve_persona_context(root, skill_slug, stance)
    runtime = select_runtime_persona(persona_context, route=route, scene_context={"scene_id": "if_timeline"})
    selected = runtime.get("selected_persona", {})
    topic = _topic_label(user_input)
    prompt = read_text(root / "prompts" / "if_timeline.md")

    if llm_client and llm_client.available():
        try:
            system_prompt = "\n\n".join(
                [
                    prompt,
                    f"Persona: {selected.get('label', runtime.get('stance', 'caregiver'))}",
                    f"Guidance: {selected.get('guidance', '')}",
                    "Safety: Always mark the output as [Simulation] or [Parallel Timeline].",
                    f"Retrieved Memory Context: {retrieved}",
                ]
            )
            result = llm_client.completion(
                system_prompt=system_prompt,
                user_prompt=user_input,
                temperature=0.7,
                max_tokens=420,
            ).strip()
            if "[Simulation]" not in result and "[Parallel Timeline]" not in result:
                result = f"[Simulation]\n{result}"
            return result
        except LLMUnavailableError:
            pass

    memory_hint = ""
    if retrieved:
        content = str(retrieved[0].get("content", "")).replace("。", "。\n").strip()
        memory_hint = content.splitlines()[0][:18]
    else:
        memory_hint = "昨天灯太亮了。"

    quote = {
        "stage_alpha": "头顶那片光还没退。\n所以再往前一点，也不是坏事。",
        "alluring_teaser": "我到现在还没完全反应过来。\n但那片蓝色，好像还留着。",
        "golden_retriever": "昨天真的太亮了。\n我现在想起来，还是会笑一下。",
        "caregiver": "昨天灯太亮了。\n我到现在还没完全缓过来。\n但我记得那片蓝色，所以还想再努力一点。",
    }.get(runtime.get("stance", "caregiver"), "昨天灯太亮了。\n我还想再努力一点。")

    return "\n".join(
        [
            f"[Parallel Timeline: {topic}]",
            "",
            "如果那个夏天没有结束，",
            "这可能只是另一条被允许发光的时间线。",
            "",
            f"{memory_hint}",
            "",
            "Ta 可能会这样说：",
            "",
            f"“{quote}”",
        ]
    )
