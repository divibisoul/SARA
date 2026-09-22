"""Executable SARA HTTP service entrypoint using the real stdlib boundary."""
from __future__ import annotations
import os
from sara.service.http_api import create_server


def main() -> None:
    host = os.getenv("SARA_HOST", "0.0.0.0")
    port = int(os.getenv("SARA_PORT", "8090"))
    server = create_server(host, port, fail_closed=True)
    print(f"SARA HTTP listening on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
