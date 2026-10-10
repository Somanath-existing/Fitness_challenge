# FitChallenge

A full-stack fitness tracking app. Log workouts, earn points, compete on a leaderboard, track streaks, and get AI coaching insights.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Scoring & Tiers](#scoring--tiers)
- [Quick Start (Docker)](#quick-start-docker)
- [Local Development](#local-development)
- [Seed Accounts](#seed-accounts)
- [Environment Variables](#environment-variables)
- [API Routes](#api-routes)
- [Tests](#tests)
- [Deployment](#deployment)

---

## Features

- Log activities for 6 sports: Running, Walking, Cycling, Gym, Swimming, Steps
- Points calculated automatically per activity
- Daily streak tracking (timezone-aware)
- Five performance tiers: Rookie → Active → Athlete → Competitor → Elite
- Milestone badges awarded at point thresholds
- Real-time leaderboard via WebSocket
- 365-day activity heatmap
- AI coaching insights powered by Groq (cached 1 hour per user, falls back to generic tips on API failure)
- AI-generated daily challenges
- Friend requests and friends activity feed

---

## Tech Stack

**Backend**
- FastAPI (Python 3.11)
- PostgreSQL + SQLModel (SQLAlchemy)
- Alembic migrations
- JWT authentication, bcrypt password hashing
- Groq API for AI insights and challenges

**Frontend**
- React 18 + TypeScript
- Vite
- Tailwind CSS
- Zustand (client state), TanStack React Query (server state)
- Recharts, react-activity-calendar
- React Router v6

---

## Project Structure

```
fitness-challenge/
├── apps/
│   ├── backend/
│   │   ├── alembic/            # DB migrations
│   │   ├── app/
│   │   │   ├── models/         # SQLModel tables (User, Activity, Challenge, Friendship)
│   │   │   ├── routers/        # Route handlers
│   │   │   ├── services/       # Business logic (scoring, streaks, tiers, badges, insights)
│   │   │   ├── database.py
│   │   │   ├── dependencies.py # Auth + rate limiting
│   │   │   ├── schemas.py
│   │   │   └── ws_manager.py
│   │   ├── main.py
│   │   ├── seed.py
│   │   └── requirements.txt
│   └── frontend/
│       ├── src/
│       │   ├── api/
│       │   ├── components/
│       │   ├── pages/
│       │   ├── stores/
│       │   └── types/
│       ├── package.json
│       └── vite.config.ts
├── tests/                      # pytest suite (API, auth, scoring, streaks, tiers, challenges)
├── docker-compose.yml
└── docker-compose.prod.yml
```

---

## Scoring & Tiers

### Points per activity

| Sport | Input | Rate | Formula |
|---|---|---|---|
| Running | km | 100 pts/km | `floor(km × 100)` |
| Walking | km | 50 pts/km | `floor(km × 50)` |
| Cycling | km | 25 pts/km | `floor(km × 25)` |
| Swimming | MM:SS | 15 pts/min | `floor(seconds ÷ 60) × 15` |
| Gym | MM:SS | 5 pts/min | `floor(seconds ÷ 60) × 5` |
| Steps | count | 1 pt/100 steps | `floor(steps ÷ 100)` |

### Performance tiers

| Tier | Points |
|---|---|
| Rookie | 0 – 500 |
| Active | 501 – 2,000 |
| Athlete | 2,001 – 5,000 |
| Competitor | 5,001 – 10,000 |
| Elite | 10,001+ |

---

## Quick Start (Docker)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
cp .env.example .env
# Add your GROQ_API_KEY to .env
docker compose up --build
```

- Frontend: http://localhost:5173
- API docs: http://localhost:3001/docs

---

## Local Development

### Backend

Requires Python 3.11+ and PostgreSQL.

```bash
cd apps/backend
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Create `apps/backend/.env`:
```env
DATABASE_URL=postgresql://fitness:fitness123@localhost:5432/fitness_challenge
GROQ_API_KEY=gsk_your_key_here
SECRET_KEY=your_random_secret
FRONTEND_URL=http://localhost:5173
ENVIRONMENT=development
```

```bash
alembic upgrade head
python seed.py
uvicorn main:app --reload --port 3001
```

### Frontend

Requires Node.js 18+.

```bash
cd apps/frontend
npm install
```

Create `apps/frontend/.env`:
```env
VITE_API_URL=http://localhost:3001
```

```bash
npm run dev
```

---

## Seed Accounts

After running `python seed.py`, 10 demo accounts are created with 30 days of activity history.

**Password for all accounts:** `Password123!`

Usernames: `alice_chen`, `bob_patel`, `priya_sharma`, `marcus_webb`, `sofia_rossi`, `kenji_tanaka`, `aisha_omar`, `luca_bianchi`, `mei_lin`, `arjun_nair`

---

## Environment Variables

| Variable | Where | Required | Notes |
|---|---|---|---|
| `DATABASE_URL` | Backend | Yes | PostgreSQL connection string |
| `GROQ_API_KEY` | Backend | Yes | For AI insights and challenges |
| `SECRET_KEY` | Backend | Yes | Signs JWT tokens |
| `FRONTEND_URL` | Backend | Yes | Allowed CORS origin (comma-separated for multiple) |
| `ENVIRONMENT` | Backend | No | `development` or `production` (default: `development`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Backend | No | JWT lifespan (default: `30`) |
| `LOGIN_RATE_LIMIT_MAX` | Backend | No | Max login attempts per 5 min per IP (default: `30`) |
| `REGISTER_RATE_LIMIT_MAX` | Backend | No | Max registrations per hour per IP (default: `30`) |
| `INSIGHTS_RATE_LIMIT_MAX` | Backend | No | Max insight requests per hour per IP (default: `30`) |
| `DAILY_CHALLENGE_RATE_LIMIT_MAX` | Backend | No | Max challenge requests per window per IP (default: `20`) |
| `LOGIN_MAX_FAILURES` | Backend | No | Failed attempts before account lockout (default: `5`) |
| `LOGIN_LOCKOUT_SECONDS` | Backend | No | Lockout duration in seconds (default: `900`) |
| `VITE_API_URL` | Frontend | Yes | Backend API base URL |

---

## API Routes

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/users` | Register a new account |
| `POST` | `/api/auth/login` | Login, returns JWT + sets httpOnly cookie |
| `POST` | `/api/auth/logout` | Clear auth cookie |
| `GET` | `/api/auth/me` | Current user profile |
| `POST` | `/api/activities` | Log an activity |
| `GET` | `/api/activities/user/{id}` | List activities for a user |
| `GET` | `/api/leaderboard` | Leaderboard (supports sport + scope filters) |
| `GET` | `/api/dashboard/{id}` | Dashboard stats, heatmap, streak |
| `GET` | `/api/challenges/daily/{id}` | Get today's challenges |
| `POST` | `/api/challenges/{id}/complete` | Complete a challenge |
| `GET` | `/api/insights/{id}` | AI coaching insights (cached 1 hr) |
| `GET` | `/api/friends` | List friends |
| `POST` | `/api/friends/request` | Send a friend request |
| `POST` | `/api/friends/{id}/respond` | Accept or decline a request |
| `GET` | `/health` | Health check |
| `WS` | `/ws` | WebSocket — real-time leaderboard updates |

---

## Tests

```bash
python -m pytest tests/ -v
```

Covers: API endpoints, authentication, scoring, streak logic, tier calculations, challenge metrics.

---

## Deployment

Production runs on **Neon** (PostgreSQL), **Render** (backend), and **Vercel** (frontend).

### 1. Neon

Create a PostgreSQL project at [neon.tech](https://neon.tech). Use the pooled connection string with `sslmode=require`.

### 2. Render

Create a Docker web service pointing to `apps/backend/Dockerfile`. Set these environment variables in Render:

- `DATABASE_URL` — Neon connection string
- `GROQ_API_KEY`
- `SECRET_KEY`
- `FRONTEND_URL` — your Vercel URL, e.g. `https://your-app.vercel.app`
- `ENVIRONMENT=production`

The container runs Alembic migrations on startup before the API starts.

### 3. Vercel

Import the repo and set the root directory to `apps/frontend`. The included `vercel.json` handles client-side routing rewrites.

### CI/CD

GitHub Actions (`.github/workflows/deploy.yml`) deploys on pushes to `main` when the relevant app files change.

Required repository secrets:

- `RENDER_SERVICE_ID`
- `RENDER_API_KEY`
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

The workflow fetches the Render service URL at build time and injects it into the Vercel build as `VITE_API_URL` automatically.
