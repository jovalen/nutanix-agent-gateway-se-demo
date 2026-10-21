from typing import Any
import json
import httpx
from .settings import Settings


class MCPError(RuntimeError):
    pass


class MCPClient:
    """Minimal Streamable HTTP MCP client for the NAI MCP Connector."""

    def __init__(self, cfg: Settings):
        self.cfg = cfg
        self._request_id = 0
        self._session_id: str | None = None
        self._initialized = False

    def _headers(self, include_protocol: bool = True) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        if include_protocol and self.cfg.mcp_protocol_version:
            headers["MCP-Protocol-Version"] = self.cfg.mcp_protocol_version
        if self.cfg.mcp_key:
            headers["Authorization"] = f"Bearer {self.cfg.mcp_key}"
        return headers

    @staticmethod
    def _parse_response(response: httpx.Response) -> dict[str, Any]:
        if response.status_code in {202, 204} or not response.text.strip():
            return {}
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            for line in response.text.splitlines():
                if line.startswith("data:"):
                    value = line[5:].strip()
                    if value:
                        return json.loads(value)
            raise MCPError("MCP stream contained no data event")
        return response.json()

    async def _post(self, payload: dict[str, Any], include_protocol: bool = True) -> tuple[dict[str, Any], httpx.Response]:
        try:
            async with httpx.AsyncClient(timeout=60, verify=self.cfg.tls_verify) as client:
                response = await client.post(self.cfg.mcp_url, headers=self._headers(include_protocol), json=payload)
                if response.is_error:
                    detail = response.text.strip().replace("\n", " ")[:1000]
                    raise MCPError(
                        f"MCP HTTP {response.status_code} en {self.cfg.mcp_url}"
                        + (f": {detail}" if detail else "")
                    )
                return self._parse_response(response), response
        except MCPError:
            raise
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise MCPError(f"MCP request failed: {exc}") from exc

    async def _initialize(self) -> None:
        if self._initialized:
            return
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": self.cfg.mcp_protocol_version,
                "capabilities": {},
                "clientInfo": {
                    "name": "seguroauto-agent-gateway-demo",
                    "version": "0.2.2",
                },
            },
        }
        result, response = await self._post(payload, include_protocol=False)
        if "error" in result:
            raise MCPError(result["error"].get("message", "MCP initialize failed"))
        self._session_id = response.headers.get("Mcp-Session-Id")
        server_version = result.get("result", {}).get("protocolVersion")
        if server_version:
            # Use the version negotiated by the server for subsequent calls.
            self.cfg.mcp_protocol_version = server_version
        self._initialized = True

        # MCP initialization completion is a JSON-RPC notification: no id and
        # usually a 202/204 response. Some gateways return an empty JSON body.
        await self._post({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        })

    async def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        await self._initialize()
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }
        data, _ = await self._post(payload)
        if "error" in data:
            raise MCPError(data["error"].get("message", "MCP error"))
        return data.get("result", data)

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self.request("tools/list")
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.request("tools/call", {"name": name, "arguments": arguments or {}})
