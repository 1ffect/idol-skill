from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .config_loader import read_text

TRIGGERS = [
    "不像",
    "太油了",
    "太 AI 了",
    "Ta 不会这么说",
    "他不会这么说",
    "少说教",
    "更像 2020",
    "不要恋爱脑",
    "更克制一点",
    "太霸总了",
    "太像客服了",
]


@dataclass
class CorrectionEntry:
    version: int
    trigger: str
    problem: str
    new_rule: str
    confidence: str
    example_before: str
    example_after: str


def is_ooc_feedback(text: str) -> bool:
    return any(trigger.lower() in text.lower() for trigger in TRIGGERS)


def _next_version(corrections_text: str) -> int:
    versions = [int(match) for match in re.findall(r"## Correction v(\d+)", corrections_text)]
    return (max(versions) + 1) if versions else 1


def _infer_rule(trigger: str) -> tuple[str, str, str, str]:
    mappings = [
        ("太油", "回复过于亲密或用力", "减少暧昧和情绪堆叠，改为克制、短句、低饱和表达。", "High"),
        ("恋爱脑", "回复越过粉丝陪伴边界", "禁止恋爱脑口吻，不说独占、不说爱、不制造私密关系。", "High"),
        ("太 ai", "回复有明显模板味或抽象腔", "多用具体动作和生活化表达，少用抽象总结。", "Medium"),
        ("少说教", "回复像在教育用户", "减少指导口吻，先陪伴，再给最小行动建议。", "High"),
        ("更像 2020", "时代感偏差", "优先贴近用户记忆中的高光时期语气与意象。", "Medium"),
        ("更克制", "情绪浓度偏高", "降低语气强度，避免大词和过度抒情。", "High"),
        ("太霸总", "回复出现占有感或强制感", "去掉霸总口吻与命令式占有表达，保留克制撑腰感。", "High"),
        ("客服", "回复像模板安抚或客服话术", "取消总结和解释，改成更短、更生活化的句子。", "High"),
        ("不像", "人格和记忆不贴脸", "优先使用已封存记忆中的表达方式，不自行发挥太多。", "Medium"),
    ]
    lowered = trigger.lower()
    for keyword, problem, rule, confidence in mappings:
        if keyword in lowered:
            return problem, rule, confidence, "今天先停一下。"
    return (
        "表达与用户记忆中的人格不一致",
        "下一次回复更贴近高光时期、短句、克制、具体动作导向。",
        "Medium",
        "今天先缓一缓。",
    )


def build_entry(text: str) -> CorrectionEntry:
    problem, new_rule, confidence, example_after = _infer_rule(text)
    return CorrectionEntry(
        version=0,
        trigger=text,
        problem=problem,
        new_rule=new_rule,
        confidence=confidence,
        example_before="过度抒情、过度亲密、太像模板安慰。",
        example_after=example_after,
    )


def record_correction(root: Path, trigger_text: str) -> CorrectionEntry:
    path = root / "memories" / "corrections.md"
    existing = read_text(path, "# Corrections\n\n")
    entry = build_entry(trigger_text)
    entry.version = _next_version(existing)
    block = (
        f"\n## Correction v{entry.version}\n\n"
        f"- Created: {date.today().isoformat()}\n"
        f"- Trigger: {entry.trigger}\n"
        f"- Problem: {entry.problem}\n"
        f"- New Rule: {entry.new_rule}\n"
        f"- Confidence: {entry.confidence}\n"
        f"- Example Before: {entry.example_before}\n"
        f"- Example After: {entry.example_after}\n"
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(block)
    return entry
