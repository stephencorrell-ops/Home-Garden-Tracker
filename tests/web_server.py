"""A small server for testing the web app without Pyodide: it serves web/dist and runs the real Python core behind
the same calls the page makes (see HttpEngine in web/engine.js)."""
import json
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tests import _load  # noqa: F401
from custom_components.garden_tracker.core.api import GardenApp

ROOT = Path(__file__).resolve().parents[1]
SPECIES = (ROOT / "custom_components" / "garden_tracker" / "core" / "species.json").read_text("utf-8")


class Handler(SimpleHTTPRequestHandler):
    app: GardenApp | None = None

    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
        path = self.path.strip("/")
        cls = type(self)
        if path == "start":
            cls.app = GardenApp(SPECIES, body.get("stored"), body.get("today"))
            out = {"ok": True}
        elif path == "call":
            out = json.loads(cls.app.call(body["service"], json.dumps(body.get("data") or {})))
        elif path == "snapshot":
            out = json.loads(cls.app.snapshot())
        elif path == "data":
            out = json.loads(cls.app.data())
        elif path == "today":
            cls.app.set_today(body["today"])
            out = {"ok": True}
        elif path == "weather":
            out = json.loads(cls.app.merge_weather(json.dumps(body)))
        else:
            self.send_error(404)
            return
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def serve(directory: str, port: int = 0) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=directory))


if __name__ == "__main__":
    s = serve(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 8123)
    print("serving on", s.server_address)
    s.serve_forever()
