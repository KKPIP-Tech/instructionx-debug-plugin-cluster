"""Local Server HTTP 服务层

包含所有 HTTP 服务器相关的业务逻辑。
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


class RequestHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    on_request_callback = None

    def do_GET(self):
        self._handle_request()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(content_length)
        self._handle_request()

    def _handle_request(self):
        if RequestHandler.on_request_callback:
            try:
                RequestHandler.on_request_callback()
            except Exception:
                pass
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response = {
            "status": "ok",
            "message": "Local Server is running",
            "path": self.path
        }
        self.wfile.write(json.dumps(response).encode())

    def log_message(self, format, *args):
        pass


class HttpService:
    """HTTP 服务器服务"""

    def __init__(self, port: int = None):
        self._server = None
        self._port = port
        self._load_config()

    def _load_config(self):
        config_path = Path(__file__).parent.parent.parent / "config" / "default.json"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self._default_port = cfg.get("server", {}).get("default_port", 8080)
            port_range = cfg.get("server", {}).get("port_range", [1024, 65535])
            self._min_port = port_range[0]
            self._max_port = port_range[1]
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            self._default_port = 8080
            self._min_port = 1024
            self._max_port = 65535

    def get_default_port(self) -> int:
        return self._default_port

    def get_port_range(self) -> tuple:
        return (self._min_port, self._max_port)

    def get_port(self) -> int:
        return self._port if self._port else self._default_port

    def start_server(self, port: int, request_callback):
        RequestHandler.on_request_callback = request_callback
        self._port = port
        self._server = HTTPServer(("127.0.0.1", port), RequestHandler)
        self._server.serve_forever()

    def stop_server(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

    def shutdown_server(self):
        if self._server:
            self._server.shutdown()

    def close_server(self):
        if self._server:
            self._server.server_close()
            self._server = None

    def is_running(self) -> bool:
        return self._server is not None

    def get_server(self):
        return self._server
