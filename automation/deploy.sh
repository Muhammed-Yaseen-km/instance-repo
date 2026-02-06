#!/bin/bash
# Deploy script - pull latest and restart services
# Usage: ./deploy.sh

set -e
cd ~/inference_engine

echo "=========================================="
echo "  Deploying Inference Engine"
echo "=========================================="

echo "[1/4] Pulling latest code..."
git pull origin main

echo "[2/4] Restarting Docker services..."
docker compose down
docker compose up -d --build

echo "[3/4] Waiting for services..."
sleep 15

echo "[4/4] Verifying..."
docker compose ps
curl -s --max-time 10 http://localhost:8000/api/v1/health || echo "Health check pending..."

echo ""
echo "=========================================="
echo "  DONE!"
echo "=========================================="
