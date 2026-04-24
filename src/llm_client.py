from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


class LLMUnavailableError(RuntimeError):
    pass


@dataclass
class OpenAICompatibleLLM:
    api_key: str | None
    base_url: str
    model: str
    timeout: int = 60

    @classmethod
    def from_env(cls) -> "OpenAICompatibleLLM":
        api_key = (
            os.getenv("IDOL_SKILL_API_KEY")
            or os.getenv("ZIDAN_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        base_url = (
            os.getenv("IDOL_SKILL_BASE_URL")
            or os.getenv("ZIDAN_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        )
        model = (
            os.getenv("IDOL_SKILL_MODEL")
            or os.getenv("ZIDAN_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "gpt-4o-mini"
        )
        return cls(api_key=api_key, base_url=base_url, model=model)

    def available(self) -> bool:
        return bool(self.api_key and requests is not None)

    def completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
        max_tokens: int = 700,
        json_mode: bool = False,
    ) -> str:
        if requests is None:
            raise LLMUnavailableError("缺少 requests 依赖，无法调用 OpenAI-compatible API。")
        if not self.api_key:
            raise LLMUnavailableError(
                "未检测到 API key。请设置 IDOL_SKILL_API_KEY / OPENAI_API_KEY，"
                "可选设置 IDOL_SKILL_BASE_URL / OPENAI_BASE_URL，或直接使用本地 fallback 模式。"
            )

        endpoint = self.base_url.rstrip("/") + "/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            raise LLMUnavailableError(
                f"LLM 调用失败：HTTP {response.status_code} - {response.text[:200]}"
            )
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # pragma: no cover
            raise LLMUnavailableError(f"无法解析 LLM 返回结果：{exc}") from exc


def build_default_client() -> OpenAICompatibleLLM:
    return OpenAICompatibleLLM.from_env()
