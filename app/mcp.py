from typing import Any
import json

import httpx

from .settings import Settings

class MCPError(RuntimeError):
    pass

# NAI añade este prefijo a los nombres publicados por el MCP Connector.
TOOL_NAMES = {
    "get_customer_policy": "mcp-jorge-mcp-server__get_customer_policy",
    "get_claim_status": "mcp-jorge-mcp-server__get_claim_status",
    "find_repair_shops": "mcp-jorge-mcp-server__find_repair_shops",
    "create_claim": "mcp-jorge-mcp-server__create_claim",
}

REVERSE_TOOL_NAMES = {
    value: key for key, value in TOOL_NAMES.items()
}

class MCPClient:
    """Cliente MCP Streamable HTTP para el MCP Connector de NAI."""

    def __init__(self, cfg: Settings):
        self.cfg = cfg
        self._request_id = 0
        self._session_id: str | None = None
        self._initialized = False

        # Permite aprender los nombres reales devueltos por NAI.
        self._tool_aliases: dict[str, str] = dict(TOOL_NAMES)

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
        if response.status_code in {202, 204}:
            return {}

        if not response.text.strip():
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

    async def _post(
        self,
        payload: dict[str, Any],
        include_protocol: bool = True,
    ) -> tuple[dict[str, Any], httpx.Response]:
        try:
            async with httpx.AsyncClient(
                timeout=60,
                verify=self.cfg.tls_verify,
            ) as client:
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
                "clientInfo": {
                    "name": "seguroauto-agent-gateway-demo",
                    "version": "0.3.0",
                },
            },
        }

        result, response = await self._post(payload)

        if "error" in result:
            raise MCPError(
                result["error"].get(
                    "message",
                    "MCP initialize failed",
                )
            )

        self._session_id = response.headers.get("Mcp-Session-Id")

        server_version = result.get("result", {}).get("protocolVersion")

        if server_version:
            self.cfg.mcp_protocol_version = server_version

        self._initialized = True

        # Completa el handshake MCP.
        await self._post(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            }
        )

    async def request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
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
            raise MCPError(
                data["error"].get(
                    "message",
                    "MCP error",
                )
            )

        return data.get("result", data)

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self.request("tools/list")
        tools = result.get("tools", [])

        normalized_tools: list[dict[str, Any]] = []

        for tool in tools:
            item = dict(tool)
            real_name = item.get("name", "")

            # Guardamos el nombre real devuelto por NAI.
            if "__" in real_name:
                friendly_name = real_name.split("__", 1)[1]
                self._tool_aliases[friendly_name] = real_name
                item["name"] = friendly_name
            else:
                item["name"] = REVERSE_TOOL_NAMES.get(
                    real_name,
                    real_name,
                )

            normalized_tools.append(item)

        return normalized_tools

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        real_name = self._tool_aliases.get(
            name,
            TOOL_NAMES.get(name, name),
        )

        return await self.request(
            "tools/call",
            {
                "name": real_name,
                "arguments": arguments or {},
            },
        )

