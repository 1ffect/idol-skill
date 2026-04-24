from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from .archive_preview import save_preview_markdown
from .config_loader import read_text, write_json
from .llm_client import LLMUnavailableError, OpenAICompatibleLLM

SOURCE_PATTERNS = {
    "weibo": ["微博", "超话", "转发", "置顶"],
    "interview": ["采访", "访谈", "专访", "媒体"],
    "bubble": ["bubble", "泡泡", "fromm"],
    "weverse": ["weverse", "wvs", "社区"],
    "web_augmented": ["web_augmented", "公开整理", "repo 整理"],
    "subtitle": ["字幕", "cut", "中字", "机翻", "台词", "舞台", "直播"],
    "fan_description": ["我觉得", "我记得", "在我印象里", "像是", "粉丝"],
}

RISK_PATTERNS = {
    "private_info": ["住址", "身份证", "手机号", "私下住", "家庭地址"],
    "schedule_leak": ["私生", "航班", "酒店", "行程", "蹲点"],
    "relationship_rumor": ["恋情实锤", "地下恋", "嫂子", "绯闻实锤"],
    "smear_detail": ["黑料", "塌房细节", "偷拍视频", "偷拍视频"],
    "aggressive_language": ["去死", "骂死", "废物", "滚出"],
    "sexual_content": ["性幻想", "做爱", "床上", "裸体"],
}

TAG_KEYWORDS = {
    "安慰": ["辛苦", "累", "撑住", "安慰", "没事", "抱抱", "休息"],
    "舞台": ["舞台", "live", "直拍", "唱", "跳", "镜头", "返场"],
    "温柔": ["温柔", "轻轻", "慢慢", "柔和"],
    "认真": ["认真", "练习", "努力", "排练", "专注"],
    "倔强": ["倔强", "不服输", "咬牙", "撑着"],
    "轻松": ["聊天", "碎碎念", "日常", "在吗", "轻松"],
    "回忆": ["夏天", "以前", "那年", "想回去", "怀念"],
    "边界": ["不是本人", "隐私", "声音", "住哪里", "爱我吗"],
}

TONE_KEYWORDS = {
    "温柔": ["辛苦", "慢慢", "别怕", "没事", "温柔"],
    "倔强": ["撑住", "咬牙", "不服输", "扛住"],
    "克制": ["克制", "稳住", "分寸", "边界"],
    "认真": ["练习", "准备", "认真", "专注"],
    "轻松": ["哈哈", "聊天", "轻松", "今天吃了"],
}

ERA_PATTERNS = {
    "出道期": ["出道", "新人", "练习生", "第一次舞台"],
    "上升期": ["回归", "涨粉", "打歌", "上升", "被看到"],
    "高光期": ["高光", "封神", "爆发", "代表作", "拿奖", "夏天", "舞台"],
    "用户记忆": ["我觉得", "我记得", "在我心里", "对我来说", "粉丝"],
}

RELIABILITY_BY_SOURCE = {
    "interview": "S",
    "weibo": "A",
    "weverse": "A",
    "bubble": "A",
    "subtitle": "A",
    "fan_description": "B",
    "unknown": "C",
}


def _normalize_text(raw_text: str) -> str:
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_into_chunks(raw_text: str, max_chars: int = 320) -> list[str]:
    cleaned = _normalize_text(raw_text)
    if not cleaned:
        return []

    raw_parts = [part.strip() for part in cleaned.split("\n\n") if part.strip()]
    chunks: list[str] = []
    for part in raw_parts:
        if len(part) <= max_chars:
            chunks.append(part)
            continue
        sentences = re.split(r"(?<=[。！？!?])", part)
        buffer = ""
        for sentence in sentences:
            candidate = f"{buffer}{sentence}".strip()
            if len(candidate) <= max_chars:
                buffer = candidate
                continue
            if buffer:
                chunks.append(buffer.strip())
            buffer = sentence.strip()
        if buffer:
            chunks.append(buffer.strip())
    return [chunk for chunk in chunks if chunk]


def detect_source_type(text: str) -> str:
    lower = text.lower()
    for source_type, keywords in SOURCE_PATTERNS.items():
        if any(keyword.lower() in lower for keyword in keywords):
            return source_type
    return "unknown"


def detect_era(text: str, source_type: str) -> str:
    lower = text.lower()
    for era, keywords in ERA_PATTERNS.items():
        if any(keyword.lower() in lower for keyword in keywords):
            return era
    if source_type == "fan_description":
        return "用户记忆"
    if "2020" in lower or "summer" in lower:
        return "高光期"
    return "unknown"


def detect_tags(text: str) -> list[str]:
    tags = [tag for tag, keywords in TAG_KEYWORDS.items() if any(word in text for word in keywords)]
    return tags[:6]


def detect_tone(text: str) -> str:
    for tone, keywords in TONE_KEYWORDS.items():
        if any(word in text for word in keywords):
            return tone
    return "认真"


def detect_risk_flags(text: str) -> list[str]:
    flags = [flag for flag, keywords in RISK_PATTERNS.items() if any(word in text for word in keywords)]
    return flags


def decide_reliability(source_type: str, text: str) -> str:
    if any(word in text for word in ["营销号", "搬运", "听说", "疑似", "争议"]):
        return "C"
    return RELIABILITY_BY_SOURCE.get(source_type, "C")


def build_title(text: str, source_type: str, era: str) -> str:
    first_sentence = re.split(r"[。！？!?]", text)[0].strip()
    if len(first_sentence) > 18:
        first_sentence = first_sentence[:18]
    if not first_sentence:
        first_sentence = "自动生成的记忆"
    prefix = {
        "interview": "采访",
        "weibo": "微博",
        "bubble": "泡泡",
        "weverse": "社区",
        "subtitle": "字幕",
        "fan_description": "粉丝记忆",
    }.get(source_type, "档案")
    return f"{prefix}·{era}·{first_sentence}"


def heuristic_record(text: str) -> dict[str, Any]:
    source_type = detect_source_type(text)
    era = detect_era(text, source_type)
    tags = detect_tags(text)
    risk_flags = detect_risk_flags(text)
    reliability = decide_reliability(source_type, text)
    should_include = not risk_flags and (reliability in {"S", "A", "B"}) and bool(tags or len(text) > 40)
    return {
        "id": f"auto-generated-{uuid.uuid4().hex[:12]}",
        "title": build_title(text, source_type, era),
        "content": text.strip(),
        "source_type": source_type,
        "era": era,
        "tags": tags,
        "tone": detect_tone(text),
        "reliability": reliability,
        "risk_flags": risk_flags,
        "should_include": should_include,
        "origin": "user_provided",
        "memory_type": "dynamic",
    }


def _llm_parse_json(raw_output: str) -> list[dict[str, Any]] | None:
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        parsed = parsed.get("items") or parsed.get("records")
    if not isinstance(parsed, list):
        return None
    result: list[dict[str, Any]] = []
    for item in parsed:
        if isinstance(item, dict):
            result.append(item)
    return result or None


def llm_structured_ingestion(
    root: Path, raw_text: str, llm_client: OpenAICompatibleLLM
) -> list[dict[str, Any]] | None:
    prompt = read_text(root / "prompts" / "ingestion_cleaner.md")
    try:
        raw_output = llm_client.completion(
            system_prompt=prompt,
            user_prompt=raw_text,
            temperature=0.2,
            max_tokens=1800,
        )
    except LLMUnavailableError:
        return None
    return _llm_parse_json(raw_output)


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    base = heuristic_record(str(record.get("content", "")))
    merged = {**base, **record}
    merged["id"] = merged.get("id") or base["id"]
    merged["title"] = merged.get("title") or base["title"]
    merged["source_type"] = merged.get("source_type") or base["source_type"]
    merged["era"] = merged.get("era") or base["era"]
    merged["tags"] = list(merged.get("tags") or base["tags"])
    merged["tone"] = merged.get("tone") or base["tone"]
    merged["reliability"] = merged.get("reliability") or base["reliability"]
    merged["risk_flags"] = list(merged.get("risk_flags") or base["risk_flags"])
    merged["origin"] = merged.get("origin") or "user_provided"
    merged["memory_type"] = merged.get("memory_type") or "dynamic"
    if merged["risk_flags"]:
        merged["should_include"] = False
    elif "should_include" not in merged:
        merged["should_include"] = base["should_include"]
    return merged


def auto_ingest(
    root: Path,
    raw_text: str,
    llm_client: OpenAICompatibleLLM | None = None,
) -> tuple[list[dict[str, Any]], Path]:
    raw_text = _normalize_text(raw_text)
    records: list[dict[str, Any]] = []

    if llm_client and llm_client.available():
        llm_records = llm_structured_ingestion(root, raw_text, llm_client)
        if llm_records:
            records = [normalize_record(item) for item in llm_records if item.get("content")]

    if not records:
        records = [heuristic_record(chunk) for chunk in split_into_chunks(raw_text)]

    pending_path = root / "data" / "pending" / "pending_archive.json"
    write_json(pending_path, records)
    preview_path = save_preview_markdown(root, records)
    return records, preview_path
