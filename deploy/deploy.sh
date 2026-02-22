#!/bin/bash
# Deploy script - run from your Mac
# Usage: ./deploy/deploy.sh

set -e

VPS_HOST="root@brodus.tech"
VPS_DIR="/opt/reddit-stock-analyzer"
WEB_DIR="/var/www/brodus.tech/out"

echo "=== Building frontend ==="
cd frontend
npm run build
cd ..

echo "=== Syncing Python backend ==="
rsync -avz --exclude '__pycache__' --exclude '*.pyc' --exclude 'node_modules' --exclude '.git' --exclude 'frontend/node_modules' --exclude 'frontend/.next' --exclude 'frontend/out' \
    ./ ${VPS_HOST}:${VPS_DIR}/

echo "=== Syncing static frontend ==="
rsync -avz --delete frontend/out/ ${VPS_HOST}:${WEB_DIR}/

echo "=== Installing Python dependencies on VPS ==="
ssh ${VPS_HOST} "cd ${VPS_DIR} && source venv/bin/activate && pip install -r requirements.txt -q"

echo "=== Restarting FastAPI service ==="
ssh ${VPS_HOST} "systemctl restart stock-api"

echo "=== Reloading nginx ==="
ssh ${VPS_HOST} "nginx -t && systemctl reload nginx"

echo "=== Deployment complete ==="
echo "Visit: https://brodus.tech"
