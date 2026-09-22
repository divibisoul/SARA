import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from sara.research.quantum_crawler import HTTPJSONBackend


class _Handler(BaseHTTPRequestHandler):
    calls = 0

    def do_GET(self):  # noqa: N802
        type(self).calls += 1
        if type(self).calls == 1:
            self.send_response(429)
            self.send_header("Retry-After", "0")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"items":[{"name":"demo","license":"MIT","description":"x"}]}')

    def log_message(self, fmt, *args):
        return


def test_http_backend_retries_rate_limit_and_caches_response():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        backend = HTTPJSONBackend(
            f"http://127.0.0.1:{port}/search?q={{query}}",
            cache_ttl_s=10,
            max_retries=2,
            backoff_s=0.01,
            source="TEST",
        )
        first = backend.fetch("demo")
        second = backend.fetch("demo")
        assert first == second
        assert _Handler.calls == 2
    finally:
        server.shutdown()
        server.server_close()
