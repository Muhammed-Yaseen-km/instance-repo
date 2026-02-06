#!/bin/bash
# ============================================
# FULLY AUTOMATED: GitHub Actions Self-Hosted Runner
# Just run: ./setup-runner.sh
# ============================================

set -e

echo "=========================================="
echo "  Inference Engine - Automated Runner Setup"
echo "=========================================="

# Configuration
RUNNER_DIR="$HOME/actions-runner"
REPO="Muhammed-Yaseen-km/instance-repo"
WORK_DIR="$HOME/inference_engine"

# Step 1: Check/Install GitHub CLI
echo ""
echo "[1/7] Checking GitHub CLI..."
if ! command -v gh &> /dev/null; then
    echo "Installing GitHub CLI..."
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
    sudo apt update && sudo apt install gh -y
fi
echo "✓ GitHub CLI installed"

# Step 2: Authenticate with GitHub (if needed)
echo ""
echo "[2/7] Checking GitHub authentication..."
if ! gh auth status &> /dev/null; then
    echo "Please authenticate with GitHub:"
    gh auth login
fi
echo "✓ Authenticated with GitHub"

# Step 3: Get runner registration token automatically
echo ""
echo "[3/7] Getting runner registration token..."
RUNNER_TOKEN=$(gh api -X POST "repos/${REPO}/actions/runners/registration-token" --jq '.token')
if [ -z "$RUNNER_TOKEN" ]; then
    echo "ERROR: Failed to get runner token. Make sure you have admin access to the repo."
    exit 1
fi
echo "✓ Token retrieved"

# Step 4: Download runner
echo ""
echo "[4/7] Downloading GitHub Actions Runner..."
mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

RUNNER_VERSION="2.321.0"
if [ ! -f "run.sh" ]; then
    curl -sL -o actions-runner.tar.gz \
        "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
    tar xzf actions-runner.tar.gz
    rm actions-runner.tar.gz
fi
echo "✓ Runner downloaded"

# Step 5: Configure runner
echo ""
echo "[5/7] Configuring runner..."
./config.sh --url "https://github.com/${REPO}" \
    --token "$RUNNER_TOKEN" \
    --name "salam-gpu-$(hostname)" \
    --labels "self-hosted,gpu,inference" \
    --work "_work" \
    --unattended \
    --replace

echo "✓ Runner configured"

# Step 6: Install as service
echo ""
echo "[6/7] Installing as system service..."
sudo ./svc.sh install || true
sudo ./svc.sh start
echo "✓ Service started"

# Step 7: Verify
echo ""
echo "[7/7] Verifying setup..."
sudo ./svc.sh status

echo ""
echo "=========================================="
echo "  ✅ FULLY AUTOMATED SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "From now on, every 'git push' to main will:"
echo "  → Automatically pull code to this machine"
echo "  → Automatically restart Docker services"
echo "  → Zero manual intervention needed"
echo ""
