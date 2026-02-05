#!/bin/bash
# AWS GPU Instance Setup Script for Inference Engine
# Run this after SSH'ing into your instance

set -e  # Exit on error

echo "=== Step 1: Installing Docker ==="
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

echo "=== Step 2: Installing NVIDIA Container Toolkit ==="
# Add NVIDIA repo
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker to use NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

echo "=== Step 3: Cloning Repository ==="
cd ~
git clone https://github.com/Muhammed-Yaseen-km/instance-repo.git inference_engine
cd inference_engine

echo "=== Step 4: Creating .env file ==="
cp .env.example .env

echo "=== Step 5: Starting Services ==="
sudo docker-compose up -d

echo "=== Step 6: Checking GPU ==="
nvidia-smi

echo ""
echo "=== SETUP COMPLETE ==="
echo "API running at: http://$(curl -s ifconfig.me):5000"
echo ""
echo "Test with: curl http://localhost:5000/api/v1/health"
echo "View logs: sudo docker-compose logs -f"
