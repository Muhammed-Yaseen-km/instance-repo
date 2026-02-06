#!/usr/bin/env python3
"""
Auto-deploy webhook listener for GitHub Actions + manual triggers.

SETUP ON SALAM'S MACHINE:
========================

1. Set environment variables:
   export DEPLOY_SECRET="your-secret-here"
   export RESTART_CMD="docker compose restart"

2. Run with systemd (recommended):
   sudo cp deploy-webhook.service /etc/systemd/system/
   sudo systemctl enable deploy-webhook
   sudo systemctl start deploy-webhook

3. Expose via Cloudflare tunnel (add to cloudflared config):
   - hostname: deploy-inference.trycloudflare.com
     service: http://localhost:9000

4. Add GitHub secrets:
   DEPLOY_WEBHOOK_URL: https://deploy-inference.trycloudflare.com
   DEPLOY_SECRET: your-secret-here
   INFERENCE_ENGINE_URL: https://far-hindu-passed-vbulletin.trycloudflare.com
   INFERENCE_API_KEY: your-api-key
"""
import os
import hmac
import hashlib
import subprocess
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime

# Configuration
DEPLOY_SECRET = os.getenv("DEPLOY_SECRET", "")
REPO_PATH = os.getenv("REPO_PATH", os.path.dirname(os.path.abspath(__file__)))
RESTART_CMD = os.getenv("RESTART_CMD", "docker compose restart")
PORT = int(os.getenv("DEPLOY_PORT", "9000"))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("deploy")


def verify_signature(payload: bytes, signature: str, secret_header: str) -> bool:
    """Verify webhook signature (GitHub or custom header)."""
    # Check custom header first (from GitHub Actions)
    if secret_header and DEPLOY_SECRET:
        return hmac.compare_digest(secret_header, DEPLOY_SECRET)

    # Check GitHub webhook signature
    if signature and DEPLOY_SECRET:
        expected = "sha256=" + hmac.new(
            DEPLOY_SECRET.encode(), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    # Allow if no secret configured (development mode)
    if not DEPLOY_SECRET:
        log.warning("No DEPLOY_SECRET configured - allowing all requests!")
        return True

    return False


def deploy():
    """Pull latest code and restart services."""
    log.info(f"Starting deployment in {REPO_PATH}")
    results = {"started_at": datetime.now().isoformat()}

    # Git pull
    log.info("Pulling latest code...")
    result = subprocess.run(
        ["git", "pull", "origin", "main"],
        cwd=REPO_PATH,
        capture_output=True,
        text=True,
        timeout=60
    )
    results["git_pull"] = {
        "success": result.returncode == 0,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip() if result.returncode != 0 else ""
    }
    log.info(f"Git pull: {result.stdout.strip()}")

    if result.returncode != 0:
        log.error(f"Git pull failed: {result.stderr}")
        results["success"] = False
        results["error"] = "Git pull failed"
        return results

    # Restart services
    log.info(f"Restarting services: {RESTART_CMD}")
    result = subprocess.run(
        RESTART_CMD.split(),
        cwd=REPO_PATH,
        capture_output=True,
        text=True,
        timeout=120
    )
    results["restart"] = {
        "success": result.returncode == 0,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip() if result.returncode != 0 else ""
    }

    if result.returncode != 0:
        log.error(f"Restart failed: {result.stderr}")
        results["success"] = False
        results["error"] = "Restart failed"
    else:
        log.info("Deployment completed successfully!")
        results["success"] = True

    results["completed_at"] = datetime.now().isoformat()
    return results


class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        log.info(f"{self.address_string()} - {format % args}")

    def send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def do_POST(self):
        if self.path != "/deploy":
            self.send_json(404, {"error": "Not found"})
            return

        content_length = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(content_length)

        # Get signatures
        github_signature = self.headers.get("X-Hub-Signature-256", "")
        custom_secret = self.headers.get("X-Deploy-Secret", "")

        if not verify_signature(payload, github_signature, custom_secret):
            log.warning(f"Invalid signature from {self.address_string()}")
            self.send_json(403, {"error": "Invalid signature"})
            return

        # Parse payload
        try:
            data = json.loads(payload) if payload else {}
            ref = data.get("ref", "refs/heads/main")
            triggered_by = data.get("triggered_by", "webhook")
        except json.JSONDecodeError:
            ref = "refs/heads/main"
            triggered_by = "unknown"

        # Only deploy main branch
        if ref != "refs/heads/main":
            self.send_json(200, {"message": f"Ignoring push to {ref}"})
            return

        log.info(f"Deployment triggered by {triggered_by}")

        try:
            results = deploy()
            status = 200 if results.get("success") else 500
            self.send_json(status, results)
        except Exception as e:
            log.exception("Deployment failed with exception")
            self.send_json(500, {"error": str(e)})

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {
                "status": "ok",
                "repo_path": REPO_PATH,
                "restart_cmd": RESTART_CMD
            })
        elif self.path == "/":
            self.send_json(200, {
                "service": "inference-engine-deploy",
                "endpoints": {
                    "/deploy": "POST - Trigger deployment",
                    "/health": "GET - Health check"
                }
            })
        else:
            self.send_json(404, {"error": "Not found"})


def main():
    log.info("=" * 50)
    log.info("Inference Engine Deploy Webhook")
    log.info("=" * 50)
    log.info(f"Port: {PORT}")
    log.info(f"Repo: {REPO_PATH}")
    log.info(f"Restart: {RESTART_CMD}")
    log.info(f"Secret: {'configured' if DEPLOY_SECRET else 'NOT SET (dev mode)'}")
    log.info("=" * 50)

    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    try:
        log.info(f"Listening on http://0.0.0.0:{PORT}")
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
