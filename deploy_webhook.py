#!/usr/bin/env python3
"""
Auto-deploy webhook listener.
Pulls latest code and restarts services when GitHub push is received.

Run on Salam's machine:
    python deploy_webhook.py

Then add webhook in GitHub repo settings:
    URL: http://<salam-public-ip>:9000/deploy
    Content-type: application/json
    Secret: (set DEPLOY_SECRET env var)
    Events: Just the push event
"""
import os
import hmac
import hashlib
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

DEPLOY_SECRET = os.getenv("DEPLOY_SECRET", "your-secret-here")
REPO_PATH = os.getenv("REPO_PATH", os.path.dirname(os.path.abspath(__file__)))
RESTART_CMD = os.getenv("RESTART_CMD", "docker compose restart")
PORT = int(os.getenv("DEPLOY_PORT", "9000"))


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature."""
    if not signature:
        return DEPLOY_SECRET == "your-secret-here"  # Allow if no secret configured
    expected = "sha256=" + hmac.new(
        DEPLOY_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def deploy():
    """Pull latest code and restart services."""
    print(f"[Deploy] Pulling latest code in {REPO_PATH}...")
    result = subprocess.run(
        ["git", "pull", "origin", "main"],
        cwd=REPO_PATH,
        capture_output=True,
        text=True
    )
    print(f"[Deploy] Git pull: {result.stdout}")
    if result.returncode != 0:
        print(f"[Deploy] Git error: {result.stderr}")
        return False, result.stderr

    print(f"[Deploy] Restarting services: {RESTART_CMD}")
    result = subprocess.run(
        RESTART_CMD.split(),
        cwd=REPO_PATH,
        capture_output=True,
        text=True
    )
    print(f"[Deploy] Restart: {result.stdout}")
    if result.returncode != 0:
        print(f"[Deploy] Restart error: {result.stderr}")
        return False, result.stderr

    return True, "Deployed successfully"


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/deploy":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(content_length)
        signature = self.headers.get("X-Hub-Signature-256", "")

        if not verify_signature(payload, signature):
            print("[Deploy] Invalid signature!")
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Invalid signature")
            return

        # Check if it's a push to main
        try:
            data = json.loads(payload)
            ref = data.get("ref", "")
            if ref != "refs/heads/main":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(f"Ignoring push to {ref}".encode())
                return
        except json.JSONDecodeError:
            pass

        # Deploy!
        success, message = deploy()
        self.send_response(200 if success else 500)
        self.end_headers()
        self.wfile.write(message.encode())

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    print(f"[Deploy] Starting webhook listener on port {PORT}")
    print(f"[Deploy] Repo path: {REPO_PATH}")
    print(f"[Deploy] Restart command: {RESTART_CMD}")
    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Deploy] Shutting down...")
        server.shutdown()
