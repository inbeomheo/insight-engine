# Insight Engine

[한국어](README.md) · **English**

Installation, configuration, and operations documentation is maintained in both languages. Update both versions together when changing commands, environment variables, or security warnings.

An AI learning engine that turns YouTube videos, documents, and text into learning materials and an LLMWiki-style knowledge wiki. Generation uses CLIProxyAPI through an OpenAI-compatible interface, with Korean, English, and Japanese output, retrieval-augmented generation (RAG: using stored knowledge as reference), and team workspaces.

Flask + Next.js · LiteLLM · CLIProxyAPI · pytest + Vitest + Playwright

---

## Features

### Core

- **Four output styles:** Summary, Q&A, Quiz, and Retention Cards.
- **One AI connection:** CLIProxyAPI connects an authenticated AI service through a common, OpenAI-compatible API.
- **Multilingual output:** Korean, English, and Japanese.
- **Four transcript fallbacks:** youtube-transcript-api → watch-page parsing → Supadata API → local Whisper speech recognition.

### Content Generation

- **Batch processing:** Analyze up to 10 URLs concurrently.
- **Multiple styles:** Generate multiple styles from one URL.
- **Fusion analysis:** Cross-analyze multiple sources.
- **Automated pipelines:** Transcript extraction → learning-note generation, with server-sent events (SSE: incremental server updates).
- **Source citations:** `[MM:SS]` timestamps linked to YouTube.
- **Automatic chapters:** Split transcripts into topical chapters.
- **Parallel comment analysis:** Generate the main content and a comment summary concurrently.

### Post-Processing

- **Direct editing:** Edit generated titles and Markdown, keeping rendered HTML and shared output synchronized.
- **Mind maps:** Convert content into mind-map Markdown.

### Publishing & Collaboration

- **Team workspaces:** Owner, Editor, and Viewer roles, with content approval workflows.
- **Channel monitoring:** Check for new YouTube uploads every 30 minutes.

### Intelligence

- **Knowledge retrieval:** Upload documents to a ChromaDB vector store and inject relevant references into generation.
- **Web research:** Supplement transcripts using the Tavily API.
- **Multi-agent workflows:** Research → Writer → Editor → SEO.
- **Knowledge wiki:** Save notes, recommend related notes, and chat using source evidence.

### Export & Integration

- **Exports:** HTML and Markdown.
- **Webhooks:** Send completed results to a configured URL.
- **Learning sources:** YouTube URLs, uploaded documents, and pasted text.

---

## Quick Start

### Requirements

- Python 3.11+
- Node.js 22.19+
- CLIProxyAPI 7.2.152, with the project patch described below

### Installation

```bash
git clone https://github.com/inbeomheo/insight-engine.git
cd insight-engine

# Virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux

# Runtime and verification dependencies
pip install -r requirements.txt -r requirements-dev.txt
npm ci
npm --prefix frontend ci
npm --prefix tests/e2e ci
```

### Environment Variables

```bash
# First-time setup only. Never overwrite an existing .env.
cp .env.example .env
```

Download the binary and checksum for your operating system from the official [CLIProxyAPI v7.2.152 release](https://github.com/router-for-me/CLIProxyAPI/releases/tag/v7.2.152), and verify the checksum.
The current app uses this version with the project's [quota-pool isolation patch](patches/README.en.md). Docker builds apply the patch automatically; for a local source build, follow the patch instructions.

Set the same **new, randomly generated key** in the backend and gateway. Never commit real keys or share them in chat. If `.env` already exists, add the new settings locally instead of overwriting the file.

```env
FLASK_ENV=development
CLIPROXYAPI_BASE_URL=http://127.0.0.1:8317/v1
CLIPROXYAPI_API_KEY=<new-random-key-generated-locally>

# Optional
YOUTUBE_API_KEY=...             # Comment collection
SUPADATA_API_KEY=...            # Transcript fallback service
TAVILY_API_KEY=...              # Web research
```

Start the local gateway as follows. Also inject `CLIPROXYAPI_API_KEY` into the terminal using your local secret-management tool. The launcher does not load `.env` automatically.

```bash
# Replace these with absolute paths to the installed binary and a new dedicated auth directory.
export CLIPROXYAPI_BINARY=/absolute/path/to/cli-proxy-api
export CLIPROXYAPI_AUTH_DIR=/absolute/path/to/insight-cliproxyapi-auth
python scripts/cliproxyapi_runtime.py login
python scripts/cliproxyapi_runtime.py serve  # http://127.0.0.1:8317/v1
```

`login` requires approval through Codex browser sign-in. Available models and quotas depend on the authenticated account. CLIProxyAPI does not guarantee access to paid official APIs or unlimited usage.

The launcher creates a fresh temporary configuration file with mode `0600` and disables the management API and control panel. It excludes inherited management-password, remote-auth-storage, and cluster settings. The health check verifies authenticated access and `404` responses from management paths.

Existing ChatMock/Codex authentication files are not copied, moved, or deleted. Old `CHATMOCK_*` settings are not used for the new connection. AI calls are blocked if the gateway key is missing.

See [.env.example](.env.example) for the complete environment template.

### Run the App

Keep the gateway running, and start both app servers:

```bash
# Terminal 1 — backend
python app.py                    # → http://localhost:5001

# Terminal 2 — frontend
cd frontend && npm run dev       # → http://localhost:3000
```

Open **http://localhost:3000** in your browser.

---

## Architecture

The Next.js frontend on port 3000 calls the Flask backend on port 5001. The backend uses LiteLLM to call CLIProxyAPI, obtains YouTube transcripts and comments, and uses Supabase for authentication, database storage, and usage accounting.

### Project Structure

```text
insight-engine/
├── app.py                         # Flask entry point (port 5001)
├── config.py                      # Providers, styles, and modifiers
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment template
├── routes/
│   ├── blog_routes.py             # Generation and source extraction
│   ├── auth_routes.py             # Authentication and workspace routes
│   ├── advanced_routes.py         # Advanced generation
│   ├── export_routes.py           # HTML/Markdown exports
│   └── utility_routes.py          # Health, providers, and utilities
├── services/
│   ├── core/                      # AI, generation, pipelines, cache
│   ├── analysis/                  # Text and NLP analysis
│   ├── content/                   # Content processing
│   ├── data/                      # Storage, scheduling, notifications
│   ├── rag/                       # Knowledge retrieval
│   ├── export/                    # Export utilities
│   ├── usage/                     # Atomic usage reservations/refunds
│   └── exceptions/                # Error handling
├── prompts/
│   ├── base.py                    # Shared prompt rules
│   └── styles/                    # Public and internal styles
├── frontend/
│   ├── app/                       # Next.js App Router pages
│   ├── components/                # React components
│   ├── hooks/                     # Custom hooks
│   ├── stores/                    # Zustand state
│   └── lib/                       # API clients, types, utilities
├── tests/
│   ├── test_*.py                  # pytest tests
│   ├── e2e/                       # Playwright end-to-end tests
│   └── load/                      # Load tests
└── supabase/schema.sql            # Database schema
```

---

## Supported Models

| Provider | Models | Notes |
|----------|--------|-------|
| **CLIProxyAPI** | gpt-5.6-luna only | OpenAI-compatible local gateway |

The application model ID is `cliproxyapi/gpt-5.6-luna`. Public generation requests and default auxiliary calls use Luna only. `CLIPROXYAPI_MODELS` does not add other models.

A previously selected browser model is retained if it is still supported; otherwise, the default model is displayed. Existing notes, results, and usage records are not bulk-converted or deleted.

### Quality-First Luna Generation

Evidence extraction, writing, and repairs use `reasoning_effort=medium`; independent evidence review uses `high`.

Writing styles first select exact source passages, generate a draft, and review its claims in a separate Luna call. Code also checks mixed-language output, length limits, and SEO/GEO metadata formats. Generation fails if checks still do not pass after two repairs.

Short, medium, and long bodies are limited to 800, 1,500, and 3,000 characters, including Markdown. When the selected evidence is sufficient, minimum lengths of 500, 1,000, and 2,000 characters are also checked. Short sources are not padded to meet an arbitrary minimum. Token usage includes all auxiliary calls.

Sources up to 20,000 characters typically require 3–7 calls. Longer sources add one evidence-extraction call per 20,000-character chunk. The quality pipeline has a 240-second total limit. This does not guarantee that unsupported claims are completely eliminated.

Streaming sends only the reviewed body, so the first content may appear later. Text and ordinary single-YouTube generation display evidence, writing, review, and repair stages, with a cancel button. Once a disconnect is detected, subsequent AI calls are blocked; usage for requests already sent is not reversed. Ordinary web URLs, multiple-source generation, and agent mode retain their existing request paths.

Fixed Korean labels required by the SEO/GEO parsers remain unchanged in other output languages; values and ordinary headings are translated. Structured transformations such as mind maps, chapters, comment summaries, and knowledge notes, as well as low-level calls without a style, retain their existing format contracts. Earlier caches are separated using a new key version rather than deleted.

The binary's protocol can be tested against a local fake provider without an external account. This checks regular responses, tool calls, streaming, and final usage, but does not replace real sign-in and model-generation verification.

```bash
CLIPROXYAPI_TEST_BINARY=/absolute/path/to/cli-proxy-api \
  node scripts/run_python.cjs -m pytest tests/test_cliproxyapi_protocol.py -v
```

---

## Styles

| Style | Description |
|-------|-------------|
| Summary | Key-point summaries |
| Q&A | Questions and answers |
| Quiz | Multiple-choice learning quizzes |
| Retention Cards | Spaced-review learning cards |

Each style has a dedicated prompt and generation settings. Model-specific handling determines which settings, such as temperature, can be sent.

---

## API

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/generate` | POST | Generate content from a single URL or direct text |
| `/generate-stream` | POST | Text or single-YouTube generation, with progress and reviewed output |
| `/generate-batch` | POST | Batch generation for up to 10 URLs |

### Content Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mindmap` | POST | Generate a mind map |
| `/api/extract-document` | POST | Extract text from PDF/DOCX/PPTX |
| `/api/extract-audio` | POST | Transcribe MP3/WAV/M4A/OGG/FLAC/AAC |
| `/api/export/html` | POST | Export HTML |
| `/api/export/markdown` | POST | Export Markdown |

### Platform & Publishing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workspaces` | GET/POST | Workspace management |

### System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/providers` | GET | Available AI configuration |
| `/api/knowledge/upload` | POST | Upload a knowledge-reference document |
| `/api/admin/dashboard` | GET | Operations dashboard |

---

## Environment Variables

### AI Provider

| Variable | Provider | Configuration |
|----------|----------|---------------|
| `CLIPROXYAPI_BASE_URL` | CLIProxyAPI | Default: `http://127.0.0.1:8317/v1` |
| `CLIPROXYAPI_API_KEY` | CLIProxyAPI | Required; the same new random key configured on the gateway |
| `CLIPROXYAPI_MODELS` | CLIProxyAPI | Unused; the app is Luna-only |

### Key Settings

| Variable | Description |
|----------|-------------|
| `YOUTUBE_API_KEY` | YouTube comments |
| `SUPADATA_API_KEY` | Transcript fallback |
| `TAVILY_API_KEY` | Web research |
| `SUPABASE_URL` + `SUPABASE_PUBLISHABLE_KEY` | Required production database/auth settings; legacy `SUPABASE_ANON_KEY` supported |
| `SUPABASE_SECRET_KEY` | Required production server-side administration/background tasks; legacy `SUPABASE_SERVICE_ROLE_KEY` supported |
| `PUBLIC_ORIGIN` | Canonical production HTTPS origin |
| `WHISPER_ENABLED` | Local Whisper fallback (`true`/`false`) |
| `DOCUMENT_UPLOAD_MAX_BYTES` | Document extraction upload limit in bytes |
| `AUDIO_UPLOAD_MAX_BYTES` | Audio transcription upload limit in bytes |
| `RAG_ENABLED` | Knowledge retrieval (`true`/`false`) |
| `WEBHOOK_URL` + `WEBHOOK_ENABLED` | Completion notifications |
| `REDIS_URL` | Rate-limiter storage |
| `YT_HTTP_PROXY` / `YT_HTTPS_PROXY` | Proxy settings for YouTube access |

Complete template: [.env.example](.env.example).

---

## Testing

```bash
# Full local verification: backend, frontend, and E2E smoke tests
npm run verify:all

# Full local Chromium E2E suite; unconfigured authentication cases are skipped
cd tests/e2e
npm ci
npx --no-install playwright install chromium
npm run test:ci

# Run the following commands from the repository root
cd ../..
node scripts/run_python.cjs -m pytest tests/ --cov=. --cov-report=html
npm --prefix frontend exec -- tsc --noEmit
```

---

## Deployment

### Docker

```bash
# Local backend, frontend, Redis, and Nginx
docker compose up --build -d

# Open http://localhost
docker compose ps
```

The default `docker-compose.yml` uses `development` mode, where authentication bypass is allowed. Backend, frontend, Redis, and Nginx ports bind to `127.0.0.1` only. They are not exposed to the LAN or internet by default. **Do not publish this development configuration.** Use the production configuration instead.

Before deployment, configure real secrets using `.env.example`, then validate them:

```bash
npm run verify:production -- --env-file <production-env-file>
```

Production authentication and atomic usage reservations require `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` (legacy `SUPABASE_ANON_KEY` is supported). Administration, aggregate statistics, and background channel monitoring also require `SUPABASE_SECRET_KEY` (legacy `SUPABASE_SERVICE_ROLE_KEY` is supported). Never expose this server-side secret to a browser.

`SUPABASE_URL` must be a production `https://` URL, not a loopback/local URL. `PUBLIC_ORIGIN` must be one production HTTPS origin without a path.

For a new database, apply [supabase/schema.sql](supabase/schema.sql) once. For an existing database, apply only missing migrations from `003` through `009`, in order. If `007` is already applied, continue with [008_usage_reservation_idempotency.sql](supabase/migrations/008_usage_reservation_idempotency.sql) and [009_workspace_rls_security.sql](supabase/migrations/009_workspace_rls_security.sql). Do not apply both the consolidated schema and the same incremental migrations to a new database.

`/ready` calls the read-only `insight_engine_schema_version()` database function using the anonymous/public client and requires schema version `9`; otherwise it returns `503`. This check does not create or modify data and does not require a server secret.

Production uses `docker-compose.deploy.yml`. Application data, backups, caches, and logs reside in the single `insight_app_persist` volume, under `data/`, `backups/`, `cache/`, and `logs/`. Failed usage-refund retry records also live under `data/`. Persist and back up the entire volume.

> **Warning — existing volumes:** Data in old `insight_app_data` / `insight_app_backups` volumes is not moved automatically. Stop services, back up the old volumes, copy and verify the required data and backups, and obtain approval before any destructive migration. Do not delete the original volumes before verification.

Portable ZIP backups are disabled by default. Enable them explicitly with `AUTO_BACKUP_ENABLED=true`. The first backup waits `BACKUP_INITIAL_DELAY_SECONDS` (default 300 seconds). On Linux, the backup process pauses the backend process group with `SIGSTOP` to capture Chroma/SQLite write-ahead logs, then resumes it with `SIGCONT`. The pause is bounded by `BACKUP_QUIESCE_TIMEOUT_SECONDS` (default 600 seconds).

Archives are extracted and checked using file hashes and SQLite `PRAGMA quick_check` before old archives beyond `MAX_BACKUPS` are removed. Failures receive three bounded retry attempts and then appear as a failed process and supervisor logs; configure operational alerts. API processing pauses during the snapshot, and verification requires enough temporary disk space under `/tmp`. Prefer platform volume backups for large volumes. On non-Linux systems, stop writers before manually running `backup` or `rehearse`.

Restoration requires all writers, including the backend and backup daemon, to be stopped. **Restoring with `--overwrite` replaces the target data; back up and obtain approval first.**

```bash
python scripts/backup_app_data.py restore <archive.zip> --target <data-dir> --overwrite
```

The restore command verifies archive paths, CRC, file types, the SHA-256 manifest, and SQLite integrity in a separate staging directory before atomically replacing the destination. On failure, the original destination is retained or rolled back. Keep the archive outside the restore target.

Production CLIProxyAPI is built from the pinned official `v7.2.152` commit and runs as a non-root user. The build also applies the project's quota-pool patch and regression tests. This patch is not part of the official release itself.

After setting `CLIPROXYAPI_API_KEY`, perform initial sign-in or token renewal with:

```bash
docker compose -f docker-compose.deploy.yml --profile cliproxyapi-login run --rm --build --service-ports cliproxyapi-login
```

Credentials are stored at `/data/cliproxyapi/auth` in the new dedicated `insight_cliproxyapi_auth` volume. The host `.codex` directory and old `insight_chatmock_credentials` volume are neither mounted nor modified. Unauthenticated `/v1/models` requests are rejected. In addition to the gateway health check, backend `/ready` checks the usable model list. A running but unauthenticated gateway does not pass AI readiness.

The Caddy-protected area requires a username and password hash as secrets. Generate a bcrypt hash instead of storing a plaintext password. Quote the hash with single quotes in `.env` so Compose does not interpolate its `$` characters.

```bash
docker run --rm caddy:2-alpine caddy hash-password --plaintext 'long-production-password'
# .env: use the complete output, enclosed in single quotes; never commit it
CADDY_BASIC_AUTH_USER=operator
CADDY_BASIC_AUTH_HASH='<caddy hash-password output>'

docker compose -f docker-compose.deploy.yml up --build -d
```

The production backend health check uses `/ready`, which calls CLIProxyAPI, Redis, Supabase, and Next.js. It returns `503` if a required dependency fails. `/health` checks process liveness only.

### Railway

Continuous integration (CI: automated build and test runs) executes backend, frontend, browser, and Docker build/runtime verification without deployment credentials. External publishing and deployment are disabled by default. Configure the following in GitHub **Settings → Secrets and variables → Actions** to enable them on `master` pushes:

| Capability | Repository variables | Secrets |
|------------|----------------------|---------|
| Publish Docker Hub images | `ENABLE_DOCKER_PUBLISH=true` | `DOCKER_USERNAME`, `DOCKER_PASSWORD` |
| Deploy to Railway | Publishing enabled, plus `ENABLE_RAILWAY_DEPLOY=true` | Publishing credentials, plus `RAILWAY_TOKEN` |

Missing or non-`true` flags skip the corresponding external action. Enabled actions fail on missing required credentials; enabling Railway without image publishing also fails. Railway uses only the image verified and published by the same CI run.

1. Set the Railway `insight-engine` service source to **Docker Image**, initially `<DOCKER_USERNAME>/insight-engine:<git-sha>`. CI updates the source using `service source connect --image` and a unique commit-SHA tag. For a private registry, configure a deployment-only read-only token in Registry Credentials.
2. Configure `FLASK_ENV=production`, the external gateway's `CLIPROXYAPI_BASE_URL` and `CLIPROXYAPI_API_KEY`, and the required Redis, Supabase, CORS, security, and backup settings. Set `RAILWAY_RUN_UID=0` and mount exactly one persistent volume at `/app/persist`. The startup supervisor initializes and assigns ownership of the root-owned volume directories, then permanently drops to the `appuser` UID/GID. Flask, Next.js, Nginx, and the optional backup daemon do not run as root. See Railway's [Volumes](https://docs.railway.com/volumes) and [Volume Reference](https://docs.railway.com/volumes/reference).
3. Docker Image sources do not read repository `railway.json`. In **Settings → Deploy**, set Healthcheck Path to `/ready`, Healthcheck Timeout to `120`, and Required Mount Path to `/app/persist`. Set Draining Time to at least `630` seconds and `RAILWAY_DEPLOYMENT_DRAINING_SECONDS=630`. The zero-second default would interrupt graceful shutdown.
4. Use Railway's manual/automated volume backups as the production recovery baseline and set `PLATFORM_VOLUME_BACKUPS_ENABLED=true`. ZIP backups are supplemental portability tools, not a substitute for independent platform backups. ZIP files on the same volume do not satisfy readiness requirements.
5. After enabling publishing/deployment, push to `master`. CI publishes the verified image under both its commit-SHA tag and the convenience `production` tag, but deploys the immutable SHA tag using Railway CLI `5.45.2`. It waits for a new deployment ID and final `SUCCESS`, treating failure or timeout as deployment failure. It verifies the live source image, `/ready`, 120-second health timeout, single `/app/persist` volume and required mount, and 630-second draining configuration. Finally, `PUBLIC_ORIGIN/ready` must return `200`. Full environment-variable JSON is not logged; only the required public-origin/draining contract is inspected through a pipe.

Do not let Railway independently rebuild the GitHub source or redeploy only the mutable `production` tag; that can diverge from the artifact verified in CI. Pushes to `main` run tests and Docker build verification but do not publish or deploy production images.

`railway.json` is a separate safety net for GitHub-source deployments: Dockerfile builder, `/ready`, required `/app/persist` mount, and 630-second draining. For Docker Image sources, the service settings above are authoritative. Readiness includes the Next.js process in the same container, alongside the gateway, Redis, and database schema checks.

### Manual

```bash
export FLASK_ENV=production
export FLASK_DEBUG=0
gunicorn app:app -b 0.0.0.0:5001
```

This starts the backend only; the frontend, gateway, required services, and production access controls must also be configured.

---

## Troubleshooting

| Problem | What to check |
|---------|---------------|
| AI calls or `/ready` fail | Gateway sign-in/running state, base URL and key agreement, and available models in `/v1/models` |
| YouTube transcript retrieval fails | Configure `SUPADATA_API_KEY` or the appropriate `YT_HTTP_PROXY` settings |
| Comments are missing | Configure `YOUTUBE_API_KEY` and enable YouTube Data API v3 |
| Frontend shows a blank page | Check that the backend is running (`python app.py`), then inspect frontend errors |

---

## Tech Stack

**Backend:** Python 3.11+ · Flask 3.1+ · LiteLLM · APScheduler · ChromaDB · faster-whisper · Supabase

**Frontend:** Next.js 16 · React 19 · TypeScript · Tailwind CSS v4 · Zustand · TanStack Query · shadcn/ui · Radix UI

**Testing:** pytest · Playwright E2E · Vitest · MSW

---

## License

MIT License
