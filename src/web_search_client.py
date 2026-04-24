from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from typing import Any

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


ALLOWED_TERMS = ["舞台", "彩排", "采访", "花絮", "直播", "互动", "表演", "出道夜", "后台"]
BLOCKED_TERMS = ["恋情", "绯闻", "爆料", "黑料", "争议", "丑闻", "塌房", "吸毒", "出轨", "私生", "行程", "住址", "酒店"]
ALLOWED_SOURCE_MARKERS = ["官方", "official", "weverse", "微博", "interview", "字幕", "repo"]
DISALLOWED_SOURCE_MARKERS = ["营销号", "论坛", "匿名", "爆料", "黑称", "私生", "付费", "unverified"]


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    publication_date: str
    source: str
    unsafe_time_unverified: bool = False


def build_timeboxed_query(name: str, era_start: str, era_end: str, allowed_terms: list[str]) -> str:
    """Build a safe search query that only includes allowed public-performance terms."""
    filtered_terms = [term for term in allowed_terms if term in ALLOWED_TERMS]
    joined_terms = " OR ".join(filtered_terms or ALLOWED_TERMS[:4])
    blocked = " ".join(f"-{term}" for term in BLOCKED_TERMS)
    return f"{name} ({joined_terms}) {blocked} {era_start} {era_end}".strip()


def _within_range(publication_date: str, start_date: str, end_date: str) -> bool:
    try:
        published = date.fromisoformat(publication_date)
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        return False
    return start <= published <= end


class WebSearchClient:
    """Optional web search adapter. By default it is dormant until the user enables web access."""

    def __init__(self) -> None:
        self.api_key = os.getenv("IDOL_SKILL_SEARCH_API_KEY") or os.getenv("IDOL_MEMORY_SEARCH_API_KEY")
        self.api_url = os.getenv("IDOL_SKILL_SEARCH_API_URL") or os.getenv("IDOL_MEMORY_SEARCH_API_URL")
        self.supports_native_time = (
            os.getenv("IDOL_SKILL_SEARCH_SUPPORTS_NATIVE_TIME")
            or os.getenv("IDOL_MEMORY_SEARCH_SUPPORTS_NATIVE_TIME")
            or "false"
        ).lower() == "true"

    def configured(self) -> bool:
        return bool(self.api_key and self.api_url and requests is not None)

    def search_timeboxed(self, query: str, start_date: str, end_date: str) -> list[SearchResult]:
        """Use native time parameters when supported; otherwise return only unsafe_time_unverified results."""
        if not self.configured():
            return []

        params: dict[str, Any] = {"q": query}
        if self.supports_native_time:
            params["start_date"] = start_date
            params["end_date"] = end_date

        response = requests.get(
            self.api_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        raw_items = payload.get("results") if isinstance(payload, dict) else payload
        results: list[SearchResult] = []
        for raw in raw_items or []:
            publication_date = str(raw.get("publication_date") or "").strip()
            if not publication_date:
                continue
            if not _within_range(publication_date, start_date, end_date):
                continue
            source = str(raw.get("source", ""))
            lowered_source = source.lower()
            if any(marker in lowered_source for marker in DISALLOWED_SOURCE_MARKERS):
                continue
            if source and not any(marker in lowered_source for marker in ALLOWED_SOURCE_MARKERS):
                continue
            results.append(
                SearchResult(
                    title=str(raw.get("title", "")),
                    url=str(raw.get("url", "")),
                    snippet=str(raw.get("snippet", "")),
                    publication_date=publication_date,
                    source=source,
                    unsafe_time_unverified=not self.supports_native_time,
                )
            )
        if not self.supports_native_time:
            return [result for result in results if not result.unsafe_time_unverified]
        return results


def search_timeboxed(query: str, start_date: str, end_date: str) -> list[SearchResult]:
    client = WebSearchClient()
    return client.search_timeboxed(query, start_date, end_date)
