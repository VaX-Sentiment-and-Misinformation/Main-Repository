# AGENTS.md

Context for AI agents working in this repository. Read this before changing code.

`frontend/AGENTS.md` is a separate, **auto-generated** file written by `next dev` — don't
hand-edit it, and don't delete it from a diff (it regenerates).

---

## What this project is

**VaX — Vaccine Sentiment & Misinformation Analysis.** A Monash FIT3164 team project. The
product is a web app where you type a vaccine claim or paste a public X (Twitter) post URL;
the backend scores it for sentiment and misinformation using two fine-tuned ModernBERT
services, with an optional plain-language explanation from a local Ollama LLM. A Trends
page charts sentiment over time from pre-built JSON.

**Everything runs locally** — four processes on one machine, no Docker. Don't add
containers, a compose file or Dockerfiles; that plan was dropped. The "Reality check" table
below records what actually runs today.

---

## Tools and stack

| Layer | Tool | Version | Notes |
|---|---|---|---|
| API | FastAPI + uvicorn | 0.141.1 / 0.52.1 | `backend/main_api/main.py` |
| ORM | SQLModel on SQLAlchemy | 0.0.39 / 2.0.51 | SQLModel = Pydantic + SQLAlchemy |
| DB driver | psycopg2-binary | 2.9.12 | blocking, hence `def` not `async def` routes |
| Database | Postgres on **Supabase** | free tier | hosted; nothing to install locally |
| Config | python-dotenv | 1.2.2 | `backend/.env`, never committed |
| Frontend | **Next.js** (App Router) | **16.3.0** | see the Next 16 warning below |
| UI | React / TypeScript / Tailwind | 19.2.8 / 5 / **v4** | Tailwind v4 via `@tailwindcss/postcss` |
| Charts | recharts | 3.10.1 | `SentimentTrendChart.tsx` on the Trends page |
| Lint | ESLint + eslint-config-next | 9 / 16.3.0 | frontend only |
| X fetching | **Python stdlib only** | — | `urllib`, no `requests`; keep it that way |
| ML | torch + transformers, ModernBERT | 2.14.0 / 5.16.1 | `model_sentiment/`, `model_misinformation/` |
| Service calls | httpx | — | main_api → model services and Ollama |
| Explanation LLM | Ollama, `llama3.2:3b` | — | optional; result page works without it |

**Python is 3.13.2** in `backend/venv` (the README says 3.10+; the code uses `X | None`
unions and `list[dict]`, so 3.10 is the real floor). **All backend services share that one
venv.**

**Tests:** pytest, in `backend/main_api/tests/` (`pytest.ini` sets `pythonpath = .`). They
mock the model services, so they run without weights. pytest isn't in any
`requirements.txt` — `pip install pytest` first. There is no Python linter config and no CI.

---

## Commands

Everything below assumes the venv is active. **It must be activated in every new terminal**
(`(venv)` appears in the prompt); a `ModuleNotFoundError` on an installed package almost
always means it isn't.

Running the app takes four terminals. The model weights (~600 MB each) aren't in git:
`VaX-model-weights.zip` from the team Google Drive, extracted into the repo root, puts them
at `backend/model_sentiment/modernbert_model_weighted2/final_model/` and
`backend/model_misinformation/savedModel/final_model/`.

```bash
# terminal 1 - sentiment model, :8001
cd backend/model_sentiment
uvicorn app:app --port 8001

# terminal 2 - misinformation model, :8002
cd backend/model_misinformation
uvicorn app:app --port 8002

# terminal 3 - main API, :8000 (interactive docs at /docs)
cd backend/main_api
uvicorn main:app --reload

# terminal 4 - frontend, :3000
cd frontend
npm run dev
npm run build                     # see the src/pages/ trap below
npm run lint
```

Activate with `..\venv\Scripts\activate` (macOS/Linux: `source ../venv/bin/activate`), or
call `..\venv\Scripts\uvicorn` directly.

```bash
# tests
cd backend/main_api
python -m pytest
```

```bash
# is the database reachable?
cd backend/main_api
python -c "from dotenv import load_dotenv; load_dotenv('../.env'); from database import engine; from sqlalchemy import text; print(engine.connect().execute(text('select version()')).scalar())"
```

```bash
# paid official X API search (backend/main_api/x_api_search.py)
python x_api_search.py --count            # week's match volume; not billed per post
python x_api_search.py 10                 # ~$0.05 - smallest real fetch
python x_api_search.py --engagement 100   # ~$0.50 - writes x_posts_<stamp>.json
```

```bash
# bulk keyless collector (backend/scraper/x-scraper.py) - training data, not live
python x-scraper.py --from-file ids.csv --id-column id --out posts.jsonl --resume --workers 5
python x-scraper.py --from-file ids.csv --dry-run    # catches float64-mangled 19-digit IDs
```

**Adding a Python package:** install it, then add it *by name* to the right
`requirements.txt`. Never `pip freeze >`. `main_api/requirements.txt` was generated that
way and lists torch, opencv, pandas and Jupyter — ~2.5 GB for a service that needs only
fastapi, uvicorn, httpx, sqlmodel, psycopg2-binary and python-dotenv. Because every
service shares one venv, its frozen `torch==2.10.0` pin also conflicts with the
`torch==2.14.0` the model services need — **don't `pip install -r main_api/requirements.txt`**;
the README's setup installs `model_sentiment/requirements.txt` plus main_api's packages by
name.

---

## Architecture

**Next.js (:3000) → FastAPI main_api (:8000)**, which calls three local HTTP services and
one optional database:

| Service | Default URL (env override) | Notes |
|---|---|---|
| `model_sentiment` | `http://localhost:8001/predict` (`SENTIMENT_MODEL_URL`) | weights dir: `SENTIMENT_MODEL_DIR` |
| `model_misinformation` | `http://localhost:8002/predict` (`MISINFO_MODEL_URL`) | weights dir: `MISINFO_MODEL_DIR` |
| Ollama | `http://localhost:11434/api/generate` (`OLLAMA_URL`, `OLLAMA_MODEL`) | optional |
| Supabase Postgres | `DATABASE_URL` | optional; only `/api/post(s)` use it |

Both model services take `{"texts": [...]}` and return `{"predictions": [{label, score,
scores}]}`. They load weights once at startup, so they take a few seconds before answering.
main_api starts without `DATABASE_URL` — the analysis routes never touch the database.

### The normalised post dict is the central contract

This is the one thing worth understanding before editing anything. **Three** independent
sources of X posts all emit the *same* flat dict shape, and one classmethod consumes it:

```
x_post_fetcher.fetch_post()   ─┐
x-scraper.py  (bulk, by ID)   ─┼──▶  { id, url, text, created_at, likes, views,
x_api_search._normalise()     ─┘        author_handle, ..., "_backend": "..." }
                                              │
                                              ▼
                                  XPost.from_fetch()  ──▶  Postgres
```

Keep any new source in that shape and it drops into the database, the API and the frontend
type for free. `_backend` is the one renamed key — it becomes the `backend` column, because
SQLModel treats leading underscores as private.

### Two separate paths to X, with different economics

| | `x_post_fetcher.py` / `x-scraper.py` | `x_api_search.py` |
|---|---|---|
| Auth | none | `X_BEARER_TOKEN` |
| Cost | free | **~$0.005 per post returned** |
| Gets | one post by ID/URL | search over a rolling 7-day window |
| Backends | fxtwitter → syndication fallback | official API v2 |

The keyless path tries `api.fxtwitter.com` first, then X's own syndication embed endpoint.
**The syndication fallback cannot supply `views`** (hardcoded `None`), and `views` is null
throughout `labeled.jsonl` — so never rank or aggregate on `views`; use `likes`, which every
backend populates.

`x_api_search.py` ranks *locally* because the X API cannot sort by engagement at all
(`sort_order` accepts only `recency`/`relevancy`; there is no `min_faves:` in v2). It
requests `relevancy` so the pool it pays for skews toward high-engagement posts. **That bias
is deliberate and presentational** — it makes the output unsuitable as a representative
sample for the models, whose training corpora are keyword-and-time sampled. `count_recent()`
exists to quantify the gap: the broad vaccine query matches ~104k posts/week, so a 100-post
pool is ~0.1% and the result is "notable posts", not a true top 10.

### Database

One table, `XPost` (`models.py`), keyed on **the post's own ID as text** — so re-submitting
a link upserts via `session.merge()` instead of duplicating. Engagement counts are
`BigInteger` (a viral post exceeds INTEGER's 2.1 B ceiling); `created_at`/`fetched_at` are
`timestamptz`, because X returns a `+0000` offset that plain `timestamp` would discard.

`parse_x_time()` deliberately accepts **two** formats: X's legacy
`"Tue Mar 21 20:50:14 +0000 2006"` from the public backends, and ISO 8601 from the official
API. Parsing only the first silently nulls every API-sourced date.

Schema is created by `SQLModel.metadata.create_all()` at startup — **no Alembic, no
migrations**. `create_all` only ever adds tables; it never alters existing ones, so changing
a column type requires manual intervention.

**Predictions are meant to live in their own table keyed on `xpost.id`**, so a post can be
re-scored without rewriting its row. That table does not exist yet.

---

## Traps

- **`load_dotenv()` must run before `database.py` is imported.** `database.py` builds the
  engine at *import* time from `DATABASE_URL`. `main.py` does this and has `# noqa: E402`
  on the imports below it — don't "tidy" that import order.
- **Use the Supabase Session pooler** (port 5432), not Direct (IPv6-only on free tier → 
  `could not translate host name`) and not the Transaction pooler (6543, no prepared
  statements). Percent-encode `@ : / ? # %` in the password.
- **`SSL connection has been closed unexpectedly`** means the free-tier project paused after
  a week idle — unpause in the dashboard, data is preserved.
- **`npm run build` fails** prerendering `/result/result`. The App Router pages in `src/app/`
  import their view components from `src/pages/*/`, but `src/pages/` is also the Pages
  Router directory, so Next additionally builds each file there as its own route — and
  `result.tsx` crashes with no props (`Cannot read properties of undefined (reading 'ok')`).
  `npm run dev` is unaffected. The fix is to move those components out of `src/pages/`
  (e.g. under `src/components/`) and update the four imports.
- **Next.js 16 is newer than most training data.** `layout.tsx` already uses the
  `LayoutProps<"/">` global type. Check `node_modules/next/dist/docs/` before writing
  Next-specific code rather than relying on recalled App Router conventions.
- **Never commit `backend/.env`.** Add new variables to `.env.example` as placeholders. If a
  credential is ever pushed, rotate it in Supabase — deleting the commit is not enough.
- **Ignore rules go in the nearest `.gitignore`**: Python/OS/secrets at the root, Next/npm
  in `frontend/.gitignore`.

---

## Reality check — what actually exists

| Area | State |
|---|---|
| `GET /`, `GET /analyse/sentiment?q=`, `GET /analyse/misinformation?q=`, `POST /analyse/misinformation/explanation` | Working. `q` is a claim or a post URL (fetched via `x_post_fetcher`). |
| `POST /api/post`, `GET /api/posts` | Working, need `DATABASE_URL`. No page calls them. |
| `model_sentiment/`, `model_misinformation/` | Working FastAPI services; need the weights zip (not in git). `model_sentiment/` also holds training code (`modernbert.py`, `train_sentiment_colab.ipynb`). |
| `x_post_fetcher.py`, `x-scraper.py` | Working, keyless. |
| `x_api_search.py` | Working, but the X account is **`402 credits depleted`** (token itself is valid). |
| `main_api/apify/` | Paid Apify collector (`APIFY_TOKEN`): monthly history + last 7 days. |
| `backend/scripts/` | Offline: run the models over scrapes and build `frontend/src/data/*.json`. |
| Supabase connection | Configured; the table was still empty as of the last commit touching it. |
| Predictions table | Does not exist. Scores are computed per request, not stored. |
| Frontend | Home, result, trends and info pages. Trends and trending-post cards read pre-built JSON from `src/data/`, so they need no backend. |

**The only ordering anywhere in the served API is `fetched_at DESC`** on `/api/posts` —
there is no ranking, no score column, no pagination beyond a 200 cap.

---

## Data (`data/`, ~324 MB)

| Path | What it is |
|---|---|
| `misinformation/Labeled/VaxMisinfoData.csv` | 15,073 labelled IDs — 9,322 not-misinfo / 5,751 misinfo. The misinfo training set. |
| `misinformation/VaccineTweets/*.csv` | 35 weekly files of bare post IDs — a large dehydrated corpus. |
| `sentiment/sentimentvaccine1.csv` | 10,729 rows, vaccine-specific, `label` ∈ {-1, 0, 1} with annotator `agreement`. |
| `sentiment/twitter_*_sentiment.csv` | Generic Kaggle Twitter sentiment set — **not** vaccine-specific. |
| `misinfo_sentiment_predictions.csv` | 17,290 rows of model *output* (`predicted_sentiment`, `confidence`), rewritten by `backend/scripts/predict_sentiment.py`. |
| `backend/scraper/labeled.jsonl` | 9,405 posts rehydrated from the labelled IDs (10,000 attempted; the rest unreachable). |

These are **ID-and-time sampled, not popularity sampled** — which is why engagement-ranked
live data doesn't match their distribution.

Nothing yet bridges `labeled.jsonl` into Postgres. Model weights are never committed.

---

## Working with the team

Branch per person off `main`: `fazli-DB`, `fazli-scraper`, `kea-misinformation`,
`kea-frontend`, `jek-dataprocessing`, `input_validator`, `pagedesign`. Commit messages are
plain descriptive sentences — match that style.
