from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import hashlib

from app.audio import analyze_audio, extract_features
from app.store import BeatIndex, BeatRecord


class TuneFindService:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.uploads_dir = data_dir / "uploads"
        self.index = BeatIndex(data_dir / "index" / "beats.json")

    def upload_beat(
        self,
        owner_id: str,
        filename: str,
        file_bytes: bytes,
        bpm: int | None = None,
        key: str | None = None,
        skip_duplicates: bool = False,
    ) -> dict:
        lower_name = filename.lower()
        if not (
            lower_name.endswith(".wav")
            or lower_name.endswith(".mp3")
            or lower_name.endswith(".webm")
            or lower_name.endswith(".ogg")
            or lower_name.endswith(".m4a")
        ):
            raise ValueError("Only .wav, .mp3, .webm, .ogg, and .m4a files are supported in this MVP.")

        audio_hash = hashlib.sha256(file_bytes).hexdigest()
        existing = self.index.find_by_owner_hash(owner_id, audio_hash)
        if existing:
            if skip_duplicates:
                return {"skipped": True, "filename": filename, "duplicate_of": existing.filename}
            raise ValueError(f"Duplicate upload detected: {existing.filename}")

        feats, est_bpm, est_key = analyze_audio(file_bytes)
        beat_id = str(uuid4())
        bpm = bpm if bpm is not None else est_bpm
        key = key if key else est_key

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
                audio_hash=audio_hash,
                bpm=bpm,
                key=key,
            )
        )
        return {"beat_id": beat_id, "filename": filename, "owner_id": owner_id}

    def upload_beats(
        self,
        owner_id: str,
        files: list[tuple[str, bytes]],
        bpm: int | None = None,
        key: str | None = None,
        skip_duplicates: bool = False,
    ) -> dict:
        uploaded = []
        skipped = []
        failed = []
        for filename, file_bytes in files:
            try:
                result = self.upload_beat(
                    owner_id,
                    filename,
                    file_bytes,
                    bpm=bpm,
                    key=key,
                    skip_duplicates=skip_duplicates,
                )
                if result.get("skipped"):
                    skipped.append(result)
                else:
                    uploaded.append(result)
            except Exception as err:
                failed.append({"filename": filename, "error": str(err)})
        return {"uploads": uploaded, "skipped": skipped, "failed": failed, "count": len(uploaded)}

    def search_by_hum(self, owner_id: str, file_bytes: bytes, top_k: int = 5) -> dict:
        if top_k < 1 or top_k > 20:
            raise ValueError("top_k must be between 1 and 20")
        query = extract_features(file_bytes)
        matches = self.index.search(query.vector, owner_id=owner_id, top_k=top_k)
        return {"matches": matches, "count": len(matches)}

    def list_uploads(self, owner_id: str) -> dict:
        uploads = self.index.list_by_owner(owner_id)
        return {"uploads": uploads, "count": len(uploads)}

    def delete_uploads(self, owner_id: str) -> dict:
        removed = self.index.delete_by_owner(owner_id)
        removed_files = [r.filename for r in removed]
        return {"deleted": removed_files, "count": len(removed_files)}

    def delete_upload(self, owner_id: str, beat_id: str) -> dict:
        removed = self.index.delete_by_owner_and_id(owner_id, beat_id)
        if not removed:
            raise ValueError("Upload not found.")
        return {"deleted": removed.filename, "beat_id": beat_id}
