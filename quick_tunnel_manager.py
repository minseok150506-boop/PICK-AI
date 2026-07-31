"""PICK AI - Cloudflare Quick Tunnel 자동 관리자.

기능:
1) 로컬 Ollama 앞에 토큰 인증 게이트웨이를 실행합니다.
2) cloudflared Quick Tunnel을 시작하고 trycloudflare.com 주소를 감지합니다.
3) Render 환경변수 PICK_OLLAMA_HOST / PICK_OLLAMA_TOKEN을 자동 갱신합니다.
4) Render Deploy Hook을 호출해 새 주소를 적용합니다.

주의: 이 파일과 .pick_tunnel.env는 집 PC에서만 실행/보관하세요.
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / ".pick_tunnel.env"
URL_RE = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def require_config() -> dict[str, str]:
    cfg = {**load_env_file(CONFIG_PATH), **os.environ}
    required = ["RENDER_API_KEY", "RENDER_SERVICE_ID", "RENDER_DEPLOY_HOOK", "PICK_OLLAMA_TOKEN"]
    missing = [name for name in required if not cfg.get(name)]
    if missing:
        print("[오류] 설정값이 없습니다: " + ", ".join(missing))
        print("먼저 setup_quick_tunnel.ps1 을 실행하세요.")
        raise SystemExit(2)
    cfg.setdefault("OLLAMA_LOCAL_URL", "http://127.0.0.1:11434")
    cfg.setdefault("GATEWAY_HOST", "127.0.0.1")
    cfg.setdefault("GATEWAY_PORT", "11435")
    cfg.setdefault("CLOUDFLARED_PATH", "cloudflared")
    return cfg


def http_json(url: str, *, method: str = "GET", headers: Optional[dict[str, str]] = None,
              body: Optional[dict] = None, timeout: int = 30) -> tuple[int, bytes]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req_headers = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.status, response.read()


def verify_ollama(local_url: str) -> None:
    try:
        status, _ = http_json(local_url.rstrip("/") + "/api/tags", timeout=5)
        if status != 200:
            raise RuntimeError(f"HTTP {status}")
    except Exception as exc:
        print(f"[오류] Ollama에 연결할 수 없습니다: {local_url}")
        print("Ollama 앱이 실행 중인지 확인한 뒤 다시 실행하세요.")
        raise SystemExit(3) from exc


def make_gateway_handler(local_url: str, token: str):
    class GatewayHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _authorized(self) -> bool:
            supplied = self.headers.get("X-PICK-TUNNEL-TOKEN", "")
            auth = self.headers.get("Authorization", "")
            return supplied == token or auth == f"Bearer {token}"

        def _reject(self) -> None:
            payload = b'{"error":"unauthorized"}'
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _proxy(self) -> None:
            if not self._authorized():
                self._reject()
                return
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(length) if length else None
            target = local_url.rstrip("/") + self.path
            headers = {"Content-Type": self.headers.get("Content-Type", "application/json")}
            req = urllib.request.Request(target, data=body, headers=headers, method=self.command)
            try:
                with urllib.request.urlopen(req, timeout=300) as response:
                    response_body = response.read()
                    self.send_response(response.status)
                    self.send_header("Content-Type", response.headers.get("Content-Type", "application/json"))
                    self.send_header("Content-Length", str(len(response_body)))
                    self.end_headers()
                    self.wfile.write(response_body)
            except urllib.error.HTTPError as exc:
                response_body = exc.read()
                self.send_response(exc.code)
                self.send_header("Content-Type", exc.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(response_body)))
                self.end_headers()
                self.wfile.write(response_body)
            except Exception as exc:
                response_body = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
                self.send_response(502)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(response_body)))
                self.end_headers()
                self.wfile.write(response_body)

        do_GET = _proxy
        do_POST = _proxy
        do_OPTIONS = _proxy

        def log_message(self, fmt: str, *args) -> None:
            return

    return GatewayHandler


def start_gateway(cfg: dict[str, str]) -> ThreadingHTTPServer:
    host = cfg["GATEWAY_HOST"]
    port = int(cfg["GATEWAY_PORT"])
    server = ThreadingHTTPServer((host, port), make_gateway_handler(cfg["OLLAMA_LOCAL_URL"], cfg["PICK_OLLAMA_TOKEN"]))
    thread = threading.Thread(target=server.serve_forever, name="pick-ollama-gateway", daemon=True)
    thread.start()
    print(f"[정상] 보안 게이트웨이 실행: http://{host}:{port}")
    return server


def update_render_env(cfg: dict[str, str], key: str, value: str) -> None:
    service_id = cfg["RENDER_SERVICE_ID"]
    url = f"https://api.render.com/v1/services/{service_id}/env-vars/{key}"
    headers = {"Authorization": f"Bearer {cfg['RENDER_API_KEY']}"}
    status, _ = http_json(url, method="PUT", headers=headers, body={"value": value}, timeout=30)
    if status not in (200, 201):
        raise RuntimeError(f"Render 환경변수 갱신 실패: HTTP {status}")


def trigger_render_deploy(cfg: dict[str, str]) -> None:
    req = urllib.request.Request(cfg["RENDER_DEPLOY_HOOK"], data=b"", method="POST")
    with urllib.request.urlopen(req, timeout=30) as response:
        if response.status not in (200, 201, 202):
            raise RuntimeError(f"Render 재배포 요청 실패: HTTP {response.status}")


def apply_tunnel_url(cfg: dict[str, str], tunnel_url: str) -> None:
    print(f"[감지] 새 Quick Tunnel 주소: {tunnel_url}")
    update_render_env(cfg, "PICK_OLLAMA_HOST", tunnel_url)
    update_render_env(cfg, "PICK_OLLAMA_TOKEN", cfg["PICK_OLLAMA_TOKEN"])
    trigger_render_deploy(cfg)
    print("[완료] Render 환경변수 갱신 및 재배포 요청 완료")


def run_cloudflared_once(cfg: dict[str, str], last_url: Optional[str]) -> tuple[int, Optional[str]]:
    gateway_url = f"http://{cfg['GATEWAY_HOST']}:{cfg['GATEWAY_PORT']}"
    cmd = [cfg["CLOUDFLARED_PATH"], "tunnel", "--url", gateway_url, "--no-autoupdate"]
    print("[시작] Cloudflare Quick Tunnel 실행 중...")
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace", bufsize=1)
    except FileNotFoundError as exc:
        print("[오류] cloudflared를 찾지 못했습니다. 설치 또는 CLOUDFLARED_PATH 설정을 확인하세요.")
        raise SystemExit(4) from exc

    current_url = last_url
    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            clean = line.rstrip()
            print("[cloudflared] " + clean)
            match = URL_RE.search(clean)
            if match:
                found = match.group(0)
                if found != current_url:
                    try:
                        apply_tunnel_url(cfg, found)
                        current_url = found
                    except Exception as exc:
                        print(f"[오류] Render 자동 갱신 실패: {exc}")
        return proc.wait(), current_url
    except KeyboardInterrupt:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        raise


def main() -> None:
    cfg = require_config()
    verify_ollama(cfg["OLLAMA_LOCAL_URL"])
    server = start_gateway(cfg)
    last_url: Optional[str] = None

    def stop_handler(_signum, _frame):
        server.shutdown()
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, stop_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, stop_handler)

    try:
        while True:
            code, last_url = run_cloudflared_once(cfg, last_url)
            print(f"[경고] cloudflared가 종료되었습니다(코드 {code}). 10초 후 다시 시작합니다.")
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n[종료] PICK Quick Tunnel 관리자를 종료합니다.")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
