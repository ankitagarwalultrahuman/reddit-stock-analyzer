#!/bin/bash
# One-time VPS setup script
# Run on VPS as root

set -e

echo "=== Installing system packages ==="
apt update && apt install -y nginx apache2-utils

echo "=== Setting up basic auth ==="
echo "Enter username for dashboard:"
read -r USERNAME
htpasswd -c /etc/nginx/.htpasswd "$USERNAME"

echo "=== Creating directories ==="
mkdir -p /var/www/brodus.tech/out
mkdir -p /opt/reddit-stock-analyzer

echo "=== Installing systemd service ==="
cp /opt/reddit-stock-analyzer/deploy/stock-api.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable stock-api

echo "=== Installing nginx config ==="
cp /opt/reddit-stock-analyzer/deploy/nginx-brodus.conf /etc/nginx/sites-available/brodus.tech
ln -sf /etc/nginx/sites-available/brodus.tech /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo "=== Setup complete ==="
echo "Next steps:"
echo "1. Run deploy.sh from your Mac to deploy the app"
echo "2. Disable the old Streamlit service: systemctl disable --now streamlit"
