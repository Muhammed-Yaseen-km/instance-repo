#!/bin/bash
# GPU Instance Setup Script for Inference Engine
# Run this ONCE on Salam's machine to set up everything

set -e

echo "=========================================="
echo "  Inference Engine - Initial Setup"
echo "=========================================="

# Step 1: Install Docker
echo ""
echo "[1/5] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "Docker installed. You may need to log out and back in."
else
    echo "Docker already installed"
fi

# Step 2: Install NVIDIA Container Toolkit
echo ""
echo "[2/5] Installing NVIDIA Container Toolkit..."
if ! dpkg -l | grep -q nvidia-container-toolkit; then
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    sudo apt-get update
    sudo apt-get install -y nvidia-container-toolkit
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker
else
    echo "NVIDIA toolkit already installed"
fi

# Step 3: Clone Repository
echo ""
echo "[3/5] Setting up repository..."
cd ~
if [ ! -d "inference_engine" ]; then
    git clone https://github.com/Muhammed-Yaseen-km/instance-repo.git inference_engine
else
    echo "Repository already exists"
fi
cd inference_engine

# Step 4: Setup environment
echo ""
echo "[4/5] Setting up environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env from example. Edit it with your settings."
else
    echo ".env already exists"
fi

# Step 5: Start services
echo ""
echo "[5/5] Starting services..."
docker compose up -d

echo ""
echo "=========================================="
echo "  SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "Verify with:"
echo "  nvidia-smi"
echo "  docker compose ps"
echo "  curl http://localhost:8000/api/v1/health"
echo ""
