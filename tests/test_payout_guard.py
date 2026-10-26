"""Tests for payout exposure, invocation, and optional application policy."""
import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

import app.main as main


def successful_result():
    return {
        "isError": False,
        "operation": "approve_claim_payout",
        "status": "approved",
        "execution": "simulated",
        "content": [{"type": "text", "text": "SIMULATED_PAYMENT_APPROVED"}],
    }


class PayoutPolicyTests(unittest.TestCase):
    def test_approval_intent_selects_payout_tool(self):
        selected, args = main.choose_tool(
            "Approve the payout for claim CLM-2026-1043 and execute payment now"
        )
        self.assertEqual(selected, main.settings.blocked_tool)
        self.assertEqual(args["claim_id"], "CLM-2026-1043")

    def _request(self):
        return main.AssistantRequest(
            message="Approve the payout for claim CLM-2026-1043 and execute payment now"
        )

    def test_rehearsal_exposure_flag_controls_advertised_tools(self):
        from mock_mcp import server
        original = os.environ.get("MOCK_MCP_EXPOSE_PAYOUT")
        try:
            os.environ["MOCK_MCP_EXPOSE_PAYOUT"] = "false"
            self.assertNotIn("approve_claim_payout", {t["name"] for t in server.advertised_tools()})
            os.environ["MOCK_MCP_EXPOSE_PAYOUT"] = "true"
            self.assertIn("approve_claim_payout", {t["name"] for t in server.advertised_tools()})
        finally:
            if original is None:
                os.environ.pop("MOCK_MCP_EXPOSE_PAYOUT", None)
            else:
                os.environ["MOCK_MCP_EXPOSE_PAYOUT"] = original

    def test_hidden_tool_is_not_called(self):
        original_mcp, original_policy = main.mcp, main.settings.app_policy_deny_payout
        fake_mcp = SimpleNamespace(
            list_tools=AsyncMock(return_value=[{"name": "get_claim_status"}]),
            call_tool=AsyncMock(),
        )
        main.mcp = fake_mcp
        main.settings.app_policy_deny_payout = False
        try:
            result = asyncio.run(main.assistant(self._request()))
        finally:
            main.mcp, main.settings.app_policy_deny_payout = original_mcp, original_policy
        self.assertTrue(result["blocked"])
        self.assertFalse(result["tool_invoked"])
        self.assertEqual(result["policy_source"], "mcp-connector-allowlist")
        self.assertIn("not available", result["block_reason"])
        fake_mcp.call_tool.assert_not_awaited()

    def test_exposed_tool_is_invoked_when_app_policy_is_disabled(self):
        original_mcp, original_policy = main.mcp, main.settings.app_policy_deny_payout
        fake_mcp = SimpleNamespace(
            list_tools=AsyncMock(return_value=[{"name": main.settings.blocked_tool}]),
            call_tool=AsyncMock(return_value=successful_result()),
        )
        main.mcp = fake_mcp
        main.settings.app_policy_deny_payout = False
        try:
            result = asyncio.run(main.assistant(self._request()))
        finally:
            main.mcp, main.settings.app_policy_deny_payout = original_mcp, original_policy
        self.assertFalse(result["blocked"])
        self.assertTrue(result["tool_invoked"])
        self.assertEqual(result["tool_result"]["execution"], "simulated")
        fake_mcp.call_tool.assert_awaited_once_with(
            main.settings.blocked_tool,
            {"claim_id": "CLM-2026-1043", "amount": 1840},
        )

    def test_exposed_tool_is_blocked_by_application_policy(self):
        original_mcp, original_policy = main.mcp, main.settings.app_policy_deny_payout
        fake_mcp = SimpleNamespace(
            list_tools=AsyncMock(return_value=[{"name": main.settings.blocked_tool}]),
            call_tool=AsyncMock(),
        )
        main.mcp = fake_mcp
        main.settings.app_policy_deny_payout = True
        try:
            result = asyncio.run(main.assistant(self._request()))
        finally:
            main.mcp, main.settings.app_policy_deny_payout = original_mcp, original_policy
        self.assertTrue(result["blocked"])
        self.assertFalse(result["tool_invoked"])
        self.assertEqual(result["policy_source"], "application-policy")
        self.assertFalse(result["mcp_denial_verified"])
        fake_mcp.call_tool.assert_not_awaited()

    def test_mcp_denial_is_preserved_without_llm_call(self):
        original_mcp, original_llm, original_policy = main.mcp, main.llm, main.settings.app_policy_deny_payout
        denial = {
            "isError": True,
            "policy_source": "mcp-server-policy",
            "content": [{"type": "text", "text": "DENIED_BY_POLICY: Human authorization required."}],
        }
        fake_mcp = SimpleNamespace(
            list_tools=AsyncMock(return_value=[{"name": main.settings.blocked_tool}]),
            call_tool=AsyncMock(return_value=denial),
        )
        fake_llm = SimpleNamespace(chat=AsyncMock())
        main.mcp, main.llm = fake_mcp, fake_llm
        main.settings.app_policy_deny_payout = False
        try:
            result = asyncio.run(main.assistant(self._request()))
        finally:
            main.mcp, main.llm, main.settings.app_policy_deny_payout = original_mcp, original_llm, original_policy
        self.assertTrue(result["blocked"])
        self.assertTrue(result["tool_invoked"])
        self.assertTrue(result["mcp_denial_verified"])
        self.assertEqual(result["policy_source"], "mcp-server-policy")
        self.assertIn("DENIED_BY_POLICY", result["content"])
        fake_llm.chat.assert_not_awaited()

    def test_raw_tool_endpoint_honors_application_policy(self):
        original_mcp, original_policy = main.mcp, main.settings.app_policy_deny_payout
        fake_mcp = SimpleNamespace(
            list_tools=AsyncMock(return_value=[{"name": main.settings.blocked_tool}]),
            call_tool=AsyncMock(),
        )
        main.mcp = fake_mcp
        main.settings.app_policy_deny_payout = True
        try:
            result = asyncio.run(main.call_tool(main.ToolRequest(name=main.settings.blocked_tool)))
        finally:
            main.mcp, main.settings.app_policy_deny_payout = original_mcp, original_policy
        self.assertTrue(result["blocked"])
        self.assertFalse(result["tool_invoked"])
        self.assertEqual(result["policy_source"], "application-policy")
        fake_mcp.call_tool.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
