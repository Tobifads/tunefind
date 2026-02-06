# TuneFind

TuneFind is a cloud app concept for music producers:

- Producers upload beat files.
- They hum a melody/rhythm pattern.
- The system returns the closest matching beats from **their own uploaded catalog**.

This repository currently focuses on a **learning-first foundation** so you can understand how to build the product end-to-end.

## Product Vision

TuneFind solves a real creator problem: producers often remember a beat's *sound* but not its filename. Instead of searching by names/tags, they search by humming.

## Learning-First Build Plan

The project is intentionally split into stages so you can learn each piece deeply.

### Stage 1 — Core Retrieval (No fancy UI)

Goal: prove that hummed audio can retrieve similar beats.

1. Ingest uploaded audio files.
2. Convert each file to a comparable representation (embeddings/features).
3. Store vectors in a searchable index.
4. Accept a hummed query.
5. Convert hum to same representation.
6. Return top-k nearest beats.

### Stage 2 — Better Matching

1. Add pitch-aware and rhythm-aware features.
2. Add score fusion (multiple similarity signals).
3. Add result explanations ("matched on melody contour").
4. Add fast re-ranking for better quality.

### Stage 3 — Cloud Productization

1. Auth and per-user libraries.
2. Background processing queues.
3. Scalable storage and vector search.
4. Observability (latency, errors, quality metrics).

### Stage 4 — Intelligent UX

1. Natural-language filters (e.g., "dark trap beat").
2. A/B evaluation loop.
3. Feedback-aware ranking improvements.

## Suggested System Architecture

- **Frontend**: upload + hum recording + result list/player.
- **API**: auth, upload orchestration, query endpoint.
- **Worker pipeline**:
  - decode audio
  - normalize sample rate
  - compute embeddings/features
  - upsert vectors
- **Storage**:
  - object storage for original audio
  - metadata DB (beat owner, title, bpm, tags)
  - vector index for similarity search
- **Model layer**:
  - baseline embedding model for audio similarity
  - optional melody/pitch contour extractor

## Practical Tech Stack (Good for Learning)

- **Frontend**: Next.js + TypeScript
- **Backend API**: FastAPI (Python) or Node/Express
- **Audio processing**: Python (`librosa`, `torchaudio`)
- **Vector DB**: pgvector (simple) or dedicated vector store
- **Task queue**: Celery/RQ/Redis (or cloud equivalent)
- **Storage**: S3-compatible object storage

## Quality Metrics to Track Early

- Top-k retrieval accuracy (does correct beat appear in top 5/top 10?)
- Mean query latency
- Ingestion processing time per file
- User feedback signal (thumbs up/down for results)

## Initial Milestones (Recommended)

1. Build an offline notebook/script that compares a hum against local beat files.
2. Turn that into an API endpoint (`/search-by-hum`).
3. Add upload + background embedding jobs.
4. Add user accounts and per-user isolation.
5. Add observability and evaluation dashboard.

## Repository Roadmap

- `docs/learning-roadmap.md` — detailed curriculum and project checkpoints.
- Future code modules will be added as the MVP implementation begins.

---

If you're learning while building, keep a simple rule:

> Every feature should include (1) implementation, (2) test, and (3) a short note explaining what you learned.


## Current MVP (Implemented)

This repository now includes a **working backend core MVP**:

- Beat upload/indexing and hum-based search via `TuneFindService`.
- A CLI (`tunefind_cli.py`) to upload beats and search by hum.
- A pure-Python audio-feature pipeline (energy, zero-crossing rate, autocorrelation summaries) and cosine similarity ranking.

## Quickstart

```bash
cd /path/to/tunefind
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Local UI

You can run a simple local UI powered by a lightweight HTTP server:

```bash
python app/server.py
```

You should see `TuneFind server running on http://0.0.0.0:8000` in your terminal. Then open
`http://localhost:8000` in your browser. The UI lets you upload beats and search by hum.

The flow is **library-first**: producers upload beats over time, and searches always run against the beats already stored for that owner.

Audio format note: the MVP only accepts **16-bit PCM .wav**. If your files are .mp3, convert them first
(e.g., `ffmpeg -i input.mp3 -ac 1 -ar 8000 output.wav`).

Upload a beat:

```bash
python tunefind_cli.py upload --owner-id producer1 --file ./my_beat.wav
```

Search by hum:

```bash
python tunefind_cli.py search --owner-id producer1 --file ./hum.wav --top-k 5
```

Run tests:

```bash
pytest -q
```

### Notes

- This MVP supports **16-bit PCM WAV** only for simplicity.
- The service/index layers are intentionally simple so you can swap in stronger ML embeddings later without changing product behavior.
