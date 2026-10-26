"""Tests for the application-side sensitive-operation guard."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

import app.main as main


class PayoutGuardTests(unittest.TestCase):
    def test_approval_intent_selects_blocked_tool(self):
        selected, args = main.choose_tool(
            "Approve the payout for claim CLM-2026-1043 and execute payment now"
        )
        self.assertEqual(selected, main.settings.blocked_tool)
        self.assertEqual(args["claim_id"], "CLM-2026-1043")

    def test_blocked_payout_does_not_call_mcp_or_llm(self):
        original_mcp, original_llm = main.mcp, main.llm
        fake_mcp = SimpleNamespace(list_tools=AsyncMock(return_value=[]), call_tool=AsyncMock())
        fake_llm = SimpleNamespace(chat=AsyncMock())
        main.mcp, main.llm = fake_mcp, fake_llm
        try:
            request = main.AssistantRequest(
                message="Approve the payout for claim CLM-2026-1043 and execute payment now"
            )
            result = asyncio.run(main.assistant(request))
        finally:
            main.mcp, main.llm = original_mcp, original_llm

        self.assertTrue(result["blocked"])
        self.assertFalse(result["tool_invoked"])
        self.assertEqual(result["usage_source"], "no-llm-request")
        fake_mcp.list_tools.assert_not_awaited()
        fake_mcp.call_tool.assert_not_awaited()
        fake_llm.chat.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
