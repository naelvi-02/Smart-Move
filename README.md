# ⚡ Smart Move - Research Intelligence

> **Next-Generation Intelligence Dashboard for LLM & Generative AI Assets**

![Smart Move Dashboard Preview](https://placehold.co/1200x630/030305/6366f1?text=Smart+Move+Intelligence&font=inter)

Smart Move is an advanced, internal research tool designed for analyzing, benchmarking, and simulating costs for Large Language Models (LLMs) and Image Generation Models. Built with a "Privacy-First" and "Safety-First" architecture, it allows researchers to probe models without generating sensitive content.

## 📡 Data Sources & Sync Model

- **LLM models** are sourced from **OpenRouter only**.
- **Image models** are sourced from **Civitai** and **Novita**.
- **Novita** is used for **image generation models only**.
- Sync is **on-demand**: pressing the sync button fetches the latest live data from each platform and updates the local database.
- The dashboard shows **per-source sync progress** so you can see which platform is still running.

## 🚀 Features

### 🌌 Ultra-Premium UI/UX
- **Cosmic Nebula Theme**: Deep void aesthetics with ambient gradient glows.
- **Glassmorphism Architecture**: Modern, frosted-glass interface components.
- **Fluid Animations**: Powered by `framer-motion` for seamless transitions.
- **Interactive Data**: `recharts` and custom visualizations.

### 🧠 Intelligence Modules
- **📊 Mission Control Dashboard**: Real-time overview of the model landscape using Bento Grid layout.
- **🤖 LLM Explorer**: Advanced filtering for Context Window, Pricing, Moderation, and Tier Suitability.
- **🎨 Image Model Explorer**: Style-based categorization (Anime, Realistic, 3D) with visual impact.
- **📈 Benchmark Probes**: Safe, neutral probing system to evaluate model compliance and instruction following.
- **💰 Cost Simulator**: Complex projection engine to estimate monthly operational costs across tiers (Free/Pro/Admin).

## 🛠 Tech Stack

- **Frontend**: Next.js 15 (App Router), TypeScript, Tailwind CSS 4, Framer Motion, Lucide React.
- **Backend**: FastAPI (Python), SQLAlchemy, Pydantic.
- **Database**: SQLite (Local) / PostgreSQL (Production ready).
- **APIs**: OpenRouter (LLM), Civitai (image), Novita AI (image only).

## 🖥 Desktop App Build & Updates

- The desktop shell uses **Tauri** so it stays lightweight on lower-end laptops.
- GitHub Actions builds the Windows installer and publishes it as a GitHub Release.
- The app includes an **update checker** that looks at GitHub Releases.
- Signed auto-updates are planned through Tauri’s updater system.
- To enable fully automatic in-app updates, you must generate and configure the Tauri signing keys.

## ☁️ VPS Production Mode

For public/internal desktop distribution, do **not** bundle provider API keys into the Tauri app. Put them on your VPS instead.

- Run the FastAPI backend on your VPS with your real provider secrets.
- Point the desktop release to your VPS API URL at build time.
- In VPS mode, the desktop app skips the local Python sidecar and talks directly to your server.

Recommended production flow:

1. Deploy `backend/` to your VPS.
2. Set backend env vars on the VPS:

```env
OPENROUTER_API_KEY=your_key_here
NOVITA_API_KEY=your_key_here
CIVITAI_API_KEY=your_key_here
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/smart_move
```

3. Put your API behind HTTPS, for example `https://api.smartmove.yourdomain.com`.
4. Add a GitHub repository variable named `SMART_MOVE_REMOTE_API_URL` with that HTTPS URL.
5. Push a new desktop release tag. GitHub Actions will bake that URL into the desktop build.

Full AWS VPS notes: `docs/aws-vps-deploy.md`

Auto-deploy notes: `docs/github-vps-autodeploy.md`

Notes:

- Desktop dev still uses the local sidecar by default.
- Desktop releases use the VPS URL only when `SMART_MOVE_REMOTE_API_URL` is set.
- CORS already allows `tauri://localhost` and `https://tauri.localhost` for desktop webviews.

## 🏁 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.10+

### 1. Backend Setup
```bash
cd backend
python -m venv venv
# Windows
.\venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn main:app --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 3. Environment Variables
Create a `.env` file in the root directory for local backend development:
```env
OPENROUTER_API_KEY=your_key_here
NOVITA_API_KEY=your_key_here
CIVITAI_API_KEY=optional
DATABASE_URL=sqlite:///./smart_move.db
```

> Note: `NOVITA_API_KEY` is used for image-model sync only.

### 4. Desktop Build

```bash
npm install
npm install --prefix frontend
npm run build
```

For release builds, push a tag like `v0.1.1` and let GitHub Actions generate the Windows installer.

### 5. GitHub Release Secrets

Add these repository secrets before publishing desktop releases:

- `TAURI_SIGNING_PRIVATE_KEY` = full contents of `C:\Users\Nopal\.tauri\smart-move.key`
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` = password you entered while generating the signing key

The public key is already stored in `src-tauri/tauri.conf.json` for update verification.

### 6. GitHub Release Variable For VPS Routing

If you want desktop builds to call your VPS backend instead of the bundled local sidecar, add this repository variable:

- `SMART_MOVE_REMOTE_API_URL` = `https://api.smartmove.yourdomain.com`

When this variable is present during the GitHub Actions build:

- the frontend uses the VPS URL inside the Tauri app
- the Rust shell skips spawning the local Python backend sidecar

## 🔒 Safety Protocols
This tool is strictly for **research and metadata analysis**.
- No generation of NSFW content.
- No storage of sensitive prompts.
- All benchmarks use neutral, synthetic queries.

---

*Built with ❤️ by DeepMind & Nopal*
