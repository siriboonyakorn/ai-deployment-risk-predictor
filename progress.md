# Project Progress Log

> Updated after every work session. Most recent entry at the top.

---

## 2026-02-23 — Session 3: Full Dashboard UI

### What was built
- **Dark GitHub-style theme** — `globals.css` rewritten with CSS variables for background, surface, border, accent and risk colours.
- **Next.js API proxy** — `next.config.ts` now rewrites `/api/v1/*` → `http://localhost:8000/api/v1/*`, eliminating CORS issues.
- **Root redirect** — `app/page.tsx` redirects `/` → `/dashboard`.
- **Shared layout** — `app/(dashboard)/layout.tsx` wraps all dashboard pages with the sidebar.
- **Sidebar** (`components/Sidebar.tsx`) — fixed navigation, active route highlighting, "Soon" badges for future features (ML Analytics, PR Bot, Team).
- **API client** (`lib/api.ts`) — fully-typed fetch wrapper for health, repositories, commits and predictions endpoints.
- **RiskBadge** (`components/RiskBadge.tsx`) — colour-coded LOW / MEDIUM / HIGH badge with optional score.

### Pages (all returning HTTP 200)
| Route | File | Live data |
|---|---|---|
| `/dashboard` | `app/(dashboard)/dashboard/page.tsx` | Yes — `/health` polled every 30s, repo count live |
| `/repositories` | `app/(dashboard)/repositories/page.tsx` | Yes — list + import modal + delete |
| `/commits` | `app/(dashboard)/commits/page.tsx` | Yes — real GitHub API via backend, branch + pagination |
| `/predictions` | `app/(dashboard)/predictions/page.tsx` | Demo data — awaiting webhook pipeline |
| `/settings` | `app/(dashboard)/settings/page.tsx` | Static — API config form + roadmap sections |

---

## 2026-02-23 — Session 2: GitHub Integration Endpoints

### What was built
- **`GET /api/v1/health`** — enhanced with `uptime_seconds` and `db_status` fields. `APP_START_TIME` recorded in `main.py` at startup. DB connectivity checked via `SELECT 1`.
- **`POST /api/v1/repositories/import`** — accepts `github_url` + optional `branch`. Parses URL, fetches GitHub repo metadata and last 30 commits, upserts `Repository` DB record, returns everything in one response.
- **`GET /api/v1/repositories/{repo_id}/commits`** — fetches live commit history from GitHub API with `page`, `per_page` and `branch` query params.
- **`app/services/github.py`** — new service module: `parse_github_url`, `fetch_repo_metadata`, `fetch_commit_history`.
- **`GITHUB_TOKEN`** setting added to `config.py` (set in `.env` to raise rate limits / access private repos).
- **New schemas** — `RepoImportRequest`, `RepoImportResponse`, `GitHubRepoMetadata`, `GitHubCommitItem`, `CommitHistoryResponse`, `GitHubAuthor`.

### Fixed
- Installed `email-validator` into Python 3.14 interpreter (`pythoncore-3.14-64`) — fixes `ImportError` on startup.

---

## 2026-02-23 — Session 1: Project Scaffold

### What existed
- FastAPI backend with SQLAlchemy models (`User`, `Repository`, `Commit`, `RiskAssessment`).
- Basic health, predictions, repositories and webhooks routers.
- Blank Next.js 16 + TailwindCSS 4 frontend.
- Docker Compose config with PostgreSQL + Redis services.

### State at end of session
- Backend runnable via `python -m uvicorn app.main:app --reload` from `backend/`.
- SQLite used for local dev (auto-created as `dev.db`).
- Rule-based risk scorer (MVP) in `predictions.py` — scores 0-100 from lines changed, files changed and commit message keywords.
- Frontend on default Next.js boilerplate.

---

## Upcoming / Roadmap

- [ ] GitHub OAuth login flow
- [ ] Webhook auto-registration when repo is imported
- [ ] Populate real risk assessments via webhook pipeline
- [ ] scikit-learn Logistic Regression model (milestone 2)
- [ ] Graph Neural Network risk model
- [ ] PR comment bot
- [ ] Multi-repository analytics dashboard
- [ ] Team risk profiling
- [ ] Real-time anomaly detection
- [ ] Technical debt scoring
- [ ] SaaS billing integration
- [ ] Enterprise SSO
