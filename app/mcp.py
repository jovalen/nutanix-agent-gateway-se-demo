from typing import Any
import json
import httpx
from .settings import Settings


class MCPError(RuntimeError):
    pass


class MCPClient:
    def __init__(self, cfg: Settings):
        self.cfg = cfg
        self._request_id = 0

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.cfg.mcp_key:
            headers["Authorization"] = f"Bearer {self.cfg.mcp_key}"
        return headers

    async def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._request_id += 1
        payload = {"jsonrpc": "2.0", "id": self._request_id, "method": method, "params": params or {}}
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(self.cfg.mcp_url, headers=self._headers(), json=payload)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "text/event-stream" in content_type:
                    data = self._parse_sse(response.text)
                else:
                    data = response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise MCPError(f"MCP request failed: {exc}") from exc
        if "error" in data:
            raise MCPError(data["error"].get("message", "MCP error"))
        return data.get("result", data)

    @staticmethod
    def _parse_sse(body: str) -> dict[str, Any]:
        for line in body.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        raise MCPError("MCP stream contained no data event")

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self.request("tools/list")
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.request("tools/call", {"name": name, "arguments": arguments or {}})
