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
Create a `.env` file in the root directory:
```env
OPENROUTER_API_KEY=your_key_here
NOVITA_API_KEY=your_key_here
CIVITAI_API_KEY=optional
DATABASE_URL=sqlite:///./smart_move.db
```

> Note: `NOVITA_API_KEY` is used for image-model sync only.

## 🔒 Safety Protocols
This tool is strictly for **research and metadata analysis**.
- No generation of NSFW content.
- No storage of sensitive prompts.
- All benchmarks use neutral, synthetic queries.

---

*Built with ❤️ by DeepMind & Nopal*
