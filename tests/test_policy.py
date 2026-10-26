import unittest

from app.policy import choose_tool


KW = dict(
    policy_tool="get_customer_policy",
    claim_tool="get_claim_status",
    repair_tool="find_repair_shops",
    create_claim_tool="create_claim",
    blocked_tool="approve_claim_payout",
)


class PolicyTests(unittest.TestCase):
    def test_payout_intent_wins_over_claim_keyword(self):
        tool, args = choose_tool("Approve the payout for claim CLM-2026-1043 and execute payment now", **KW)
        self.assertEqual(tool, "approve_claim_payout")
        self.assertEqual(args["claim_id"], "CLM-2026-1043")

    def test_payout_status_is_read_only(self):
        tool, _ = choose_tool("What is the payout status for my claim?", **KW)
        self.assertEqual(tool, "get_claim_status")

    def test_create_claim_wording_is_not_rigid(self):
        tool, _ = choose_tool("I want to file a new insurance claim", **KW)
        self.assertEqual(tool, "create_claim")


if __name__ == "__main__":
    unittest.main()
