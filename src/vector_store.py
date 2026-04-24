from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .config_loader import read_json, write_json

try:
    import chromadb
except Exception:  # pragma: no cover
    chromadb = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None


RELIABILITY_WEIGHTS = {"S": 1.0, "A": 0.85, "B": 0.65, "C": 0.2}
MEMORY_TYPE_WEIGHTS = {"emotional": 1.0, "dynamic": 0.9, "core": 0.7, "augmented": 0.35}
FAN_TYPE_TAG_BOOSTS = {
    "career_fan": {"舞台", "认真", "努力", "事业", "采访"},
    "caregiver_fan": {"安慰", "温柔", "日常", "陪伴"},
    "comfort_fan": {"安慰", "轻松", "陪伴", "温柔"},
    "stage_fan": {"舞台", "表演", "出道夜", "高光", "夏天"},
    "archive_fan": {"回忆", "夏天", "灯光", "彩排", "档案"},
}


def _tokenize(text: str) -> list[str]:
    text = str(text or "").lower()
    ascii_words = re.findall(r"[a-z0-9_]+", text)
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", text)
    cjk_bigrams = ["".join(cjk_chars[index : index + 2]) for index in range(len(cjk_chars) - 1)]
    return ascii_words + cjk_chars + cjk_bigrams


def _counter_similarity(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    common = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


class Embedder:
    """Lazy sentence-transformers wrapper with graceful fallback state."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self.model = None
        self.error: str | None = None
        if SentenceTransformer is None:
            self.error = "sentence-transformers 未安装"
            return
        try:
            self.model = SentenceTransformer(model_name)
        except Exception as exc:
            self.error = str(exc)

    @property
    def available(self) -> bool:
        return self.model is not None

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not self.model:
            raise RuntimeError("Embedding model unavailable")
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def build_index(root: Path, memories: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a Chroma-first index and persist a JSON fallback copy."""
    vectors_dir = root / "data" / "vectors"
    vectors_dir.mkdir(parents=True, exist_ok=True)

    embedder = Embedder()
    backend = "token"
    embeddings: list[list[float]] = []

    if memories and embedder.available:
        embeddings = embedder.encode(
            [
                " ".join(
                    [
                        item.get("title", ""),
                        item.get("content", ""),
                        " ".join(item.get("tags", [])),
                        item.get("era", ""),
                        item.get("memory_type", ""),
                    ]
                )
                for item in memories
            ]
        )
        backend = "embedding-json"
        if chromadb is not None:
            try:
                client = chromadb.PersistentClient(path=str(vectors_dir / "chromadb"))
                try:
                    client.delete_collection("idol_skill")
                except Exception:
                    pass
                collection = client.create_collection("idol_skill")
                collection.add(
                    ids=[item["id"] for item in memories],
                    documents=[item.get("content", "") for item in memories],
                    metadatas=[
                        {
                            "title": item.get("title", ""),
                            "era": item.get("era", ""),
                            "reliability": item.get("reliability", "C"),
                            "tags": ",".join(item.get("tags", [])),
                            "memory_type": item.get("memory_type", "dynamic"),
                        }
                        for item in memories
                    ],
                    embeddings=embeddings,
                )
                backend = "chromadb"
            except Exception:
                backend = "embedding-json"

    token_vectors = [
        Counter(
            _tokenize(
                " ".join(
                    [
                        item.get("title", ""),
                        item.get("content", ""),
                        " ".join(item.get("tags", [])),
                        item.get("era", ""),
                        item.get("memory_type", ""),
                    ]
                )
            )
        )
        for item in memories
    ]

    payload = {
        "backend": backend,
        "model_name": embedder.model_name if embedder.available else None,
        "embedder_error": embedder.error,
        "items": [
            {
                "memory": item,
                "embedding": embeddings[index] if embeddings else None,
                "token_vector": dict(token_vectors[index]),
            }
            for index, item in enumerate(memories)
        ],
    }
    write_json(vectors_dir / "index.json", payload)
    return {"backend": backend, "count": len(memories), "embedder_error": embedder.error}


def _preferred_era(query: str, route: dict[str, Any] | None) -> str | None:
    lowered = query.lower()
    if "出道" in lowered:
        return "出道期"
    if "上升" in lowered:
        return "上升期"
    if route and route.get("mode") == "nostalgia":
        return "高光期"
    return None


def top_retrieval_score(items: list[dict[str, Any]]) -> float:
    return max((item.get("score", 0.0) for item in items), default=0.0)


def retrieve_memories(
    root: Path,
    query: str,
    *,
    route: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None,
    top_k: int = 6,
    min_score: float = 0.45,
    allowed_memory_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Retrieve memories using semantic similarity, tags, era, reliability, and memory_type."""
    index_payload = read_json(root / "data" / "vectors" / "index.json", default={})
    items = index_payload.get("items") or []
    if not items:
        return []

    preferred_era = _preferred_era(query, route)
    route_tags = set(route.get("need_retrieval_tags", [])) if route else set()
    expanded_query = f"{query} {' '.join(route_tags)}".strip()
    query_counter = Counter(_tokenize(expanded_query))
    allowed_types = set(allowed_memory_types or [])
    fan_type = (state or {}).get("fan_type")
    fan_type_tags = FAN_TYPE_TAG_BOOSTS.get(fan_type or "", set())

    query_embedding = None
    if any(item.get("embedding") for item in items):
        embedder = Embedder(index_payload.get("model_name") or "all-MiniLM-L6-v2")
        if embedder.available:
            try:
                query_embedding = embedder.encode([query])[0]
            except Exception:
                query_embedding = None

    scored: list[dict[str, Any]] = []
    for item in items:
        memory = item.get("memory", {})
        if allowed_types and memory.get("memory_type") not in allowed_types:
            continue
        token_counter = Counter(item.get("token_vector") or {})
        semantic_score = _counter_similarity(query_counter, token_counter)
        if query_embedding and item.get("embedding"):
            semantic_score = max(semantic_score, _cosine_similarity(query_embedding, item["embedding"]))

        memory_tags = set(memory.get("tags", []))
        tag_overlap = len(route_tags & memory_tags)
        tag_score = 0.0 if not route_tags else max(float(tag_overlap > 0), tag_overlap / max(len(route_tags), 1))
        fan_score = 1.0 if memory_tags & fan_type_tags else 0.0
        era_score = 1.0 if preferred_era and memory.get("era") == preferred_era else 0.0
        reliability = RELIABILITY_WEIGHTS.get(memory.get("reliability", "C"), 0.2)
        memory_type = MEMORY_TYPE_WEIGHTS.get(memory.get("memory_type", "dynamic"), 0.5)
        final_score = (
            semantic_score * 0.36
            + tag_score * 0.2
            + era_score * 0.1
            + reliability * 0.15
            + memory_type * 0.15
            + fan_score * 0.04
        )
        scored.append({**memory, "score": round(final_score, 4)})

    scored.sort(key=lambda entry: entry.get("score", 0), reverse=True)
    filtered = [item for item in scored if item.get("score", 0) >= min_score][:top_k]
    if filtered:
        return filtered
    relaxed_floor = min_score * 0.6
    return [item for item in scored if item.get("score", 0) >= relaxed_floor][: max(1, min(top_k, 2))]
