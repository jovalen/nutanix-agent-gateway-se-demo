from typing import Any
import httpx
from .settings import Settings


class GatewayError(RuntimeError):
    pass


def normalize_usage(data: dict[str, Any]) -> dict[str, int]:
    usage = data.get("usage") or {}
    prompt = usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0
    completion = usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0
    total = usage.get("total_tokens", prompt + completion) or 0
    return {"prompt_tokens": int(prompt), "completion_tokens": int(completion), "total_tokens": int(total)}


class UnifiedEndpointClient:
    def __init__(self, cfg: Settings):
        self.cfg = cfg

    async def chat(self, model: str, messages: list[dict[str, Any]], temperature: float = 0.2) -> dict[str, Any]:
        if self.cfg.mock_llm or not self.cfg.nai_url or not self.cfg.nai_key:
            return self._mock_chat(model, messages)

        url = self.cfg.nai_url.rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {self.cfg.nai_key}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "temperature": temperature}
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise GatewayError(f"Unified Endpoint request failed: {exc}") from exc
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GatewayError("Unified Endpoint returned an unexpected chat response") from exc
        return {
            "content": content,
            "raw": data,
            "model": model,
            "transport": "nai-unified-endpoint",
            "usage": normalize_usage(data),
            "usage_source": "unified-endpoint",
        }

    @staticmethod
    def _mock_chat(model: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
        last = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
        content = (
            f"[MOCK / {model}] He recibido la solicitud. En modo live, este texto se genera "
            "a través del Unified Endpoint de NAI, que puede enrutarla a OpenAI, Claude o un modelo privado.\n\n"
            f"Solicitud: {last[:500]}"
        )
        prompt_tokens = max(1, sum(len(str(m.get("content", ""))) for m in messages) // 4)
        completion_tokens = max(1, len(content) // 4)
        usage = {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "total_tokens": prompt_tokens + completion_tokens}
        return {"content": content, "raw": {}, "model": model, "transport": "mock", "usage": usage, "usage_source": "local-estimate"}
