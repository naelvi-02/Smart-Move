# AWS VPS Deploy

Recommended public API host: `api.naelvi.com`.

## 1. EC2 baseline

- Ubuntu 22.04 or 24.04
- Open inbound ports: `22`, `80`, `443`
- Point DNS `A` record `api.naelvi.com` to your EC2 public IP

## 2. Copy project

Suggested target:

```bash
/opt/smart-move
```

Copy only what the backend needs, at minimum:

- `backend/`
- `deploy/aws/`

If you use `git` on the server:

```bash
sudo mkdir -p /opt/smart-move
sudo chown -R ubuntu:ubuntu /opt/smart-move
cd /opt/smart-move
git clone <your-repo-url> .
```

## 3. Bootstrap packages

```bash
cd /opt/smart-move
bash deploy/aws/bootstrap-ubuntu.sh
```

## 4. Create backend env

```bash
cp deploy/aws/backend.env.example backend/.env
nano backend/.env
```

Fill real values:

```env
OPENROUTER_API_KEY=...
CIVITAI_API_KEY=...
NOVITA_API_KEY=...
DATABASE_URL=sqlite:////opt/smart-move/data/smart_move.db
```

## 5. Install systemd service

```bash
sudo cp deploy/aws/smart-move-backend.service /etc/systemd/system/smart-move-backend.service
sudo systemctl daemon-reload
sudo systemctl enable smart-move-backend
sudo systemctl start smart-move-backend
sudo systemctl status smart-move-backend
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## 6. Configure nginx

```bash
sudo cp deploy/aws/nginx-smart-move.conf /etc/nginx/sites-available/smart-move
sudo ln -s /etc/nginx/sites-available/smart-move /etc/nginx/sites-enabled/smart-move
sudo nginx -t
sudo systemctl reload nginx
```

## 7. Issue SSL cert

```bash
sudo certbot --nginx -d api.naelvi.com
```

Then verify:

```bash
curl https://api.naelvi.com/health
```

## 8. Connect desktop releases to VPS

Set GitHub repo variable:

- `SMART_MOVE_REMOTE_API_URL=https://api.naelvi.com`

After that, push the next desktop release tag. The Tauri app will:

- call the VPS API directly
- skip the local Python sidecar in production

## 9. Useful commands

Logs:

```bash
sudo journalctl -u smart-move-backend -f
```

Restart backend:

```bash
sudo systemctl restart smart-move-backend
```

Reinstall Python deps after pull:

```bash
/opt/smart-move/.venv/bin/pip install -r /opt/smart-move/backend/requirements.txt
sudo systemctl restart smart-move-backend
```
