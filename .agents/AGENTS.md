# Smart Move Custom Rules

## Deployment
- **CI/CD Pipeline**: The project uses GitHub Actions (`deploy-backend.yml`).
- Whenever backend code is pushed to the `main` branch, the VPS automatically pulls the changes and restarts the `smart-move-backend` systemd service.
- **NEVER** instruct the user to manually run `git pull` or `sudo systemctl restart smart-move-backend` on the VPS after a push. The server updates itself automatically.
