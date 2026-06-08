import json
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"


class RadarHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS), **kwargs)

    def do_POST(self):
        if self.path != "/api/refresh":
            self.send_error(404)
            return

        try:
            result = subprocess.run(
                [sys.executable, str(ROOT / "radar.py")],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=120,
            )
            payload = {
                "ok": result.returncode == 0,
                "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-2000:],
            }
            if result.returncode != 0:
                payload["error"] = "radar.py failed"
        except Exception as exc:
            payload = {"ok": False, "error": str(exc)}

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200 if payload["ok"] else 500)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    port = 8787
    server = ThreadingHTTPServer(("127.0.0.1", port), RadarHandler)
    print(f"SemiCSP Radar running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
