# GitHub VPS Auto Deploy

This workflow deploys backend changes from `main` to the VPS automatically.

Workflow file:

- `.github/workflows/deploy-backend.yml`

It runs only when these paths change:

- `backend/**`
- `deploy/aws/**`
- `.github/workflows/deploy-backend.yml`

## Required GitHub Secrets

Add these in GitHub:

- `VPS_HOST` = `api.naelvi.com` or your VPS IP
- `VPS_USER` = `ubuntu`
- `VPS_SSH_KEY` = private SSH key content
- `VPS_PORT` = `22` (optional, but recommended)

## What the workflow does

On every matching push to `main`:

1. SSH into the VPS
2. Reset repo to `origin/main`
3. Reinstall backend requirements
4. Re-copy nginx config
5. Validate nginx config
6. Restart `smart-move-backend`
7. Reload nginx

## Important

- The VPS repo path is assumed to be `/opt/smart-move`
- Python venv is assumed to be `/opt/smart-move/.venv`
- Backend service is assumed to be `smart-move-backend`
- Nginx site is assumed to be `/etc/nginx/sites-available/smart-move`

## Recommended SSH key setup

Create a dedicated deploy key pair on your local machine, then put the public key into:

```bash
~/.ssh/authorized_keys
```

on the VPS `ubuntu` user.

Store the private key as the GitHub secret `VPS_SSH_KEY`.
