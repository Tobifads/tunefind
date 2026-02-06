# TuneFind Learning Roadmap

This roadmap is organized so you learn both **ML concepts** and **production engineering** while building TuneFind.

## Phase A — Foundations (1–2 weeks)

### Outcomes

- Understand digital audio basics (sample rate, mono/stereo, spectrograms).
- Understand feature extraction and similarity search.
- Build confidence with Python tooling for audio.

### Study + Build Tasks

1. Load audio and visualize waveforms/spectrograms.
2. Normalize clips to a standard format.
3. Extract baseline features (e.g., mel spectrogram, MFCC).
4. Compute cosine similarity between feature vectors.

### Deliverable

A script that takes:

- one hummed file
- a folder of beats

and returns nearest matches with similarity scores.

## Phase B — Retrieval MVP (1–2 weeks)

### Outcomes

- Understand embeddings and vector indexing.
- Build a minimal ingest + query flow.

### Study + Build Tasks

1. Generate embeddings for beat library.
2. Persist embedding vectors.
3. Build nearest-neighbor search.
4. Add API endpoint for humming query.

### Deliverable

API that returns top-k beat matches for a hummed query.

## Phase C — Product Backend (2–3 weeks)

### Outcomes

- Understand asynchronous processing and cloud storage.
- Build robust ingestion at scale.

### Study + Build Tasks

1. Implement file upload flow.
2. Store originals in object storage.
3. Queue embedding jobs.
4. Persist job status + metadata.

### Deliverable

Cloud-ready ingest/search backend with per-user data separation.

## Phase D — UX + Evaluation Loop (2 weeks)

### Outcomes

- Learn how retrieval quality is measured and improved.
- Close the loop with user feedback.

### Study + Build Tasks

1. Build result player UI with confidence scores.
2. Add result feedback actions.
3. Track retrieval metrics dashboard.
4. Evaluate failure cases and improve ranking.

### Deliverable

Usable v1 where producers can search their own beat catalog by humming.

## Suggested Weekly Habit

- Build one feature.
- Write one test.
- Write one short "what I learned" note.

Consistency beats intensity for projects like this.
