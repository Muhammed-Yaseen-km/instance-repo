#!/bin/bash
# ============================================
# ONE-TIME SETUP: GitHub Actions Self-Hosted Runner
# Run this ONCE on Salam's machine - after that, everything is automated
# ============================================

set -e

echo "=========================================="
echo "  Inference Engine - Self-Hosted Runner Setup"
echo "=========================================="

# Configuration
RUNNER_DIR="$HOME/actions-runner"
REPO_URL="https://github.com/Muhammed-Yaseen-km/instance-repo"
WORK_DIR="$HOME/inference_engine"

# Check if runner token is provided
if [ -z "$1" ]; then
    echo ""
    echo "ERROR: Runner registration token required!"
    echo ""
    echo "To get the token:"
    echo "1. Go to: $REPO_URL/settings/actions/runners/new"
    echo "2. Copy the token from the configuration command"
    echo ""
    echo "Usage: ./setup-runner.sh <RUNNER_TOKEN>"
    echo ""
    exit 1
fi

RUNNER_TOKEN="$1"

echo ""
echo "[1/6] Creating runner directory..."
mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

echo ""
echo "[2/6] Downloading GitHub Actions Runner..."
RUNNER_VERSION="2.321.0"
curl -o actions-runner-linux-x64.tar.gz -L \
    "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"

echo ""
echo "[3/6] Extracting runner..."
tar xzf actions-runner-linux-x64.tar.gz
rm actions-runner-linux-x64.tar.gz

echo ""
echo "[4/6] Configuring runner..."
./config.sh --url "$REPO_URL" --token "$RUNNER_TOKEN" --name "salam-gpu" --labels "gpu,inference" --work "_work" --unattended

echo ""
echo "[5/6] Installing runner as system service..."
sudo ./svc.sh install
sudo ./svc.sh start

echo ""
echo "[6/6] Verifying setup..."
sudo ./svc.sh status

echo ""
echo "=========================================="
echo "  SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "The runner is now:"
echo "  ✓ Registered with GitHub"
echo "  ✓ Running as a system service"
echo "  ✓ Will auto-start on boot"
echo ""
echo "From now on, any push to main will:"
echo "  1. Trigger GitHub Actions"
echo "  2. Run directly on THIS machine"
echo "  3. Pull code + restart services automatically"
echo ""
echo "NO manual intervention needed ever again!"
echo ""
