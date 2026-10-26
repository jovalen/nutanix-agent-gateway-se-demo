"""Offline test for the separated fault-provider listeners."""
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from fault_provider import server


class FaultProviderTests(unittest.TestCase):
    def setUp(self):
        server.ADMIN_TOKEN = "test-token"
        server.MODE["code"] = 200
        self.inference = ThreadingHTTPServer(("127.0.0.1", 0), server.InferenceHandler)
        self.admin = ThreadingHTTPServer(("127.0.0.1", 0), server.AdminHandler)
        self.threads = [
            threading.Thread(target=self.inference.serve_forever, daemon=True),
            threading.Thread(target=self.admin.serve_forever, daemon=True),
        ]
        for thread in self.threads:
            thread.start()

    def tearDown(self):
        self.inference.shutdown()
        self.admin.shutdown()
        self.inference.server_close()
        self.admin.server_close()

    def url(self, httpd, path):
        return f"http://127.0.0.1:{httpd.server_port}{path}"

    def test_admin_switch_changes_only_inference_state(self):
        payload = json.dumps({"status": 503}).encode()
        request = urllib.request.Request(
            self.url(self.admin, "/admin/mode"),
            data=payload,
            headers={
                "Authorization": "Bearer test-token",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            self.assertEqual(response.status, 200)

        inference_request = urllib.request.Request(
            self.url(self.inference, "/v1/chat/completions"),
            data=b'{"model":"fault-test-primary","messages":[]}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(inference_request)
        self.assertEqual(error.exception.code, 503)

        with urllib.request.urlopen(self.url(self.admin, "/healthz")) as response:
            state = json.load(response)
        self.assertEqual(state["upstream_status"], 503)


if __name__ == "__main__":
    unittest.main()
