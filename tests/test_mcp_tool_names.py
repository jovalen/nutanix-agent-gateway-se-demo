"""Run with: python3 -m unittest discover -s tests -p 'test_mcp_tool_names.py'"""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.mcp import MCPClient, MCPError


def client_with_tools(names):
    client = MCPClient(SimpleNamespace())
    calls = []

    async def request(method, params=None):
        calls.append((method, params))
        if method == "tools/list":
            return {"tools": [{"name": name, "description": "test"} for name in names]}
        if method == "tools/call":
            return {"content": [{"type": "text", "text": "ok"}]}
        raise AssertionError(method)

    client.request = AsyncMock(side_effect=request)
    return client, calls


class MCPToolNameTests(unittest.TestCase):
    def test_rehearsal_uses_short_name(self):
        client, calls = client_with_tools(["get_customer_policy"])
        tools = asyncio.run(client.list_tools())
        asyncio.run(client.call_tool("get_customer_policy", {"customer_id": "CUST-2048"}))
        self.assertEqual(tools[0]["name"], "get_customer_policy")
        self.assertEqual(calls[-1][1]["name"], "get_customer_policy")

    def test_live_uses_exact_nai_published_name(self):
        names = ["mcp-jorge-mcp-server__get_customer_policy"]
        client, calls = client_with_tools(names)
        tools = asyncio.run(client.list_tools())
        asyncio.run(client.call_tool("get_customer_policy"))
        self.assertEqual(tools[0]["name"], "get_customer_policy")
        self.assertEqual(calls[-1][1]["name"], names[0])

    def test_unpublished_tool_is_not_called(self):
        client, calls = client_with_tools(["get_customer_policy"])
        with self.assertRaises(MCPError):
            asyncio.run(client.call_tool("approve_claim_payout"))
        self.assertFalse(any(method == "tools/call" for method, _ in calls))

    def test_ambiguous_tool_names_are_rejected(self):
        client, _ = client_with_tools(["server-a__get_claim_status", "server-b__get_claim_status"])
        with self.assertRaisesRegex(MCPError, "Ambiguous"):
            asyncio.run(client.list_tools())

    def test_changed_connector_allowlist_is_respected(self):
        client, calls = client_with_tools(["get_customer_policy"])
        asyncio.run(client.list_tools())
        async def changed_request(method, params=None):
            if method == "tools/list":
                return {"tools": []}
            if method == "tools/call":
                raise AssertionError("Should never call a hidden tool")
        client.request = AsyncMock(side_effect=changed_request)
        with self.assertRaises(MCPError):
            asyncio.run(client.call_tool("get_customer_policy"))


if __name__ == "__main__":
    unittest.main()

class MCPPolicyDenialTests(unittest.TestCase):
    def test_json_rpc_tool_denial_is_normalized(self):
        client = MCPClient(SimpleNamespace())
        client._tool_aliases = {"approve_claim_payout": "server__approve_claim_payout"}
        async def denied_request(method, params=None):
            if method == "tools/list":
                return {"tools": [{"name": "server__approve_claim_payout"}]}
            self.assertEqual(method, "tools/call")
            from app.mcp import MCPToolDenied
            raise MCPToolDenied("Human authorization is required", code=-32003)
        client.request = AsyncMock(side_effect=denied_request)
        result = asyncio.run(client.call_tool("approve_claim_payout"))
        self.assertTrue(result["isError"])
        self.assertEqual(result["policy_source"], "nai-mcp-connector")
        self.assertEqual(result["mcp_error_code"], -32003)
        self.assertIn("DENIED_BY_POLICY", result["content"][0]["text"])
