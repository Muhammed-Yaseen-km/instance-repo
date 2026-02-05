#!/bin/bash
# Quick deploy script - run after pushing changes from local
# Usage: ./deploy.sh

cd ~/inference_engine
echo "Pulling latest changes..."
git pull

echo "Rebuilding and restarting services..."
sudo docker-compose up -d --build

echo "Showing logs (Ctrl+C to exit)..."
sudo docker-compose logs -f --tail=50
