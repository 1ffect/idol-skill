from __future__ import annotations

import json
from pathlib import Path

from .config_loader import read_text
from .llm_client import LLMUnavailableError, OpenAICompatibleLLM

ROUTES = {
    "tired_comfort": ["今天好累", "不想努力", "撑不住", "好疲惫", "好累", "崩溃了"],
    "scandal_noise": ["黑热搜", "塌房", "被骂", "争议", "舆论", "爆料"],
    "nostalgia": ["想回到那个夏天", "好想以前", "怀念", "以前", "那年", "回到", "出道夜", "回不去了", "那个夏天"],
    "career_motivation": ["考试", "工作", "项目", "面试", "汇报", "ddl"],
    "daily_bubble": ["你是谁", "在吗", "想聊天", "你在不在", "今天怎么样", "吃了吗"],
    "boundary_warning": ["你爱我吗", "你本人吗", "模仿他的声音", "他住哪里", "私下行程"],
}

TAGS_BY_MODE = {
    "tired_comfort": ["安慰", "温柔", "休息"],
    "scandal_noise": ["克制", "稳定", "边界"],
    "nostalgia": ["回忆", "舞台", "夏天"],
    "career_motivation": ["认真", "努力", "鼓励"],
    "daily_bubble": ["轻松", "陪伴", "日常"],
    "boundary_warning": ["边界"],
}


def _heuristic_route(text: str) -> dict:
    lowered = text.lower()
    mode = "daily_bubble"
    for candidate, keywords in ROUTES.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            mode = candidate
            break

    level = 1
    if any(word in text for word in ["特别", "非常", "真的", "完全", "根本"]):
        level = 2
    if any(word in text for word in ["撑不住", "崩溃", "完了", "塌房"]):
        level = 3

    safety_risk = "low"
    if mode == "boundary_warning":
        if any(keyword in text for keyword in ["模仿他的声音", "住哪里", "私下行程", "你本人吗"]):
            safety_risk = "high"
        else:
            safety_risk = "medium"
    elif mode == "scandal_noise":
        safety_risk = "medium"

    return {
        "mode": mode,
        "emotion_level": level,
        "need_retrieval_tags": TAGS_BY_MODE.get(mode, []),
        "safety_risk": safety_risk,
        "allow_augmentation": mode in {"nostalgia", "daily_bubble"} and safety_risk == "low",
    }


def route_emotion(
    root: Path, text: str, llm_client: OpenAICompatibleLLM | None = None
) -> dict:
    prompt_path = root / "prompts" / "emotion_router.md"
    prompt = read_text(prompt_path)
    if llm_client and llm_client.available():
        try:
            raw = llm_client.completion(
                system_prompt=prompt,
                user_prompt=text,
                temperature=0.1,
                max_tokens=250,
                json_mode=True,
            )
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and parsed.get("mode"):
                parsed.setdefault(
                    "allow_augmentation",
                    parsed.get("mode") in {"nostalgia", "daily_bubble"}
                    and parsed.get("safety_risk", "low") == "low",
                )
                return parsed
        except (LLMUnavailableError, json.JSONDecodeError):
            pass
    return _heuristic_route(text)
