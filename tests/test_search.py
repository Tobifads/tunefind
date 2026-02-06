import io
import math
import wave

from app.service import TuneFindService


def make_tone(freq: float, seconds: float = 1.0, sr: int = 8000) -> bytes:
    n = int(sr * seconds)
    frames = bytearray()
    for i in range(n):
        t = i / sr
        val = int(0.4 * 32767 * math.sin(2 * math.pi * freq * t))
        frames.extend(int(val).to_bytes(2, byteorder="little", signed=True))

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(bytes(frames))
    return buf.getvalue()


def test_upload_and_search_returns_expected_top_match(tmp_path):
    service = TuneFindService(tmp_path)
    owner_id = "producer-123"

    low = make_tone(220.0)
    high = make_tone(660.0)

    service.upload_beat(owner_id, "low.wav", low)
    service.upload_beat(owner_id, "high.wav", high)

    query = make_tone(230.0)
    result = service.search_by_hum(owner_id, query, top_k=2)

    assert result["count"] == 2
    assert result["matches"][0]["filename"] == "low.wav"


def test_owner_isolation(tmp_path):
    service = TuneFindService(tmp_path)
    service.upload_beat("alice", "a.wav", make_tone(220.0))
    service.upload_beat("bob", "b.wav", make_tone(220.0))

    result = service.search_by_hum("alice", make_tone(220.0), top_k=5)
    assert result["count"] == 1
    assert result["matches"][0]["owner_id"] == "alice"


def test_list_beats(tmp_path):
    service = TuneFindService(tmp_path)
    service.upload_beat("alice", "a.wav", make_tone(220.0))
    service.upload_beat("alice", "b.wav", make_tone(330.0))

    result = service.list_beats("alice")
    assert result["count"] == 2
    filenames = {beat["filename"] for beat in result["beats"]}
    assert filenames == {"a.wav", "b.wav"}
