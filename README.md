# VaX — Vaccine Sentiment & Misinformation Analysis

A web app for analysing public X (Twitter) posts about vaccines. Paste a post URL and the
app fetches the post, stores it, and (once the models are wired in) scores it for sentiment
and misinformation.

**Stack:** Next.js frontend · FastAPI backend · Postgres hosted on Supabase · two ML
microservices.

---

## 📁 Project Structure

```text
Main-Repository/
├── backend/
│   ├── main_api/              # Core web API — the one you run day to day
│   │   ├── main.py            #   FastAPI app + routes
│   │   ├── database.py        #   Engine + session handling (Supabase)
│   │   ├── models.py          #   SQLModel tables
│   │   ├── x_post_fetcher.py  #   Fetch a single X post from its URL (free, no key)
│   │   └── x_api_search.py    #   Official X API search — paid, needs X_BEARER_TOKEN
│   ├── model_sentiment/       # Sentiment microservice        (not implemented yet)
│   ├── model_misinformation/  # Misinformation microservice   (not implemented yet)
│   ├── scraper/
│   │   └── x-scraper.py       #   Offline bulk collector, for building training sets
│   ├── .env                   # Your secrets — never committed
│   └── .env.example           # Template for teammates — committed
├── data/                      # Training/reference datasets (CSV)
├── frontend/                  # Next.js app (App Router, Tailwind)
│   └── src/
│       ├── app/               #   Routes
│       └── components/        #   React components
└── docker-instructions.md     # Planned container architecture
```

---

## ✅ Prerequisites

| Requirement | Notes |
|---|---|
| **Python** 3.10+ | |
| **Node.js** 18+ & npm | |
| **Supabase account** | Free tier. The database is hosted — nothing to install locally. |

---

## 🛠️ First-Time Setup

Do this once per machine.

### 1. Backend

```bash
cd backend
```

**1.1 Create and activate a virtual environment**

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

> **What is `venv` for?** It gives this project its own private copy of Python's
> packages, in `backend/venv/`. Without it, `pip install` writes into your system-wide
> Python, so every project on your machine shares one set of versions — and two projects
> needing different versions of the same package can't both work. It also means
> `requirements.txt` describes *only* this project's dependencies, and deleting the
> `venv/` folder cleanly undoes everything. **You must activate it in every new terminal**
> — your prompt shows `(venv)` when it's active.

**1.2 Install dependencies**

```bash
pip install -r main_api/requirements.txt
```

**1.3 Configure your database connection**

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

Get the string from the Supabase dashboard: **Connect** → **Connection string** →
**Session pooler**. Paste it into `backend/.env` and replace `[YOUR-PASSWORD]`:

```env
DATABASE_URL="postgresql://postgres.<project-ref>:<password>@aws-<region>.pooler.supabase.com:5432/postgres"
```

> ⚠️ **Use the Session pooler, not the Direct connection.** On the free tier the direct
> connection (`db.<ref>.supabase.co`) is IPv6-only — IPv4 is a paid add-on — so on most
> home and campus networks it fails with `could not translate host name` or
> `Network is unreachable`. The session pooler is IPv4 on every tier and is meant for
> long-lived servers like this API. Don't use the **Transaction** pooler (port `6543`)
> either: it's for serverless and doesn't support prepared statements.

If your password contains `@ : / ? # %`, percent-encode it (`@` → `%40`), or the URL
parses incorrectly.

Tables are created automatically on first startup — there is no migration step.

### 2. Frontend

```bash
cd frontend
npm install
```

---

## ▶️ Running the App

Two terminals, both from the repo root.

**Terminal 1 — backend:**
```bash
cd backend/main_api
..\venv\Scripts\activate        # macOS/Linux: source ../venv/bin/activate
uvicorn main:app --reload
```
* API: <http://127.0.0.1:8000>
* Interactive API docs: <http://127.0.0.1:8000/docs>

**Terminal 2 — frontend:**
```bash
cd frontend
npm run dev
```
* Web app: <http://localhost:3000>

---

## 🔌 API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check. |
| `POST` | `/api/post` | Fetch one X post by URL. Body: `{"url": "...", "refresh": false}`. Returns the stored row; `refresh: true` forces a re-fetch of a post already in the database. |
| `GET` | `/api/posts?limit=50` | Most recently fetched posts. |

Posts are cached in Postgres, so re-submitting the same link is served from the database
rather than hitting X again. Errors: `400` for an unparseable URL, `404` for a post that
is deleted, private, or nonexistent.

---

## 📦 Developer Guidelines

**Adding a Python package.** Install it, then add it *by name* to the relevant
service's `requirements.txt`:

```bash
pip install <package>
```

> ⚠️ Don't use `pip freeze > requirements.txt`. It records every package in your venv,
> including transitive dependencies and anything you installed for unrelated work.
> `main_api/requirements.txt` currently lists torch, opencv, pandas and Jupyter this way —
> about 2.5 GB of installs for a service that needs only `fastapi`, `uvicorn`, `sqlmodel`,
> `psycopg2-binary` and `python-dotenv`. Each service should list only what it imports,
> which matters once these are separate containers.

**Secrets.** Never commit `.env`. It's covered by the root `.gitignore`. When you add a
new variable, add a placeholder version to `.env.example` and commit *that*, so teammates
know the variable exists. If a password is ever pushed, rotate it in Supabase — deleting
the commit is not enough.

**Ignore rules.** Put a rule in the `.gitignore` closest to what it ignores: Python, OS
and secret rules at the repo root; Next.js and npm rules in `frontend/.gitignore`.

---

## 🩺 Troubleshooting

| Symptom | Cause & fix |
|---|---|
| `could not translate host name` / `Network is unreachable` on startup | You're on the Direct connection string. Switch to the **Session pooler** (see 1.3). |
| `password authentication failed` | Password wrong, or a special character isn't percent-encoded. |
| `SSL connection has been closed unexpectedly` | The free-tier project paused after a week of inactivity. Unpause it in the dashboard; data is preserved. |
| `ModuleNotFoundError` on a package you installed | The venv isn't activated in this terminal. Look for `(venv)` in your prompt. |
| Frontend shows "Could not reach the backend" | The API isn't running, or isn't on port 8000. Check Terminal 1. |
| `next build` fails with `is not a module` | `src/pages/homepage/homepage.tsx` and `src/pages/result/result.tsx` are empty placeholder files. Because `src/pages/` is the Pages Router directory, Next treats them as routes and requires a default export. Delete them or move them into `src/components/`. |

To test the database connection on its own:

```bash
cd backend/main_api
python -c "from dotenv import load_dotenv; load_dotenv('../.env'); from database import engine; from sqlalchemy import text; print(engine.connect().execute(text('select version()')).scalar())"
```
