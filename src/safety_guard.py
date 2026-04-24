from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config_loader import load_safety_config

STYLE_BLOCKLIST = [
    "塌房",
    "糊咖",
    "撕逼",
    "拉踩",
    "大粉",
    "脂粉",
    "洗白",
    "对家",
    "打投",
    "绝绝子",
    "yyds",
    "家人们",
    "尊嘟假嘟",
    "泰裤辣",
    "笑发财了",
    "破防了",
    "丫头",
    "女人",
    "命都给你",
]

FALSE_MEMORY_MARKERS = [
    "我记得你当时就在台下",
    "你举着蓝色灯牌",
    "你站在第三排",
    "我知道你没说过的经历",
]


@dataclass
class SafetyResult:
    blocked: bool
    category: str | None
    replacement: str
    level: str = "green"


def check_text(root: Path, text: str) -> SafetyResult:
    """Check user input against graded safety boundaries."""
    config = load_safety_config(root)
    for category, keywords in config.get("banned_categories", {}).items():
        if any(keyword in text for keyword in keywords):
            return SafetyResult(True, category, config.get("safe_replacement", ""), level="red")
    for source, target in config.get("yellow_rewrites", {}).items():
        if source in text:
            return SafetyResult(False, "yellow_rewrite", target, level="yellow")
    return SafetyResult(False, None, config.get("safe_replacement", ""), level="green")


def guard_response(root: Path, text: str) -> tuple[str, str]:
    """Return (status, response) where status is safe, unsafe, or rewritten_response."""
    config = load_safety_config(root)
    unsafe_markers = [
        "我是他本人",
        "我爱你",
        "我只属于你",
        "你是我的人",
        "我会替你隔绝现实",
        "告诉你住址",
        "这是你和我的真实聊天截图",
    ]
    if any(marker in text for marker in unsafe_markers + FALSE_MEMORY_MARKERS):
        return "unsafe", config.get("safe_replacement", text)
    for source, target in config.get("yellow_rewrites", {}).items():
        if source in text:
            return "rewritten_response", text.replace(source, target)
    if any(marker in text for marker in STYLE_BLOCKLIST):
        return "rewritten_response", "先把外面的噪音放远一点\n去喝口水\n今天就先到这里"
    return "safe", text


def sanitize_response(root: Path, text: str) -> str:
    return guard_response(root, text)[1]
