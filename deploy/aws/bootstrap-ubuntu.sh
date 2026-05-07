#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/opt/smart-move"
BACKEND_ROOT="$APP_ROOT/backend"
VENV_ROOT="$APP_ROOT/.venv"

sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx

sudo mkdir -p "$APP_ROOT" /opt/smart-move/data
sudo chown -R "$USER":"$USER" "$APP_ROOT" /opt/smart-move/data

python3 -m venv "$VENV_ROOT"
"$VENV_ROOT/bin/pip" install --upgrade pip
"$VENV_ROOT/bin/pip" install -r "$BACKEND_ROOT/requirements.txt"

echo "Bootstrap complete. Next: copy .env, install systemd service, configure nginx, issue cert."
