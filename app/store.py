from __future__ import annotations

import json
import time
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
    audio_hash: str | None = None
    bpm: int | None = None
    key: str | None = None


class BeatIndex:
    def __init__(self, index_path: Path) -> None:
        self.index_path = index_path
        self.records: list[BeatRecord] = []
        self._load()

    def _load(self) -> None:
        if self.index_path.exists():
            try:
                data = json.loads(self.index_path.read_text())
            except json.JSONDecodeError:
                backup = self.index_path.with_name(f"{self.index_path.stem}.corrupt.{int(time.time())}.json")
                self.index_path.rename(backup)
                self.records = []
                return
            self.records = []
            for item in data:
                if "audio_hash" not in item:
                    item["audio_hash"] = None
                if "bpm" not in item:
                    item["bpm"] = None
                if "key" not in item:
                    item["key"] = None
                self.records.append(BeatRecord(**item))

    def _save(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps([asdict(r) for r in self.records], indent=2))

    def upsert(self, record: BeatRecord) -> None:
        self.records = [r for r in self.records if r.beat_id != record.beat_id]
        self.records.append(record)
        self._save()

    def find_by_owner_hash(self, owner_id: str, audio_hash: str) -> BeatRecord | None:
        for record in self.records:
            if record.audio_hash and record.owner_id == owner_id and record.audio_hash == audio_hash:
                return record
        return None

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

    def list_by_owner(self, owner_id: str) -> list[dict]:
        items = [r for r in self.records if r.owner_id == owner_id]
        items.sort(key=lambda r: r.filename.lower())
        return [
            {
                "beat_id": item.beat_id,
                "filename": item.filename,
                "owner_id": item.owner_id,
                "duration_s": item.duration_s,
                "sample_rate": item.sample_rate,
                "bpm": item.bpm,
                "key": item.key,
            }
            for item in items
        ]

    def delete_by_owner(self, owner_id: str) -> list[BeatRecord]:
        removed = [r for r in self.records if r.owner_id == owner_id]
        if removed:
            self.records = [r for r in self.records if r.owner_id != owner_id]
            self._save()
        return removed

    def delete_by_owner_and_id(self, owner_id: str, beat_id: str) -> BeatRecord | None:
        removed = None
        remaining = []
        for record in self.records:
            if record.owner_id == owner_id and record.beat_id == beat_id:
                removed = record
                continue
            remaining.append(record)
        if removed:
            self.records = remaining
            self._save()
        return removed
