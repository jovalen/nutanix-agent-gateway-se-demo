"""MCP Streamable HTTP client for local rehearsal and NAI MCP Connectors.

NAI can publish tools as ``<server-id>__<tool-name>``. The application uses
short logical names; this module resolves them from the actual tools/list
response, without hard-coding a server name or bypassing connector allowlists.
"""
from typing import Any
import json

import httpx

from .settings import Settings


class MCPError(RuntimeError):
    pass


class MCPToolDenied(MCPError):
    """A tools/call response rejected by MCP policy.

    NAI MCP Connectors may return a JSON-RPC error for a policy denial, while
    an MCP server may return the standard ``result.isError`` shape. The client
    normalizes the former so the application can present both consistently.
    """

    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


class MCPClient:
    """MCP Streamable HTTP client using discovered, connector-scoped tool names."""

    def __init__(self, cfg: Settings):
        self.cfg = cfg
        self._request_id = 0
        self._session_id: str | None = None
        self._initialized = False
        # friendly tool name -> exact name returned by tools/list
        self._tool_aliases: dict[str, str] = {}

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
        if "text/event-stream" in response.headers.get("content-type", ""):
            for line in response.text.splitlines():
                if line.startswith("data:"):
                    value = line[5:].strip()
                    if not value:
                        continue
                    event = json.loads(value)
                    if isinstance(event, dict) and ("result" in event or "error" in event):
                        return event
            raise MCPError("MCP stream contained no JSON-RPC result event")
        return response.json()

    async def _post(
        self,
        payload: dict[str, Any],
        include_protocol: bool = True,
    ) -> tuple[dict[str, Any], httpx.Response]:
        try:
            async with httpx.AsyncClient(timeout=60, verify=self.cfg.tls_verify) as client:
                response = await client.post(
                    self.cfg.mcp_url,
                    headers=self._headers(include_protocol),
                    json=payload,
                )
                if response.is_error:
                    detail = response.text.strip().replace("\n", " ")[:1000]
                    message = f"MCP HTTP {response.status_code}"
                    if detail:
                        message += f": {detail}"
                    # A Connector may surface a policy decision as HTTP 403
                    # rather than a JSON-RPC error object.
                    if payload.get("method") == "tools/call" and response.status_code == 403:
                        raise MCPToolDenied(message, response.status_code)
                    raise MCPError(message)
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
                "clientInfo": {"name": "seguroauto-agent-gateway-demo", "version": "0.3.0"},
            },
        }
        result, response = await self._post(payload)
        if "error" in result:
            raise MCPError(result["error"].get("message", "MCP initialize failed"))
        self._session_id = response.headers.get("Mcp-Session-Id")
        server_version = result.get("result", {}).get("protocolVersion")
        if server_version:
            self.cfg.mcp_protocol_version = server_version
        self._initialized = True
        await self._post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    async def request(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
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
            error = data["error"] or {}
            message = error.get("message", "MCP error")
            if method == "tools/call":
                raise MCPToolDenied(message, error.get("code"))
            raise MCPError(message)
        return data.get("result", data)

    @staticmethod
    def _friendly_name(real_name: str) -> str:
        # For NAI names, preserve everything after the first separator.
        # Never manufacture a server prefix; use the returned real name to call.
        return real_name.split("__", 1)[1] if "__" in real_name else real_name

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self.request("tools/list")
        tools = result.get("tools", [])
        if not isinstance(tools, list):
            raise MCPError("Invalid MCP tools/list response")

        aliases: dict[str, str] = {}
        normalized: list[dict[str, Any]] = []
        for tool in tools:
            if not isinstance(tool, dict) or not isinstance(tool.get("name"), str):
                raise MCPError("Invalid tool entry in MCP tools/list response")
            real_name = tool["name"]
            friendly_name = self._friendly_name(real_name)
            if not friendly_name:
                raise MCPError(f"Invalid MCP tool name: {real_name!r}")
            if friendly_name in aliases and aliases[friendly_name] != real_name:
                raise MCPError(
                    f"Ambiguous MCP tool '{friendly_name}' exposed by multiple servers; "
                    "use a connector with unique tool names."
                )
            aliases[friendly_name] = real_name
            item = dict(tool)
            item["name"] = friendly_name
            normalized.append(item)

        # Atomic replacement makes connector allowlist changes take effect.
        self._tool_aliases = aliases
        return normalized

    async def call_tool(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        # Resolve against the connector's CURRENT allowlist, including direct calls.
        await self.list_tools()
        real_name = self._tool_aliases.get(name)
        if real_name is None:
            # Allow the exact published name only if discovered.
            if name in self._tool_aliases.values():
                real_name = name
            else:
                raise MCPError(f"Tool '{name}' is not exposed by the MCP connector")
        try:
            return await self.request(
                "tools/call",
                {"name": real_name, "arguments": arguments or {}},
            )
        except MCPToolDenied as exc:
            # Some NAI Connector policy decisions are JSON-RPC errors rather
            # than an MCP result with isError=true. Keep one app-level shape.
            return {
                "isError": True,
                "policy_source": "nai-mcp-connector",
                "mcp_error_code": exc.code,
                "content": [{"type": "text", "text": f"DENIED_BY_POLICY: {exc}"}],
            }
