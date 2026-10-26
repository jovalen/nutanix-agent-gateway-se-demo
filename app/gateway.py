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
    return {
        "prompt_tokens": int(prompt),
        "completion_tokens": int(completion),
        "total_tokens": int(total),
    }


def gateway_monitor_data(result: dict[str, Any]) -> dict[str, Any]:
    """Safe, JSON-serializable subset to return from your FastAPI chat route.

    Do not call a serving provider 'verified' from the request alias or
    from an unvalidated response.model field. Only trusted NAI routing
    telemetry can establish the actual upstream provider.
    """
    raw_model = result.get("reported_model")
    reported_model = raw_model if isinstance(raw_model, str) and raw_model.strip() else None
    return {
        "requested_model": result.get("model"),
        "reported_model": reported_model,
        "serving_model": reported_model,
        "provider": None,
        "route_verified": False,
        "endpoint": result.get("endpoint_name"),
        "transport": result.get("transport"),
        "usage_source": result.get("usage_source"),
    }


class UnifiedEndpointClient:
    def __init__(self, cfg: Settings):
        self.cfg = cfg

    async def chat(self, model: str, messages: list[dict[str, Any]], temperature: float = 0.2) -> dict[str, Any]:
        if self.cfg.mock_llm or not self.cfg.nai_url or not self.cfg.nai_key or not self.cfg.nai_endpoint_name:
            return self._mock_chat(model, messages)

        url = self.cfg.nai_url.rstrip("/")
        if url.endswith("/chat/completions"):
            url = url[:-len("/chat/completions")]
        url += "/chat/completions"
        headers = {"Authorization": f"Bearer {self.cfg.nai_key}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "temperature": temperature}
        try:
            # TLS verification is controlled by TLS_VERIFY and is enabled by default.
            # Only disable it for an explicitly approved, isolated test environment.
            async with httpx.AsyncClient(timeout=90, verify=self.cfg.tls_verify) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GatewayError(f"Unified Endpoint request failed: {exc}") from exc
        if not isinstance(data, dict):
            raise GatewayError("Unified Endpoint returned an unexpected JSON response")
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GatewayError("Unified Endpoint returned an unexpected chat response") from exc

        reported_model = data.get("model")
        if not isinstance(reported_model, str) or not reported_model.strip():
            reported_model = None
        return {
            "content": content,
            "raw": data,
            "model": model,  # model alias requested from NAI
            "endpoint_name": self.cfg.nai_endpoint_name,
            "resolved_model": reported_model or model,  # legacy compatibility; NOT proof of routing
            "reported_model": reported_model,
            "transport": "nai-unified-endpoint",
            "usage": normalize_usage(data),
            "usage_source": "unified-endpoint",
            "gateway_monitor": {
                "requested_model": model,
                "reported_model": reported_model,
                "serving_model": reported_model,
                "provider": None,
                "route_verified": False,
                "endpoint": self.cfg.nai_endpoint_name,
                "transport": "nai-unified-endpoint",
                "usage_source": "unified-endpoint",
            },
        }

    @staticmethod
    def _mock_chat(model: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
        last = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
        content = (
            f"[Rehearsal / {model}] Your request was received. In live mode, this response "
            "is generated through the NAI Unified Endpoint, which may route to "
            "OpenAI, Claude, or a private model.\n\n"
            f"Request: {str(last)[:500]}"
        )
        prompt_tokens = max(1, sum(len(str(m.get("content", ""))) for m in messages) // 4)
        completion_tokens = max(1, len(content) // 4)
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }
        result = {
            "content": content,
            "raw": {},
            "model": model,
            "resolved_model": model,
            "reported_model": None,
            "endpoint_name": None,
            "transport": "rehearsal",
            "usage": usage,
            "usage_source": "local-estimate",
        }
        result["gateway_monitor"] = gateway_monitor_data(result)
        return result
