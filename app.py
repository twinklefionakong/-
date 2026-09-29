import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from src.retrieval import HybridSearcher, compose_evidence_answer


PROJECT_ROOT = Path(__file__).resolve().parent
WEB_ROOT = PROJECT_ROOT / "web"
searcher = HybridSearcher()


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)

    def do_GET(self):
        if urlparse(self.path).path == "/":
            self.path = "/web/index.html"
        return super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != "/api/search":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            query = str(payload.get("query", "")).strip()
            if not query:
                raise ValueError("请输入问题")
            results = searcher.search(query)
            response = {
                "query": query,
                "answer": compose_evidence_answer(query, results),
                "results": results,
            }
            body = json.dumps(response, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
        except Exception as error:
            body = json.dumps({"error": str(error)}, ensure_ascii=False).encode("utf-8")
            self.send_response(400)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        if args and str(args[0]).startswith("POST"):
            super().log_message(format, *args)


if __name__ == "__main__":
    host, port = "127.0.0.1", 8000
    print(f"问答页面已启动：http://{host}:{port}")
    print("按 Control+C 停止。")
    ThreadingHTTPServer((host, port), AppHandler).serve_forever()
