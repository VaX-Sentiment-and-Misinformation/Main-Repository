# VaX — Vaccine Sentiment & Misinformation Analysis

A web app for analysing vaccine claims and public X (Twitter) posts. Type a claim or paste
a post URL and the app scores it for sentiment (stance on vaccines) and misinformation,
with an optional plain-language explanation from a local LLM. The Trends page charts
sentiment over time and shows the most popular recent vaccine posts.

**Stack:** Next.js frontend · FastAPI backend · two ModernBERT model microservices ·
optional Ollama LLM · optional Postgres on Supabase.

---

## 📁 Project Structure

```text
Main-Repository/
├── backend/
│   ├── main_api/              # Core web API — the one the frontend talks to (:8000)
│   │   ├── main.py            #   FastAPI app + routes
│   │   ├── sentiment.py       #   /analyse/sentiment -> sentiment service
│   │   ├── misinformation.py  #   /analyse/misinformation -> misinformation service + Ollama
│   │   ├── database.py        #   Engine + session handling (Supabase)
│   │   ├── models.py          #   SQLModel tables
│   │   ├── x_post_fetcher.py  #   Fetch a single X post from its URL (free, no key)
│   │   ├── x_api_search.py    #   Official X API search — paid, needs X_BEARER_TOKEN
│   │   └── apify/             #   Apify scraper: monthly history + last 7 days (paid)
│   ├── model_sentiment/       # Sentiment microservice (:8001) — weights not in git
│   ├── model_misinformation/  # Misinformation microservice (:8002) — weights not in git
│   ├── scripts/               # Build the Trends page / trending posts data
│   ├── scraper/
│   │   └── x-scraper.py       #   Offline bulk collector, for building training sets
│   ├── .env                   # Your secrets — never committed
│   └── .env.example           # Template for teammates — committed
├── data/                      # Training/reference datasets (CSV)
└── frontend/                  # Next.js app (App Router, Tailwind)
    └── src/
        ├── app/               #   Routes
        ├── components/        #   React components
        └── data/              #   Pre-built JSON for the Trends page and trending posts
```

Everything runs locally as plain processes. There is no Docker setup.

---

## ✅ Prerequisites

| Requirement | Notes |
|---|---|
| **Python** 3.10+ | |
| **Node.js** 20.9+ & npm | Next.js 16 won't start on older versions. |
| **Model weights** | `VaX-model-weights.zip` from the team Google Drive (about 1 GB). Not in git — see step 1.3. |
| **Ollama** | Optional. Only for the plain-language explanation on the result page. |
| **Supabase account** | Optional. Only for the `/api/post` and `/api/posts` endpoints, which the pages don't use. |

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

With the venv active:

```bash
pip install -r model_sentiment/requirements.txt
pip install fastapi uvicorn httpx python-dotenv sqlmodel psycopg2-binary
```

The first line covers both model services (their requirements are identical); the second
is everything `main_api` imports.

> ⚠️ Don't `pip install -r main_api/requirements.txt`. It was generated with `pip freeze`
> and pins `torch==2.10.0`, which conflicts with the `torch==2.14.0` the model services
> need in the same venv (see Developer Guidelines).

**1.3 Add the model weights**

The trained models are about 600 MB each, so they're kept out of git. Download
`VaX-model-weights.zip` from the team Google Drive and extract it **into the repo root**
(`Main-Repository/`). The zip already contains the `backend/...` folders, so it puts the
files in:

```text
backend/model_sentiment/modernbert_model_weighted2/final_model/
backend/model_misinformation/savedModel/final_model/
```

> On Windows, "Extract All" suggests a new folder named after the zip. Change the
> destination to the repo folder itself, or the files end up one level too deep.

**1.4 Ollama (optional)**

For the "why" explanation on the result page, install [Ollama](https://ollama.com), then:

```bash
ollama pull llama3.2:3b
```

Leave the Ollama app running. Without it, the result page still shows both scores.

**1.5 `.env` (optional)**

The app runs without a `.env`. You only need one for Fazli's database endpoints
(`DATABASE_URL`) or to refresh trending posts (`APIFY_TOKEN`):

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

For the database, get the string from the Supabase dashboard: **Connect** →
**Connection string** → **Session pooler**. Paste it into `backend/.env` and replace
`[YOUR-PASSWORD]`:

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

Tables are created automatically on startup when `DATABASE_URL` is set — there is no
migration step.

### 2. Frontend

From the repo root:

```bash
cd frontend
npm install
```

Only install in `frontend/`. The `package.json` at the repo root isn't used by the app.

---

## ▶️ Running the App

Four terminals, each starting from the repo root. Each backend command calls the venv's
`uvicorn` directly, so it works without activating the venv.

**Terminal 1 — sentiment model:**
```bash
cd backend/model_sentiment
../venv/bin/uvicorn app:app --port 8001          # Windows: ..\venv\Scripts\uvicorn app:app --port 8001
```

**Terminal 2 — misinformation model:**
```bash
cd backend/model_misinformation
../venv/bin/uvicorn app:app --port 8002          # Windows: ..\venv\Scripts\uvicorn app:app --port 8002
```

**Terminal 3 — main API:**
```bash
cd backend/main_api
../venv/bin/uvicorn main:app --reload            # Windows: ..\venv\Scripts\uvicorn main:app --reload
```
* API: <http://127.0.0.1:8000>
* Interactive API docs: <http://127.0.0.1:8000/docs>

**Terminal 4 — frontend:**
```bash
cd frontend
npm run dev
```
* Web app: <http://localhost:3000>

The model services take a few seconds to load their weights before they answer.

### Refreshing trending posts (optional, paid)

The "Trending posts" cards on the home and Trends pages are read from
`frontend/src/data/trendingPosts.json`, so they need nothing running. To rebuild them from
the last 7 days on X, put `APIFY_TOKEN` in `backend/.env` (about $0.40 per run), then:

```bash
cd backend/main_api
../venv/bin/python -m apify.fetch_week --out-dir ../../data/trending
cd ../..
backend/venv/bin/python backend/scripts/build_trending_posts.py data/trending/apify_vax_week-<date>.json
```

Commit the updated JSON so everyone gets it.

---

## 🔌 API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check. |
| `GET` | `/analyse/sentiment?q=...` | Sentiment of a claim, or of an X post if `q` is a post URL. Needs the sentiment service. |
| `GET` | `/analyse/misinformation?q=...` | Misinformation label and scores, same input as above. Needs the misinformation service. |
| `POST` | `/analyse/misinformation/explanation` | Plain-language reason for a label. Body: `{"text": "...", "label": "..."}`. Needs Ollama. |
| `POST` | `/api/post` | Fetch one X post by URL. Body: `{"url": "...", "refresh": false}`. Returns the stored row; `refresh: true` forces a re-fetch of a post already in the database. |
| `GET` | `/api/posts?limit=50` | Most recently fetched posts. |

`/api/post` and `/api/posts` need `DATABASE_URL`. Posts are cached in Postgres, so re-submitting the same link is served from the database
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
> `psycopg2-binary` and `python-dotenv`. Each service should list only what it imports.
> All the backend services share one venv, so a stray pin in one file (like that
> `torch==2.10.0`) breaks the others.

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
| `ModuleNotFoundError` on a package you installed | The venv isn't activated in this terminal. Look for `(venv)` in your prompt, or run the venv's programs directly as in **Running the App**. |
| `uvicorn: command not found` | Same cause. Use `../venv/bin/uvicorn` (Windows: `..\venv\Scripts\uvicorn`) from inside the service folder. |
| Result page says it couldn't reach the sentiment or misinformation model | That service isn't running (Terminal 1 or 2), or its weights are missing. Check step 1.3. |
| Model service fails with `OSError` / `Can't load ... final_model` | The weights aren't where the service looks. The `final_model` folders must be at the paths in step 1.3, not nested one level deeper. |
| Frontend shows "Could not reach the backend" | The API isn't running, or isn't on port 8000. Check Terminal 1. |
| `npm run build` fails prerendering `/result/result` (`Cannot read properties of undefined (reading 'ok')`) | The page components live in `src/pages/`, which Next also treats as the Pages Router directory, so it builds each file there as a separate route with no props. `npm run dev` is unaffected. Fix: move them into `src/components/` and update the imports in `src/app/*/page.tsx`. |

To test the database connection on its own:

```bash
cd backend/main_api
python -c "from dotenv import load_dotenv; load_dotenv('../.env'); from database import engine; from sqlalchemy import text; print(engine.connect().execute(text('select version()')).scalar())"
```
