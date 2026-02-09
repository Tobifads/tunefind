# TuneFind

TuneFind is a cloud app concept for music producers:

- Producers upload beat files.
- They hum a melody/rhythm pattern.
- The system returns the closest matching beats from **their own uploaded catalog**.


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

Install everything (Python + system dependencies) in one command:

```bash
python -m venv .venv
source .venv/bin/activate
python tunefind_cli.py setup-deps
```

## Default Dependencies

### One-Step Installer (macOS, Linux, Windows)

Run:

```bash
python tunefind_cli.py setup-deps
```

What it installs:

- Python dependencies from `requirements.txt` (including BPM dependencies).
- `ffmpeg` system binary (for MP3/browser audio decode).
- `keyfinder-cli` + libKeyFinder (for key detection).

You can install only keyfinder/ffmpeg system dependencies with:

```bash
python tunefind_cli.py setup-keyfinder
```

### System Dependencies (MP3 support)

MP3 decoding requires a system `ffmpeg` install. This cannot be installed via `pip`, so each OS needs one step:

- macOS (Homebrew): `brew install ffmpeg`
- Windows (Winget): `winget install Gyan.FFmpeg`
- Windows (Chocolatey): `choco install ffmpeg`
- Linux (Debian/Ubuntu): `sudo apt-get install ffmpeg`
- Linux (Fedora): `sudo dnf install ffmpeg`
- Linux (Arch): `sudo pacman -S ffmpeg`
- Android (Termux): `pkg install ffmpeg`

If `ffmpeg` is missing, MP3 uploads will fail with a clear error. WAV still works.

### Key Detection (libKeyFinder / keyfinder-cli)

`keyfinder-cli` is required by default and upload will fail if it is missing.

High-level steps:

1. Install libKeyFinder (build from source using CMake/FFTW or use a package manager). On macOS, Homebrew provides `brew install libkeyfinder`.
2. Build and install `keyfinder-cli` (requires `ffmpeg` and libKeyFinder).

After install, verify it is on PATH:

```bash
keyfinder-cli --help
```

You can also verify with `http://127.0.0.1:8000/diagnostics` (it will show `keyfinder` path).

**License note:** libKeyFinder and keyfinder-cli are GPL-3.0 licensed. If you plan to distribute this project, review GPL obligations.

### Rebuild Environment (Clean Install)

If uploads/search fail or you suspect a broken environment, do a clean rebuild:

```bash
deactivate 2>/dev/null || true
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
python tunefind_cli.py setup-deps
```

Then restart the server:

```bash
python app/server.py
```

You can verify system support by opening `http://127.0.0.1:8000/diagnostics`.

### Local UI

You can run a simple local UI powered by a lightweight HTTP server:

```bash
python app/server.py
```

Then open `http://localhost:8000` in your browser. The UI lets you upload beats and search by hum.

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

- This MVP supports **WAV**, **MP3**, and common browser recording formats like **WEBM/OGG/M4A** (non-WAV formats require `pydub` and a local `ffmpeg` install).
- BPM and key are **auto-estimated** on upload. BPM uses a wavelet-based detector (GPL-licensed algorithm). Key detection uses `keyfinder-cli` (libKeyFinder).
- **License note:** The BPM detector algorithm integrated here is GPL-licensed. If you plan to distribute this project, review GPL obligations.
- The service/index layers are intentionally simple so you can swap in stronger ML embeddings later without changing product behavior.

### Upload Management

- You can list uploads per owner in the UI (Your Uploads section).
- You can delete all uploads for an owner using the **Delete All Uploads** button.
