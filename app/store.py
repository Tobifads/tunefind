from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from app.audio import cosine_similarity


@dataclass
class BeatRecord:
    beat_id: str
    filename: str
    owner_id: str
    duration_s: float
    sample_rate: int
    vector: list[float]


class BeatIndex:
    def __init__(self, index_path: Path) -> None:
        self.index_path = index_path
        self.records: list[BeatRecord] = []
        self._load()

    def _load(self) -> None:
        if self.index_path.exists():
            data = json.loads(self.index_path.read_text())
            self.records = [BeatRecord(**item) for item in data]

    def _save(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps([asdict(r) for r in self.records], indent=2))

    def upsert(self, record: BeatRecord) -> None:
        self.records = [r for r in self.records if r.beat_id != record.beat_id]
        self.records.append(record)
        self._save()

    def search(self, query_vector: list[float], owner_id: str, top_k: int = 5) -> list[dict]:
        candidates = [r for r in self.records if r.owner_id == owner_id]
        scored = [(cosine_similarity(query_vector, c.vector), c) for c in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "beat_id": item.beat_id,
                "filename": item.filename,
                "owner_id": item.owner_id,
                "duration_s": item.duration_s,
                "score": round(score, 4),
            }
            for score, item in scored[:top_k]
        ]

    def list_beats(self, owner_id: str) -> list[dict]:
        return [
            {
                "beat_id": item.beat_id,
                "filename": item.filename,
                "owner_id": item.owner_id,
                "duration_s": item.duration_s,
            }
            for item in self.records
            if item.owner_id == owner_id
        ]
