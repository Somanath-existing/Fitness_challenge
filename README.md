# FitChallenge

FitChallenge is a full-stack gamified fitness tracking application with activity logging, point-based scoring, daily streaks, performance tiers, real-time leaderboards, activity heatmaps, and AI-generated workout challenges and coaching insights.

---

## Table of Contents

- [Features](#features)
- [Architecture & Tech Stack](#architecture--tech-stack)
- [Project Structure](#project-structure)
- [Scoring Rules & Performance Tiers](#scoring-rules--performance-tiers)
- [Quick Start with Docker](#quick-start-with-docker)
- [Local Development Setup](#local-development-setup)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [Default Seed Accounts](#default-seed-accounts)
- [Environment Variables](#environment-variables)
- [API Overview](#api-overview)
- [Running Tests](#running-tests)
- [Deployment](#deployment)

---

## Features

- **Activity Tracking**: Log workouts for 6 supported sports (Running, Walking, Cycling, Gym, Swimming, Steps).
- **Automated Scoring**: Rule-based point system calculated automatically per activity.
- **Streak Calculation**: Timezone-aware streak tracking requiring continuous daily activity.
- **Performance Tiers & Badges**: Progression system (Rookie to Elite) and milestone badge awards.
- **Real-Time Leaderboard**: Live ranking updates delivered over WebSockets.
- **Activity Heatmap**: Rolling 365-day calendar visualization of daily points and workout consistency.
- **AI Challenges & Coaching**: Personalized daily challenges and training insights powered by Groq (LLaMA 3.3).
- **Social Features**: Friend requests, friends activity feed, and head-to-head streak comparisons.

---

## Architecture & Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11)
- **Database & ORM**: PostgreSQL 15, SQLModel (SQLAlchemy)
- **Migrations**: Alembic
- **Real-Time Updates**: Starlette WebSockets
- **Authentication**: JWT (JSON Web Tokens) with Argon2/bcrypt password hashing
- **AI Provider**: Groq API (`llama-3.3-70b-versatile`)

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Server State & Caching**: TanStack React Query
- **Charts & Visualizations**: Recharts, `react-activity-calendar`
- **Routing**: React Router v6

---

## Project Structure

```text
fitness-challenge/
├── apps/
│   ├── backend/
│   │   ├── alembic/              # Database migration scripts
│   │   ├── app/
│   │   │   ├── models/           # SQLModel database tables (User, Activity, Challenge, Friendship)
│   │   │   ├── routers/          # API route handlers (auth, activities, leaderboard, dashboard, etc.)
│   │   │   ├── services/         # Business logic (scoring, streaks, tiers, badges, insights)
│   │   │   ├── database.py       # Engine initialization and session dependency
│   │   │   ├── dependencies.py   # Auth and token validation dependencies
│   │   │   ├── schemas.py        # Pydantic request and response models
│   │   │   └── ws_manager.py     # WebSocket connection manager
│   │   ├── main.py               # FastAPI application entrypoint
│   │   ├── seed.py               # Database seeder for demo users and activities
│   │   └── requirements.txt      # Python dependencies
│   └── frontend/
│       ├── src/
│       │   ├── api/              # API client and endpoints (Axios)
│       │   ├── components/       # Reusable UI components
│       │   ├── pages/            # View pages (Leaderboard, Dashboard, Log, Challenges, Friends)
│       │   ├── stores/           # Zustand client state stores
│       │   └── types/            # TypeScript data contracts
│       ├── package.json          # Node dependencies and scripts
│       └── vite.config.ts        # Vite configuration
├── tests/                        # Backend test suite (API, scoring, streak, auth)
├── docker-compose.yml            # Local development orchestration
└── docker-compose.prod.yml       # Optional Docker Compose production setup
```

---

## Scoring Rules & Performance Tiers

### Point System
Points are calculated deterministically using the following conversion rates:

| Sport | Metric | Conversion Rate | Formula |
|---|---|---|---|
| **Running** | Distance (km) | 100 pts / km | `floor(km * 100)` |
| **Walking** | Distance (km) | 50 pts / km | `floor(km * 50)` |
| **Cycling** | Distance (km) | 25 pts / km | `floor(km * 25)` |
| **Swimming** | Duration (MM:SS) | 15 pts / min | `floor(seconds / 60) * 15` |
| **Gym** | Duration (MM:SS) | 5 pts / min | `floor(seconds / 60) * 5` |
| **Steps** | Step Count | 1 pt / 100 steps | `floor(steps / 100)` |

### Performance Tiers

| Tier | Required Total Points |
|---|---|
| **Rookie** | 0 – 500 pts |
| **Active** | 501 – 2,000 pts |
| **Athlete** | 2,001 – 5,000 pts |
| **Competitor** | 5,001 – 10,000 pts |
| **Elite** | 10,001+ pts |

---

## Quick Start with Docker

Prerequisites: [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

1. **Clone the repository and copy the environment configuration:**
   ```bash
   cp .env.example .env
   ```

2. **Add your Groq API key in `.env`:**
   ```env
   GROQ_API_KEY=gsk_your_groq_api_key_here
   ```

3. **Start the containers:**
   ```bash
   docker compose up --build
   ```

The database migrations will run and seed demo data automatically.

- **Frontend**: [http://localhost:5173](http://localhost:5173)
- **Backend API Docs (Swagger UI)**: [http://localhost:3001/docs](http://localhost:3001/docs)
- **Alternative API Docs (ReDoc)**: [http://localhost:3001/redoc](http://localhost:3001/redoc)

---

## Local Development Setup

### Backend Setup

Prerequisites: Python 3.11+ and PostgreSQL 15+.

1. **Navigate to the backend directory and create a virtual environment:**
   ```bash
   cd apps/backend
   python -m venv .venv
   ```

2. **Activate the virtual environment:**
   - Linux/macOS:
     ```bash
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     .venv\Scripts\Activate.ps1
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create a `.env` file in `apps/backend/` (or use the root `.env`):
   ```env
   DATABASE_URL=postgresql://fitness:fitness123@localhost:5432/fitness_challenge
   GROQ_API_KEY=gsk_your_groq_api_key
   SECRET_KEY=change_me_to_a_random_secret_key
   FRONTEND_URL=http://localhost:5173
   ENVIRONMENT=development
   ```

5. **Apply database migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Seed demo data:**
   ```bash
   python seed.py
   ```

7. **Start the API server:**
   ```bash
   uvicorn main:app --reload --port 3001
   ```

---

### Frontend Setup

Prerequisites: Node.js 18+ and npm.

1. **Navigate to the frontend directory:**
   ```bash
   cd apps/frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Set environment variables:**
   Create `.env` in `apps/frontend/`:
   ```env
   VITE_API_URL=http://localhost:3001
   ```

4. **Start the development server:**
   ```bash
   npm run dev
   ```

---

## Default Seed Accounts

When seeded, the database contains 10 demo athlete profiles with 30 days of workout history:

- **Password (for all demo accounts)**: `Password123!`
- **Sample Usernames**:
  - `alice_chen`
  - `bob_patel`
  - `priya_sharma`
  - `marcus_webb`
  - `sofia_rossi`
  - `kenji_tanaka`
  - `aisha_omar`
  - `luca_bianchi`
  - `mei_lin`
  - `arjun_nair`

---

## Environment Variables

| Variable | Scope | Required | Description |
|---|---|---|---|
| `DATABASE_URL` | Backend | Yes | PostgreSQL connection string (Neon in production; use Neon’s pooled URL and require SSL) |
| `GROQ_API_KEY` | Backend | Yes | Groq API key for challenge and insight generation |
| `SECRET_KEY` | Backend | Yes | Secret string used for signing JWT access tokens |
| `FRONTEND_URL` | Backend | Yes | Allowed frontend origin for CORS (Vercel production URL in production) |
| `ENVIRONMENT` | Backend | No | Execution mode (`development` or `production`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Backend | No | JWT lifespan in minutes (default: `30`) |
| `LOGIN_MAX_FAILURES` | Backend | No | Maximum failed attempts before account lockout (default: `5`) |
| `LOGIN_LOCKOUT_SECONDS` | Backend | No | Lockout duration in seconds (default: `900`) |
| `VITE_API_URL` | Frontend | Yes | Public base URL of the Render backend API (local default: `http://localhost:3001`) |

---

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | Authenticate user and receive JWT access token |
| `GET` | `/auth/me` | Fetch authenticated user profile |
| `POST` | `/activities` | Log a new workout activity and receive calculated points |
| `GET` | `/activities/user/{id}` | List activities for a user |
| `GET` | `/leaderboard` | View leaderboard rankings (supports sport and timeframe filters) |
| `GET` | `/dashboard/{id}` | Retrieve dashboard statistics, weekly trends, and heatmap data |
| `GET` | `/challenges/daily/{id}` | Fetch current daily challenges |
| `POST` | `/challenges/{id}/complete` | Mark a challenge complete and claim bonus points |
| `GET` | `/friends` | List accepted friends |
| `POST` | `/friends/request` | Send a friend request |
| `POST` | `/friends/accept` | Accept a pending friend request |
| `GET` | `/insights/{id}` | Retrieve personalized AI training tips |
| `GET` | `/health` | Service health check |
| `WS` | `/ws` | WebSocket endpoint for real-time leaderboard broadcasts |

---

## Running Tests

The test suite covers API endpoints, authentication, scoring logic, streaks, and tier calculations using an in-memory SQLite database.

From the repository root:

```bash
# In an activated Python virtual environment:
python -m pytest tests/ -v
```

---

## Deployment

The production app uses **Neon** for PostgreSQL, **Render** for the FastAPI backend, and **Vercel** for the React frontend.

### 1. Create the Neon database

1. Create a PostgreSQL project in [Neon](https://neon.tech/).
2. Copy the connection string from the Neon dashboard. Use the pooled connection string for the deployed backend, and make sure SSL is required (`sslmode=require`).
3. Keep the connection string private; add it as a Render environment variable rather than committing it to the repository.

### 2. Deploy the backend to Render

1. Create a Docker web service in [Render](https://render.com/) connected to this repository. Set the service root directory to `apps/backend` and the Dockerfile path to `Dockerfile`.
2. Configure these environment variables in the Render service:
   - `DATABASE_URL`: Neon PostgreSQL connection string.
   - `GROQ_API_KEY`: Groq API key used for AI challenges and insights.
   - `SECRET_KEY`: a long, randomly generated secret used to sign authentication tokens.
   - `FRONTEND_URL`: the production Vercel origin, for example `https://your-app.vercel.app` (no trailing slash).
   - `ENVIRONMENT`: `production`.
3. Deploy the service and confirm its `/health` endpoint responds successfully. The container runs Alembic migrations before starting the API; Render supplies the port through `PORT`.
4. Copy the public Render service URL; it is used by the frontend as `VITE_API_URL`.

### 3. Deploy the frontend to Vercel

1. Import the repository into [Vercel](https://vercel.com/), setting the project root directory to `apps/frontend`.
2. Set the production environment variable `VITE_API_URL` to the public Render backend URL (for example, `https://your-api.onrender.com`).
3. Deploy the project. The included `vercel.json` rewrites frontend routes to `index.html` for client-side routing.

### Continuous deployment

The GitHub Actions workflow in `.github/workflows/deploy.yml` triggers deployments on pushes to `main` when the corresponding app changes. Configure these repository secrets for the automated deployments:

- `RENDER_SERVICE_ID`
- `RENDER_API_KEY`
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

Configure the production environment variables in Render and Vercel themselves; do not store database credentials, API keys, or signing secrets in GitHub source files.
