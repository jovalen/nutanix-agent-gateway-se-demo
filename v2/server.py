"""Local, single-presenter demo. Run python3 server.py."""
import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from engine import brief, investigate, live, PUBLIC
from cache import experiment

TOKEN = secrets.token_hex(24)
class Presenter(BaseHTTPRequestHandler):
    case = None
    def send(self, status, value, mime="application/json"):
        data = value.encode() if isinstance(value, str) else json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path != "/":
            return self.send(404, {})
        page = Path(__file__).with_name("index.html").read_text()
        self.send(200, page.replace("__TOKEN__", TOKEN).replace("__MODE__", "Live gateway" if live() else "Rehearsal"), "text/html; charset=utf-8")

    def do_POST(self):
        if self.headers.get("X-Presenter") != TOKEN:
            return self.send(403, {})
        trace = []
        try:
            if self.path in ("/investigate", "/fallback"):
                Presenter.case = None
                Presenter.case = investigate(trace, self.path == "/fallback")
            elif self.path == "/cache":
                return self.send(200, experiment())
            elif not self.case or self.headers.get("X-Case") != self.case["id"]:
                return self.send(409, {"error":"Run the investigation first"})
            elif self.path == "/brief" and "brief" not in self.case:
                self.case["brief"] = brief(trace)
                self.case["trace"].extend(trace)
                self.case["shared"] = PUBLIC
            elif self.path == "/approve":
                self.case["status"] = "Review ticket recorded • " + self.case["id"][:8]
            elif self.path != "/brief":
                return self.send(404, {})
            self.send(200, self.case)
        except Exception as exc:
            self.send(502, {"error":"Step stopped: " + type(exc).__name__, "trace":trace})

if __name__ == "__main__":
    with HTTPServer(("127.0.0.1", 8765), Presenter) as http:
        print("Open http://127.0.0.1:8765", flush=True)
        threading.Timer(0.4, webbrowser.open, args=("http://127.0.0.1:8765",)).start()
        http.serve_forever()
