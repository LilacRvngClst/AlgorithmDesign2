"""Run main.py directly; the local demo opens automatically in Chrome."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from agent import execute
from scenarios import configuration

ROOT = Path(__file__).resolve().parent


def find_chrome():
    candidates = [os.environ.get("CHROME_PATH", "")]
    for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        if os.environ.get(env):
            candidates.append(str(Path(os.environ[env]) / "Google/Chrome/Application/chrome.exe"))
    return next((p for p in candidates if p and Path(p).is_file()), None)


def open_browser(url):
    chrome = find_chrome()
    if chrome:
        subprocess.Popen([chrome, "--new-window", url])
    else:
        print("未找到 Chrome，使用系统默认浏览器。可设置 CHROME_PATH 指定 Chrome。", flush=True)
        webbrowser.open(url)


class Handler(BaseHTTPRequestHandler):
    def send(self, status, data, content_type="application/json; charset=utf-8"):
        raw = json.dumps(data, ensure_ascii=False).encode() if isinstance(data, (dict, list)) else data
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/config":
            return self.send(200, configuration())
        files = {"/": ("static/index.html", "text/html; charset=utf-8"),
                 "/app.js": ("static/app.js", "text/javascript; charset=utf-8"),
                 "/style.css": ("static/style.css", "text/css; charset=utf-8"),
                 "/data/energy.csv": ("data/energy.csv", "text/csv; charset=utf-8")}
        if path not in files:
            return self.send(404, {"error": "页面不存在"})
        relative, mime = files[path]
        file = ROOT / relative
        if not file.is_file():
            return self.send(404, {"error": "文件不存在"})
        self.send(200, file.read_bytes(), mime)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= 65536:
                raise ValueError("请求大小无效")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("请求内容必须为对象")
            path = urlsplit(self.path).path
            if path == "/api/run":
                return self.send(200, execute(payload))
            self.send(404, {"error": "接口不存在"})
        except (ValueError, TypeError, KeyError) as exc:
            self.send(400, {"error": str(exc)})


class LocalServer(ThreadingHTTPServer):
    # Windows SO_REUSEADDR can bind a second server to the same listening port.
    allow_reuse_address = False


def create_server(port=8765):
    # Binding port 0 lets the OS choose a free port. Explicit occupied ports fall back.
    try:
        return LocalServer(("127.0.0.1", port), Handler)
    except OSError:
        if port == 0:
            raise
        print(f"端口 {port} 被占用，自动分配空闲端口。", flush=True)
        return LocalServer(("127.0.0.1", 0), Handler)


def main():
    parser = argparse.ArgumentParser(description="可视化智能体分析路径规划")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    server = create_server(args.port)
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"可视化智能体分析路径规划已启动：{url}", flush=True)
    print("在 PyCharm 点击停止按钮，或按 Ctrl+C 结束服务。", flush=True)
    if not args.no_browser:
        threading.Timer(0.7, open_browser, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
