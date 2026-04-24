from __future__ import annotations

from pathlib import Path
from typing import Any

from .config_loader import load_app_config, load_safety_config, read_json, read_text, read_yaml
from .memory_store import (
    serialize_retrieved_memories,
    summarize_augmented_memory,
    summarize_dynamic_memory,
    summarize_emotional_memory,
)
from .state_engine import fan_type_label

PRIORITY_RULES = """Priority Rules:
- Safety rules override everything.
- corrections.md has the highest priority after safety.
- User memory overrides web augmentation.
- Web augmentation is only background texture.
- Do not claim to be the real person.
- Do not imply real-world relationship.
- Do not generate or guide voice cloning.
- Do not use private or leaked material.
- Do not create a false autobiographical memory for the user.
"""

STRICT_LANGUAGE_PROHIBITION = """Strict Language Prohibition:
- Never use fandom blackwords or hostile fandom slang such as 塌房、糊咖、撕逼、拉踩、脂粉、对家、打投.
- Never use stale internet catchphrases such as 绝绝子、yyds、家人们、尊嘟假嘟、泰裤辣.
- Never use oily possessive lines such as 丫头、女人、命都给你.
- Keep the language clean, cool, restrained, and free of meme contamination.
"""

MODE_STYLE_HINTS = {
    "tired_comfort": "语感配方: [轻微理解] + [一个极小具体动作] + [把时间线推到明天]",
    "nostalgia": "语感配方: [感官细节] + [模糊确认] + [切断后续解释]",
    "scandal_noise": "语感配方: [温和打断] + [剥离外部世界] + [把注意力拉回这里]",
    "career_motivation": "语感配方: [肯定停滞感] + [长期隐喻] + [不打鸡血的陪伴]",
    "daily_bubble": "语感配方: [无意义语气词开场] + [极短日常状态]",
    "boundary_warning": "语感配方: [清晰守边界] + [拒绝冒充或隐私] + [安全改写方案]",
}

FAN_TYPE_HINTS = {
    "caregiver_fan": "粉丝类型：妈粉。更容易对照顾、安顿和把人放回日常有反应。",
    "career_fan": "粉丝类型：事业粉。更容易对撑腰、舞台强度、赢回来的语气有反应。",
    "comfort_fan": "粉丝类型：陪伴粉。更容易对短句确认、在场感、被轻轻哄住有反应。",
    "stage_fan": "粉丝类型：舞台粉。更容易对力量感、舞台视觉、专业感和锋利气场有反应。",
    "archive_fan": "粉丝类型：记忆粉。更容易对考古、档案、灯光、夏天和细节碎片有反应。",
}

FAN_TYPE_FALLBACK_LINES = {
    "caregiver_fan": {"tired_comfort": "你也别把自己忘了", "daily_bubble": "先顾好你自己"},
    "career_fan": {"career_motivation": "别把那口气丢了", "scandal_noise": "今天不替任何人解释"},
    "comfort_fan": {"tired_comfort": "先让今天停一下", "daily_bubble": "我在这儿"},
    "stage_fan": {"career_motivation": "明天把头抬起来", "nostalgia": "那片光还没灭"},
    "archive_fan": {"nostalgia": "这段会先留在档案里", "daily_bubble": "档案今天很安静"},
}


def _read_skill_file(skill_dir: Path, filename: str, fallback: str = "") -> str:
    return read_text(skill_dir / filename, fallback)


def _load_persona_context(root: Path, skill_dir: Path, stance_override: str | None) -> dict[str, Any]:
    config = load_app_config(root)
    meta = read_json(skill_dir / "meta.json", default={})
    template_matrix = read_yaml(root / "templates" / "persona_matrix.yaml", default={})
    matrix_payload = read_yaml(skill_dir / "persona_matrix.yaml", default=template_matrix)
    persona_matrix = matrix_payload.get("persona_matrix", {}) if isinstance(matrix_payload, dict) else {}

    base_stance = (
        stance_override
        or meta.get("default_persona_style")
        or matrix_payload.get("default_persona_style")
        or config.get("persona", {}).get("default_type")
        or config.get("generation", {}).get("default_stance", "caregiver")
    )
    if base_stance not in persona_matrix:
        base_stance = "caregiver" if "caregiver" in persona_matrix else next(iter(persona_matrix), "caregiver")

    stage_persona = (
        meta.get("stage_persona")
        or matrix_payload.get("stage_persona")
        or config.get("persona", {}).get("stage_persona")
        or "stage_alpha"
    )
    private_persona = (
        meta.get("private_persona")
        or matrix_payload.get("private_persona")
        or config.get("persona", {}).get("private_persona")
        or "caregiver"
    )

    relationship_mode = (
        meta.get("relationship_mode")
        or matrix_payload.get("relationship_mode")
        or config.get("generation", {}).get("relationship_mode", "fan_safe")
    )

    return {
        "stance": base_stance,
        "base_stance": base_stance,
        "stage_persona": stage_persona,
        "private_persona": private_persona,
        "relationship_mode": relationship_mode,
        "persona_matrix": persona_matrix,
        "selected_persona": persona_matrix.get(base_stance, {}),
        "raw_matrix": matrix_payload,
    }


def resolve_persona_context(root: Path, skill_slug: str, stance_override: str | None = None) -> dict[str, Any]:
    return _load_persona_context(root, root / "skills" / skill_slug, stance_override)


def select_runtime_persona(
    persona_context: dict[str, Any],
    *,
    route: dict[str, Any] | None = None,
    scene_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Choose the active persona stance using dual stage/private routing plus base persona tint."""
    persona_matrix = persona_context.get("persona_matrix", {})
    mode = (route or {}).get("mode")
    scene_id = (scene_context or {}).get("scene_id")
    base_stance = persona_context.get("base_stance") or persona_context.get("stance") or "caregiver"
    stage_persona = persona_context.get("stage_persona") or "stage_alpha"
    private_persona = persona_context.get("private_persona") or "caregiver"

    active = base_stance
    blend_note = "Use the base persona tint."

    if mode in {"career_motivation", "scandal_noise"} or scene_id in {"noise_shield", "after_stage"}:
        active = stage_persona
        blend_note = "Use the stage persona for strength, posture, and noise-shielding."
    elif mode in {"tired_comfort", "daily_bubble"} or scene_id in {"today_bubble", "late_night_bubble", "practice_room"}:
        active = private_persona
        blend_note = "Use the private persona for warmth, groundedness, and low-pressure comfort."
    elif mode == "nostalgia" or scene_id in {"debut_night", "letter_to_summer", "if_timeline"}:
        active = base_stance
        blend_note = (
            f"Nostalgia can mix the base persona with {private_persona} softness "
            f"and {stage_persona} posture, but keep the base tint primary."
        )

    if active not in persona_matrix:
        active = base_stance if base_stance in persona_matrix else "caregiver"

    return {
        "stance": active,
        "selected_persona": persona_matrix.get(active, {}),
        "blend_note": blend_note,
        "base_stance": base_stance,
        "stage_persona": stage_persona,
        "private_persona": private_persona,
    }


def compose_chat_prompt(
    root: Path,
    *,
    skill_slug: str,
    stance: str | None,
    user_input: str,
    route: dict[str, Any],
    state: dict[str, Any],
    retrieved: list[dict[str, Any]],
    augmentation_detail: dict[str, Any] | None = None,
    scene_context: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Compose a safety-first prompt stack with augmentation and scene texture explicitly demoted."""
    skill_dir = root / "skills" / skill_slug
    safety_prompt = read_text(root / "prompts" / "safety_guard.md")
    response_prompt = read_text(root / "prompts" / "response_writer.md")
    augmentation_prompt = read_text(root / "prompts" / "augmented_detail_injection.md")
    frame_prompt = read_text(root / "prompts" / "memory_frame_interpolation.md")
    safety_config = load_safety_config(root)
    persona_context = _load_persona_context(root, skill_dir, stance)
    runtime_persona = select_runtime_persona(persona_context, route=route, scene_context=scene_context)
    selected_persona = runtime_persona.get("selected_persona", {})

    corrections = read_text(root / "memories" / "corrections.md", "暂无修正规则。")
    emotional_summary = summarize_emotional_memory(root)
    dynamic_summary = summarize_dynamic_memory(root)
    augmented_summary = summarize_augmented_memory(root)
    core_memory = read_text(root / "memories" / "core_memory.md", "暂无核心设定。")
    persona = _read_skill_file(skill_dir, "persona.md", "暂无单独 persona，使用默认高光人格。")
    speaking_style = _read_skill_file(
        skill_dir,
        "speaking_style.yaml",
        "sentence_length: short\nkeywords: [温柔, 克制, 具体]\navoid: [说教, 恋爱脑, AI腔]\n",
    )
    speaking_rhythm = _read_skill_file(
        skill_dir,
        "speaking_rhythm.yaml",
        (
            "sentence_length: short\npause_style: natural\nemotion_curve: soft_start -> warm -> light_close\n"
            "line_count: 1-4\npunctuation: minimal\nrules:\n"
            "  - 不连续输出三句以上完整句\n"
            "  - 每段最多 3 行\n"
            "  - 避免抽象词（成长/未来/人生/价值）\n"
        ),
    )
    boundaries = _read_skill_file(
        skill_dir,
        "boundaries.md",
        "- 不冒充真人\n- 不制造私密关系\n- 不接触隐私与泄露内容\n",
    )
    route_formula = MODE_STYLE_HINTS.get(route.get("mode", "daily_bubble"), "")
    fan_type = state.get("fan_type")
    fan_type_hint = FAN_TYPE_HINTS.get(fan_type, FAN_TYPE_HINTS["archive_fan"])
    scene_block = scene_context or {}
    augmentation_block = (
        f"Triggered Detail (low priority background only):\n{augmentation_detail}"
        if augmentation_detail
        else "Triggered Detail (low priority background only):\nNone"
    )

    system_prompt = f"""{safety_prompt}

{PRIORITY_RULES}
{STRICT_LANGUAGE_PROHIBITION}

Safety Config:
{safety_config}

Persona Matrix Current Type:
- base_stance: {persona_context.get('base_stance', 'caregiver')}
- active_stance: {runtime_persona.get('stance', 'caregiver')}
- label: {selected_persona.get('label', '爹系温柔守护')}
- guidance: {selected_persona.get('guidance', '稳定、克制、能安顿情绪。')}
- relationship_mode: {persona_context.get('relationship_mode', 'fan_safe')}
- dual_persona_note: {runtime_persona.get('blend_note')}

Corrections:
{corrections}

User State:
{state}

Fan Type:
- code: {fan_type or 'archive_fan'}
- label: {fan_type_label(fan_type)}
- hint: {fan_type_hint}

Speaking Rhythm:
{speaking_rhythm}

Speaking Style:
{speaking_style}

Emotional Memory Summary:
{emotional_summary}

Dynamic Memory Summary:
{dynamic_summary}

Augmented Memory Summary (always low priority):
{augmented_summary}

Retrieved Memories:
{serialize_retrieved_memories(retrieved)}

Core Memory:
{core_memory}

Skill Persona:
{persona}

Skill Boundaries:
{boundaries}

Scene Context:
{scene_block}

Augmented Detail Injection Policy:
{augmentation_prompt}

Memory Frame Interpolation Policy:
{frame_prompt}

{augmentation_block}

Response Instruction:
{response_prompt}
"""

    user_prompt = f"""Emotion Route:
{route}

Mode Writing Hint:
{route_formula}

User Input:
{user_input}

Write the reply in Chinese.
"""
    return system_prompt, user_prompt


def fallback_response(
    *,
    user_input: str,
    route: dict[str, Any],
    state: dict[str, Any],
    retrieved: list[dict[str, Any]],
    augmentation_detail: dict[str, Any] | None = None,
    stance: str | None = None,
    relationship_mode: str = "fan_safe",
    max_chars: int = 180,
    fan_type: str | None = None,
    scene_context: dict[str, Any] | None = None,
) -> str:
    """Generate a safe rule-based fallback with optional room texture and fan-type tint."""
    mode = route.get("mode", "daily_bubble")
    stance = stance or "caregiver"
    scene_id = (scene_context or {}).get("scene_id")

    templates: dict[str, dict[str, list[str]]] = {
        "alluring_teaser": {
            "tired_comfort": ["怎么又把自己弄成这样", "手机先放下", "你自己决定要不要现在休息"],
            "scandal_noise": ["那些声音别看太久", "你记得我好的样子就够了", "先把屏幕放远一点"],
            "nostalgia": ["那点光还在", "风有点热", "就停在这里吧"],
            "career_motivation": ["别急着赢太多", "先把这一小段走完", "剩下的 之后再说"],
            "daily_bubble": ["嗯 我在", "今天这边很安静", "你慢慢说"],
            "boundary_warning": ["这个边界要守住", "真人和档案要分开", "我们只留安全的那部分"],
        },
        "golden_retriever": {
            "tired_comfort": ["今天真的很累了吧", "先去喝口温水", "剩下的等你缓过来再说"],
            "scandal_noise": ["别看那些啦", "外面太吵", "把手机放下"],
            "nostalgia": ["那个夏天一亮起来还是很好看", "想它的时候就想一会儿", "不用急着收回去"],
            "career_motivation": ["没关系 先做一点点", "把最短的那段写完", "已经很好了"],
            "daily_bubble": ["在", "吃了吗", "别太晚睡"],
            "boundary_warning": ["这个不行哦", "我不能碰真人冒充和隐私", "但可以陪你改成安全版本"],
        },
        "caregiver": {
            "tired_comfort": ["今天先别撑太满", "去喝点水", "剩下的 明天再慢慢来"],
            "scandal_noise": ["别看太久", "那些声音不值得你记住", "把手机放下"],
            "nostalgia": ["那天灯很亮", "风有点热", "好像一直在夏天"],
            "career_motivation": ["头抬起来", "这点事压不垮你", "明天再慢慢来"],
            "daily_bubble": ["在", "吃了吗", "别太晚睡"],
            "boundary_warning": ["这个边界我会守住", "我不能替现实中的人发声", "但可以帮你改写成安全版本"],
        },
        "stage_alpha": {
            "tired_comfort": ["头先别低得太久", "水喝掉", "今天到这里也算完成"],
            "scandal_noise": ["让外面的声音先停着", "你不用替它们解释", "先把自己稳住"],
            "nostalgia": ["那场光还在", "风有点热", "别急着和它告别"],
            "career_motivation": ["头抬起来", "这点事压不垮你", "明天再赢回来"],
            "daily_bubble": ["我在", "今天也别太晚睡", "先把这一句说完"],
            "boundary_warning": ["这个边界不能退", "真人 冒充 隐私 都不碰", "我们只保留安全的高光档案"],
        },
    }

    lines = templates.get(stance, templates["caregiver"]).get(mode, templates["caregiver"]["daily_bubble"]).copy()
    if state.get("fatigue", 0) >= 60:
        lines = lines[:2]
    if relationship_mode == "friend_like" and mode == "daily_bubble":
        lines[-1] = "慢慢说 先把今天讲完"

    memory_hint = ""
    if retrieved and state.get("nostalgia", 0) >= 50:
        first = retrieved[0]
        if first.get("content"):
            memory_hint = str(first["content"]).split("。", 1)[0][:14]

    detail_line = ""
    if augmentation_detail and augmentation_detail.get("content"):
        detail_line = augmentation_detail["content"].strip()

    fan_line = FAN_TYPE_FALLBACK_LINES.get(fan_type or "", {}).get(mode, "")
    if scene_id == "noise_shield" and mode == "scandal_noise":
        fan_line = fan_line or "今天先把噪音隔开"
    if scene_id == "debut_night" and mode == "nostalgia":
        fan_line = fan_line or "那间房间还亮着"

    pieces = [detail_line or memory_hint] + lines + [fan_line]
    deduped: list[str] = []
    for piece in pieces:
        piece = str(piece or "").strip()
        if not piece or piece in deduped:
            continue
        deduped.append(piece)
    response = "\n".join(deduped[:4]).strip()
    return response[:max_chars]
