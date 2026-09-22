#!/usr/bin/env python3
from sara.service.http_api import create_server

server = create_server()
print(f"SARA HTTP listening on http://{server.server_address[0]}:{server.server_address[1]}")
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
