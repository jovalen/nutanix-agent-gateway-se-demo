import os
import unittest
from unittest.mock import patch
from cache import experiment
from engine import brief, investigate, FACTS, PUBLIC

class DemoTests(unittest.TestCase):
    @patch.dict(os.environ, {"DEMO_MODE":"rehearsal"})
    def test_private_fallback_and_briefing(self):
        trace = []
        case = investigate(trace, True)
        self.assertEqual(set(case["evidence"]), set(FACTS))
        self.assertEqual([x["route"] for x in trace if "route" in x],
                         ["private", "private_backup", "private", "private", "private"])
        self.assertTrue(brief(trace))
        self.assertEqual(trace[-1]["route"], "hosted")
        self.assertEqual(case["status"], "awaiting review")

    @patch.dict(os.environ, {"DEMO_MODE":"live"})
    @patch("engine.endpoint")
    def test_hosted_input(self, endpoint):
        endpoint.return_value = {"model":"reported", "choices":[{"message":{"content":"Draft"}}]}
        trace = []
        brief(trace)
        route, messages = endpoint.call_args.args
        self.assertEqual(route, "hosted")
        self.assertEqual(messages, [{"role":"user","content":PUBLIC+" Write a short customer update using only these facts."}])
        self.assertIsNone(trace[0]["cached_tokens"])

    def test_prefix(self):
        stats = experiment()
        self.assertTrue(stats["same_output"])
        self.assertGreater(stats["cold_projections"], stats["warm_projections"])

class PresenterTests(unittest.TestCase):
    @patch.dict(os.environ, {"DEMO_MODE":"rehearsal"})
    def test_full_presenter_journey(self):
        import io
        import json
        from server import Presenter, TOKEN

        def request(path, case_id=""):
            class Transport:
                response = bytearray()
                def makefile(self, *args):
                    method = "GET" if path == "/" else "POST"
                    return io.BytesIO((f"{method} {path} HTTP/1.0\r\nX-Presenter: {TOKEN}\r\n"
                                       f"X-Case: {case_id}\r\n\r\n").encode())
                def sendall(self, data):
                    self.response.extend(data)
            transport = Transport()
            Presenter(transport, ("127.0.0.1", 0), None)
            headers, body = transport.response.split(b"\r\n\r\n", 1)
            return int(headers.split()[1]), bytes(body)

        self.assertIn(b"Investigate incident", request("/")[1])
        case = json.loads(request("/investigate")[1])
        self.assertEqual(request("/approve", "stale")[0], 409)
        self.assertIn("shared", json.loads(request("/brief", case["id"])[1]))
        approved = json.loads(request("/approve", case["id"])[1])
        self.assertIn("Review ticket recorded", approved["status"])
        replay = json.loads(request("/fallback")[1])
        self.assertIn("fault", replay["trace"][0])
        self.assertEqual(request("/approve", case["id"])[0], 409)
        self.assertTrue(json.loads(request("/cache")[1])["same_output"])
