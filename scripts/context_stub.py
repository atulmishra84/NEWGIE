#!/usr/bin/env python3
"""Minimal Context Intelligence health stub for local Full+GIE staging."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/healthz", "/health"}:
            self._json(200, {"status": "ok", "agent": "context-intelligence", "mode": "stub"})
            return
        self._json(404, {"error": "not_found"})

    def log_message(self, fmt: str, *args) -> None:
        return


if __name__ == "__main__":
    # Bind all interfaces so Docker published ports work.
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
