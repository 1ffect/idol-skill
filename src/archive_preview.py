from __future__ import annotations

from pathlib import Path

from .config_loader import read_text

SOURCE_LABELS = {
    "weibo": "公开微博",
    "interview": "公开采访",
    "bubble": "泡泡摘录",
    "weverse": "Weverse 摘录",
    "web_augmented": "安全联网补充",
    "subtitle": "字幕文本",
    "fan_description": "粉丝主观描述",
    "unknown": "未知来源",
}

RISK_LABELS = {
    "private_info": "疑似未公开隐私",
    "schedule_leak": "疑似私生或行程泄露",
    "relationship_rumor": "疑似恋情实锤化表达",
    "smear_detail": "疑似黑料或偷拍视频细节",
    "aggressive_language": "攻击性语言",
    "sexual_content": "性化内容",
}


def render_preview_card(root: Path, item: dict) -> str:
    template_path = root / "templates" / "memory_card_template.md"
    template = read_text(
        template_path,
        (
            "# 档案预览卡片\n\n"
            "## 记忆标题\n{title}\n\n"
            "## 来源类型\n{source_type}\n\n"
            "## 判断时期\n{era}\n\n"
            "## 情绪标签\n{tags}\n\n"
            "## 可信度\n{reliability}\n\n"
            "## 提取内容\n“{content}”\n\n"
            "## 风险提示\n{risk_note}\n\n"
            "## 建议\n{recommendation}\n"
        ),
    )
    risk_flags = item.get("risk_flags") or []
    risk_note = "未发现明显风险。" if not risk_flags else " / ".join(
        RISK_LABELS.get(flag, flag) for flag in risk_flags
    )
    if risk_flags:
        recommendation = "建议丢弃。"
    elif item.get("should_include"):
        recommendation = "建议封存。"
    else:
        recommendation = "需要人工修改。"
    safe_content = str(item.get("content", "")).replace("\n", " ").strip()[:160]
    return template.format(
        title=item.get("title", "未命名记忆"),
        source_type=SOURCE_LABELS.get(item.get("source_type", "unknown"), item.get("source_type", "unknown")),
        era=item.get("era", "unknown"),
        tags=" / ".join(item.get("tags", [])) or "无",
        reliability=item.get("reliability", "C"),
        content=safe_content,
        risk_note=risk_note,
        recommendation=recommendation,
    )


def build_preview_markdown(root: Path, items: list[dict]) -> str:
    blocks = [render_preview_card(root, item) for item in items]
    return "\n\n---\n\n".join(blocks) if blocks else "# 档案预览卡片\n\n暂无待确认内容。\n"


def save_preview_markdown(root: Path, items: list[dict]) -> Path:
    output_path = root / "data" / "pending" / "archive_preview.md"
    output_path.write_text(build_preview_markdown(root, items), encoding="utf-8")
    return output_path
