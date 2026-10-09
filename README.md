# FitChallenge 🏃

Gamified fitness tracking — live leaderboard, AI daily challenges, badges, friends, and coaching insights.

## Quick start (Docker — one command)

```bash
cp .env.example .env
# Add your GROQ_API_KEY to .env
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API + Swagger: http://localhost:3001/docs
- ReDoc: http://localhost:3001/redoc

## Local dev without Docker

### Backend
```bash
cd apps/backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL and GROQ_API_KEY
alembic upgrade head
python seed.py
uvicorn main:app --reload --port 3001
```

### Frontend
```bash
cd apps/frontend
npm install
cp .env.example .env
npm run dev
```

## Run tests
```bash
cd apps/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ../..
python -m pytest tests/ -v
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | From https://console.groq.com (free) |
| `DATABASE_URL` | Yes | Postgres connection string |
| `FRONTEND_URL` | Yes | CORS allowed origin |
| `SECRET_KEY` | Yes | Random hex string (python -c "import secrets; print(secrets.token_hex(32))") |
| `VITE_API_URL` | Frontend | Backend base URL (baked in at build time) |

## Deploy

**Backend → Fly.io**
```bash
cd apps/backend
fly launch
fly secrets set GROQ_API_KEY=gsk_... DATABASE_URL=postgresql://... FRONTEND_URL=https://your-app.vercel.app SECRET_KEY=...
fly deploy
```

**Frontend → Vercel**
- Import repo, set build env var `VITE_API_URL=https://your-app.fly.dev`

## Tech stack
- **Backend**: Python 3.11, FastAPI, SQLModel, Alembic, PostgreSQL 15, Groq AI
- **Frontend**: React 18, Vite, TypeScript, TailwindCSS, TanStack Query, Recharts
- **Infra**: Docker Compose (local), Fly.io (backend), Vercel (frontend), Neon (production DB)
