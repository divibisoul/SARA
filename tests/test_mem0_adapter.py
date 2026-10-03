from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from sara.integrations import mem0

class Handler(BaseHTTPRequestHandler):
    calls = []
    def do_GET(self):
        self.__class__.calls.append((self.command, self.path, dict(self.headers), None))
        raw = json.dumps({"ok": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        self.__class__.calls.append((self.command, self.path, dict(self.headers), json.loads(raw or b"{}")))
        payload = {"results": [{"memory": "ok"}]} if "search" in self.path else {"results": [{"memory": "saved"}]}
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def log_message(self, *_args):
        return

def test_mem0_calls():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        old_url = mem0.os.environ.get("SARA_MEM0_URL")
        old_key = mem0.os.environ.get("SARA_MEM0_API_KEY")
        old_user = mem0.os.environ.get("SARA_MEM0_USER_ID")
        mem0.os.environ.update({
            "SARA_MEM0_URL": f"http://127.0.0.1:{server.server_port}",
            "SARA_MEM0_API_KEY": "k",
            "SARA_MEM0_USER_ID": "sara-test",
        })
        Handler.calls.clear()
        assert mem0.status()["state"] == "LIVE"
        mem0.add("hello", metadata={"source": "test"})
        mem0.search("hello", top_k=3)
        mem0.get_all(page=1, page_size=2)
        assert len(Handler.calls) == 4
        assert Handler.calls[1][1] == "/v3/memories/add/"
        assert Handler.calls[2][1] == "/v3/memories/search/"
        assert Handler.calls[1][2]["Authorization"] == "Token k"
        assert Handler.calls[1][2]["Mem0-User-ID"] == "sara-test"
    finally:
        for key, value in {
            "SARA_MEM0_URL": old_url,
            "SARA_MEM0_API_KEY": old_key,
            "SARA_MEM0_USER_ID": old_user,
        }.items():
            if value is None:
                mem0.os.environ.pop(key, None)
            else:
                mem0.os.environ[key] = value
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    test_mem0_calls()
