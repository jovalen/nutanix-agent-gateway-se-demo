"""Isolated OpenAI-compatible upstream for controlled NAI fallback tests.

The inference listener and the administrative listener are deliberately separate:
- inference: the URL that a dedicated NAI target may reach;
- admin: local control used to switch the isolated upstream between 200/429/503.
Never expose the admin listener publicly.
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from typing import Any

MODE = {"code": 200}
LOCK = Lock()
ADMIN_TOKEN = os.environ.get("FAULT_ADMIN_TOKEN", "")
INFERENCE_PORT = int(os.environ.get("FAULT_INFERENCE_PORT", "8080"))
ADMIN_PORT = int(os.environ.get("FAULT_ADMIN_PORT", "8089"))


def send_json(handler: BaseHTTPRequestHandler, code: int, data: dict[str, Any]) -> None:
    payload = json.dumps(data).encode()
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def read_json(handler: BaseHTTPRequestHandler, maximum: int) -> dict[str, Any] | None:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
        if length < 0 or length > maximum:
            return None
        value = json.loads(handler.rfile.read(length))
        return value if isinstance(value, dict) else None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


class InferenceHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/healthz":
            send_json(self, 200, {"ok": True, "listener": "inference"})
            return
        send_json(self, 404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            send_json(self, 404, {"error": "not found"})
            return
        with LOCK:
            status = MODE["code"]
        if status != 200:
            send_json(self, status, {"error": {"message": f"Lab upstream returned HTTP {status}", "type": "lab_fault"}})
            return
        body = read_json(self, 100000)
        if body is None:
            send_json(self, 400, {"error": "invalid payload"})
            return
        model = str(body.get("model") or "fault-test-primary")
        send_json(self, 200, {
            "id": "chatcmpl-faultlab",
            "object": "chat.completion",
            "created": 0,
            "model": model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "Primary lab provider responded normally."},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
        })

    def log_message(self, *_: object) -> None:
        return


class AdminHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/healthz":
            send_json(self, 404, {"error": "not found"})
            return
        with LOCK:
            status = MODE["code"]
        send_json(self, 200, {"ok": True, "listener": "admin", "upstream_status": status})

    def do_POST(self) -> None:
        if self.path != "/admin/mode":
            send_json(self, 404, {"error": "not found"})
            return
        if not ADMIN_TOKEN or self.headers.get("Authorization") != f"Bearer {ADMIN_TOKEN}":
            send_json(self, 403, {"error": "forbidden"})
            return
        body = read_json(self, 1024)
        try:
            code = int(body["status"]) if body is not None else 0
        except (KeyError, TypeError, ValueError):
            code = 0
        if code not in (200, 429, 503):
            send_json(self, 400, {"error": "status must be 200, 429 or 503"})
            return
        with LOCK:
            MODE["code"] = code
        send_json(self, 200, {"upstream_status": code})

    def log_message(self, *_: object) -> None:
        return


def run() -> None:
    admin = ThreadingHTTPServer(("0.0.0.0", ADMIN_PORT), AdminHandler)
    Thread(target=admin.serve_forever, daemon=True).start()
    inference = ThreadingHTTPServer(("0.0.0.0", INFERENCE_PORT), InferenceHandler)
    try:
        inference.serve_forever()
    finally:
        inference.server_close()
        admin.shutdown()
        admin.server_close()


if __name__ == "__main__":
    run()
