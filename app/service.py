from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.audio import extract_features
from app.store import BeatIndex, BeatRecord


class TuneFindService:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.uploads_dir = data_dir / "uploads"
        self.index = BeatIndex(data_dir / "index" / "beats.json")

    def upload_beat(self, owner_id: str, filename: str, file_bytes: bytes) -> dict:
        if not filename.lower().endswith(".wav"):
            raise ValueError(
                "Only 16-bit PCM .wav files are supported in this MVP. Convert your audio to .wav first."
            )

        feats = extract_features(file_bytes)
        beat_id = str(uuid4())

        owner_dir = self.uploads_dir / owner_id
        owner_dir.mkdir(parents=True, exist_ok=True)
        (owner_dir / f"{beat_id}_{filename}").write_bytes(file_bytes)

        self.index.upsert(
            BeatRecord(
                beat_id=beat_id,
                filename=filename,
                owner_id=owner_id,
                duration_s=feats.duration_s,
                sample_rate=feats.sample_rate,
                vector=feats.vector,
            )
        )
        return {"beat_id": beat_id, "filename": filename, "owner_id": owner_id}

    def search_by_hum(self, owner_id: str, file_bytes: bytes, top_k: int = 5) -> dict:
        if top_k < 1 or top_k > 20:
            raise ValueError("top_k must be between 1 and 20")

        query = extract_features(file_bytes)
        matches = self.index.search(query.vector, owner_id=owner_id, top_k=top_k)
        return {"matches": matches, "count": len(matches)}

    def list_beats(self, owner_id: str) -> dict:
        beats = self.index.list_beats(owner_id)
        return {"beats": beats, "count": len(beats)}
