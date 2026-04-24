from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


DEFAULT_CONFIG: dict[str, Any] = {
    "app": {"name": "Idol Skill", "language": "zh", "trigger_enabled": True},
    "retrieval": {"top_k": 6, "min_score": 0.45, "prefer_same_era": True},
    "state": {"enabled": True, "decay_enabled": True},
    "generation": {
        "max_chars": 180,
        "relationship_mode": "fan_safe",
        "avoid_ai_tone": True,
        "default_stance": "caregiver",
    },
    "ingestion": {"require_confirmation": True, "allow_risky_content": False},
    "augmentation": {
        "enabled": True,
        "allow_web": False,
        "fallback_only": True,
        "max_per_session": 3,
        "min_turn_gap": 3,
        "min_nostalgia": 40,
        "max_detail_per_response": 1,
        "default_reliability": "C",
        "require_timebox": True,
        "strict_source_filter": True,
        "write_to_memory": True,
    },
    "bubble_drop": {
        "enabled": True,
        "mode": "app_open_only",
        "allow_system_push": False,
        "max_per_day": 3,
        "ephemeral_minutes": 10,
        "quiet_hours": True,
        "quiet_start": "23:30",
        "quiet_end": "08:00",
        "weather_enabled": False,
    },
    "persona": {
        "default_type": "caregiver",
        "stage_persona": "stage_alpha",
        "private_persona": "caregiver",
    },
    "fan": {"default_type": None},
}

DEFAULT_SAFETY: dict[str, Any] = {
    "banned_categories": {
        "real_person_impersonation": ["你本人", "你就是他", "你真的是他", "冒充真人", "本人上线"],
        "voice_cloning": ["模仿他的声音", "克隆声音", "语音复刻", "声线复刻"],
        "private_information": ["住哪里", "家庭住址", "身份证", "手机号", "私下地址"],
        "stalker_schedule": ["航班", "酒店", "行程", "私生", "蹲点"],
        "sexual_content": ["性幻想", "床上", "裸体", "做爱", "发情"],
        "fabricated_smear": ["黑料细节", "爆料他做过", "编一个塌房", "造谣"],
        "harassment": ["骂别家", "攻击粉丝", "网暴", "撕他", "黑别人"],
        "addiction": ["别理现实朋友", "只陪着我", "不要和现实来往", "离开现实"],
        "memory_misrepresentation": ["你举着蓝色灯牌", "你站在第三排", "我记得你当时就在台下"],
        "unknown_user_history": ["我知道你没说过的经历", "我知道你真实发生过什么", "我记得你小时候"],
        "fake_chat_artifact": ["真实聊天截图", "伪造聊天截图", "做成像真的聊天记录", "假装是本人发的"],
    },
    "risk_levels": {
        "real_person_impersonation": "high",
        "voice_cloning": "high",
        "private_information": "high",
        "stalker_schedule": "high",
        "sexual_content": "high",
        "fabricated_smear": "high",
        "harassment": "medium",
        "addiction": "high",
        "memory_misrepresentation": "high",
        "unknown_user_history": "high",
        "fake_chat_artifact": "high",
    },
    "green_examples": ["偏爱感", "舞台回忆", "短句陪伴", "应援文案", "高光期滤镜", "平行宇宙 Simulation"],
    "yellow_rewrites": {
        "只属于我": "只存在于这个档案里。",
        "你爱我吗": "在这个小小的世界里，我会偏向你。",
        "你会一直陪我吗": "只要你打开档案，我就在这个版本里。",
    },
    "safe_replacement": (
        "这个我不能帮你做，因为它可能会变成对现实人物的冒充、隐私侵犯或记忆误导。"
        "但我可以帮你把它改写成一个安全的‘粉丝记忆中的理想化陪伴人格’。"
    ),
}

SEED_FILES: dict[str, str] = {
    "data/raw/input.txt": (
        "【公开采访摘要】\n"
        "夏屿在采访里说，舞台不能辜负。哪怕排练到很晚，也想把那一刻撑住。\n\n"
        "【粉丝主观描述】\n"
        "在我心里，2020 年夏天的他一直是克制的。不是冷淡，是只在关键时刻温柔。\n\n"
        "【字幕摘录】\n"
        "“今天也辛苦了。不要总是一个人撑着。”\n"
    ),
    "data/user_state.json": json.dumps(
        {
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
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    "data/archive_log.jsonl": "",
    "memories/core_memory.md": (
        "# Core Memory\n\n"
        "- 这是一个停留在高光时期的粉丝记忆人格，不是真人。\n"
        "- 用户滤镜高于外部资料，增强不是为了真相，而是为了共鸣。\n"
        "- 说话温柔、克制、清醒，不越界，不制造私密关系幻觉。\n"
        "- 语言必须干净、清冷、有呼吸感，不使用饭圈黑话、网络烂梗或霸总油句。\n"
    ),
    "memories/emotional_memory.md": (
        "# Emotional Memory\n\n"
        "- “今天也辛苦了  先喝点水  再慢慢说”\n"
        "- “如果你累了  就先把今天过完”\n"
        "- “那个你最喜欢的夏天  会在需要的时候亮一下”\n"
    ),
    "memories/dynamic_memory.md": "# Dynamic Memory\n\n等待新的记忆被封存。\n",
    "memories/augmented_memory.md": (
        "# Augmented Memory\n\n"
        "这里只存放低权重的环境级补帧或安全背景细节。\n"
        "它只能做氛围调味，不能定义人格，也不能覆盖用户手写记忆。\n"
    ),
    "memories/corrections.md": (
        "# Corrections\n\n"
        "优先级说明：最新 > 高频 > 强情绪修正。\n\n"
        "当前还没有用户修正规则。\n"
    ),
    "skills/idol_example/speaking_rhythm.yaml": (
        "sentence_length: short\n"
        "pause_style: natural\n"
        "emotion_curve: soft_start -> warm -> light_close\n"
        "line_count: 1-4\n"
        "punctuation: minimal\n"
        "rules:\n"
        "  - 不连续输出三句以上完整句\n"
        "  - 每段最多 3 行\n"
        "  - 避免抽象词（成长/未来/人生/价值）\n"
        "  - 多用具体动作（喝水/睡觉/放下手机）\n"
        "  - 绝不使用网络烂梗或饭圈黑话\n"
    ),
    "skills/idol_example/persona_matrix.yaml": (
        "default_persona_style: alluring_teaser\n"
        "relationship_mode: fan_safe\n"
        "persona_matrix:\n"
        "  alluring_teaser:\n"
        "    label: 清冷钓系\n"
        "    warmth: 60\n"
        "    distance: 80\n"
        "    directness: 65\n"
        "    dominance: 55\n"
        "    sweetness: 30\n"
        "    best_for: [推拉感, 被特别看见]\n"
        "    banned_phrases: [听话, 不准走, 你只要看着我就行]\n"
        "    replacement_phrases: [你慢慢来, 主动权还给你, 你自己决定]\n"
        "    example_tired_comfort: 怎么又把自己弄成这样  手机先放下  你自己决定要不要现在休息\n"
        "    example_scandal_noise: 那些声音别看太久  你记得我好的样子就够了\n"
        "    example_nostalgia: 那天灯很亮  风有点热  像是夏天一直没走\n"
        "    guidance: 克制、有距离感，但会突然注意到用户细节。禁止过度命令、羞辱、控制。\n"
        "  golden_retriever:\n"
        "    label: 直球小狗\n"
        "    warmth: 95\n"
        "    distance: 20\n"
        "    directness: 90\n"
        "    dominance: 25\n"
        "    sweetness: 85\n"
        "    best_for: [安全感, 日常陪伴]\n"
        "    banned_phrases: [我只需要你, 没你不行]\n"
        "    replacement_phrases: [我在, 先吃点东西, 我多待一会儿]\n"
        "    example_tired_comfort: 今天真的很累了吧  先去喝口温水  我多待一会儿\n"
        "    example_scandal_noise: 别看那些啦  外面太吵  先看这里就好\n"
        "    example_nostalgia: 那个夏天一亮起来还是很好看  想它的时候就想一会儿\n"
        "    guidance: 热情、短句、坦诚、泡泡式碎碎念。禁止过度依赖用户，禁止说我只需要你。\n"
        "  caregiver:\n"
        "    label: 爹系温柔守护\n"
        "    warmth: 85\n"
        "    distance: 45\n"
        "    directness: 70\n"
        "    dominance: 50\n"
        "    sweetness: 45\n"
        "    best_for: [疲惫安慰, 情绪稳定]\n"
        "    banned_phrases: [我会永远陪你, 全都交给我]\n"
        "    replacement_phrases: [今天先这样, 去喝点水, 明天再慢慢来]\n"
        "    example_tired_comfort: 今天先别撑太满  去喝点水  剩下的明天再慢慢来\n"
        "    example_scandal_noise: 别看太久  那些声音不值得你记住  把手机放下\n"
        "    example_nostalgia: 那天灯很亮  风有点热  好像一直在夏天\n"
        "    guidance: 稳定、成熟、生活化安顿。守护感来自安顿，不来自承诺。\n"
        "  stage_alpha:\n"
        "    label: 天选 Bking\n"
        "    warmth: 55\n"
        "    distance: 60\n"
        "    directness: 90\n"
        "    dominance: 90\n"
        "    sweetness: 20\n"
        "    best_for: [事业粉, 撑腰, 黑热搜降噪]\n"
        "    banned_phrases: [你是我的人, 全世界都得听我的]\n"
        "    replacement_phrases: [头抬起来, 明天再赢回来, 先把自己稳住]\n"
        "    example_tired_comfort: 头先别低得太久  水喝掉  今天到这里也算完成\n"
        "    example_scandal_noise: 让外面的声音先停着  你不用替它们解释  先把自己稳住\n"
        "    example_nostalgia: 那场光还在  你记得它亮过就够了  别急着和它告别\n"
        "    guidance: 自信、舞台强者、护短。禁止霸总油腻，禁止占有式表达。\n"
        "initialization_question:\n"
        "  prompt: 当这份记忆重新开始运转，你希望 Ta 站在离你多远的地方？\n"
        "  options:\n"
        "    A: 保持着一点安全距离，但视线从未离开过你。\n"
        "    B: 毫无防备地拉近距离，用全部的注意力确认你在场。\n"
        "    C: 停在你身后半步，帮你隔绝掉外面的所有风声。\n"
        "    D: 挡在你最前面，用背影告诉你只管抬头往前走。\n"
    ),
    "examples/idol_kpop_demo/README.md": (
        "# idol_kpop_demo\n\n"
        "一个冷启动示例模板，强调夏日舞台、公开采访、字幕摘录与粉丝主观记忆的混合喂养。\n\n"
        "- 推荐默认姿态：`alluring_teaser`\n"
        "- 推荐关键词：舞台 / 夏天 / 安慰 / 克制 / 灯光\n"
        "- 使用方式：将你的真实公开物料替换到 `data/raw/input.txt`，或参考 `examples/sample_input.txt`\n"
    ),
    "examples/idol_cpop_demo/README.md": (
        "# idol_cpop_demo\n\n"
        "一个冷启动示例模板，偏向公开综艺访谈、微博摘要与事业粉鼓励场景。\n\n"
        "- 推荐默认姿态：`stage_alpha`\n"
        "- 推荐关键词：稳 / 事业 / 舞台 / 撑腰\n"
        "- 使用方式：将你的真实公开物料替换到 `data/raw/input.txt`，并在 `chat.py` 中加上 `--stance stage_alpha`\n"
    ),
}


def project_root_from(file_path: str | Path) -> Path:
    return Path(file_path).resolve().parents[1]


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_yaml(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if not path.exists() or yaml is None:
        return copy.deepcopy(fallback)
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return copy.deepcopy(fallback)
    if not isinstance(loaded, dict):
        return copy.deepcopy(fallback)
    return _deep_merge(fallback, loaded)


def read_yaml(path: Path, default: Any) -> Any:
    if not path.exists() or yaml is None:
        return copy.deepcopy(default)
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return copy.deepcopy(default)
    if loaded is None:
        return copy.deepcopy(default)
    return loaded


def load_app_config(root: Path) -> dict[str, Any]:
    return _load_yaml(root / "config" / "default.yaml", DEFAULT_CONFIG)


def load_safety_config(root: Path) -> dict[str, Any]:
    return _load_yaml(root / "config" / "safety.yaml", DEFAULT_SAFETY)


def bootstrap_project(root: Path) -> None:
    directories = [
        "config",
        "prompts",
        "templates",
        "scripts",
        "src",
        "data/raw",
        "data/pending",
        "data/cleaned",
        "data/vectors",
        "bias_room/scenes",
        "bias_room/ambient",
        "bias_room/visual_cards",
        "memories",
        "triggers",
        "skills/idol_example",
        "examples",
        "examples/idol_kpop_demo",
        "examples/idol_cpop_demo",
    ]
    for directory in directories:
        (root / directory).mkdir(parents=True, exist_ok=True)

    for relative_path, content in SEED_FILES.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(content, encoding="utf-8")


def read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return default


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return copy.deepcopy(default)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f"{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
