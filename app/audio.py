from __future__ import annotations

import io
import math
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from dataclasses import dataclass

TARGET_SR = 8000
FRAME_SIZE = 400
HOP_SIZE = 160


@dataclass(frozen=True)
class AudioFeatures:
    vector: list[float]
    duration_s: float
    sample_rate: int


def _read_wav_mono(file_bytes: bytes) -> tuple[list[float], int]:
    with wave.open(io.BytesIO(file_bytes), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        n_frames = wav.getnframes()
        raw = wav.readframes(n_frames)

    if sample_width != 2:
        raise ValueError("Only 16-bit PCM WAV files are supported.")

    total_samples = len(raw) // 2
    ints = [int.from_bytes(raw[i * 2 : i * 2 + 2], "little", signed=True) for i in range(total_samples)]

    if channels > 1:
        mono = []
        for i in range(0, len(ints), channels):
            mono.append(sum(ints[i : i + channels]) / channels)
        ints = mono

    floats = [s / 32768.0 for s in ints]
    return floats, sample_rate


def _read_pydub_mono(file_bytes: bytes) -> tuple[list[float], int]:
    try:
        from pydub import AudioSegment
    except ImportError as exc:
        raise RuntimeError("MP3 support requires the 'pydub' package and ffmpeg installed.") from exc

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is not installed or not on PATH. Install ffmpeg to decode recordings.")

    AudioSegment.converter = ffmpeg

    segment = None
    errors = []
    for fmt in ("webm", "ogg", "mp3", "m4a", "mp4", "aac", "flac"):
        try:
            segment = AudioSegment.from_file(io.BytesIO(file_bytes), format=fmt)
            break
        except Exception as exc:
            errors.append(exc)
    if segment is None:
        raise ValueError("Failed to decode audio. Supported formats require ffmpeg.") from errors[-1]

    samples = list(segment.get_array_of_samples())
    channels = segment.channels
    sample_rate = segment.frame_rate
    sample_width = segment.sample_width

    if channels > 1:
        mono = []
        for i in range(0, len(samples), channels):
            mono.append(sum(samples[i : i + channels]) / channels)
        samples = mono

    max_amp = float(1 << (8 * sample_width - 1)) or 1.0
    floats = [s / max_amp for s in samples]
    return floats, sample_rate


def _read_audio_mono(file_bytes: bytes) -> tuple[list[float], int]:
    try:
        return _read_wav_mono(file_bytes)
    except (wave.Error, EOFError):
        return _read_pydub_mono(file_bytes)


def _resample_linear(samples: list[float], src_sr: int, dst_sr: int) -> list[float]:
    if src_sr == dst_sr:
        return samples
    if not samples:
        return samples

    out_len = max(1, int(len(samples) * dst_sr / src_sr))
    out = []
    for i in range(out_len):
        x = i * (len(samples) - 1) / max(1, out_len - 1)
        left = int(math.floor(x))
        right = min(left + 1, len(samples) - 1)
        frac = x - left
        out.append(samples[left] * (1 - frac) + samples[right] * frac)
    return out


def _frame_iter(samples: list[float]) -> list[list[float]]:
    if len(samples) < FRAME_SIZE:
        samples = samples + [0.0] * (FRAME_SIZE - len(samples))
    frames = []
    for start in range(0, len(samples) - FRAME_SIZE + 1, HOP_SIZE):
        frames.append(samples[start : start + FRAME_SIZE])
    return frames


def _frame_features(frame: list[float]) -> list[float]:
    energy = sum(x * x for x in frame) / len(frame)

    zc = 0
    for a, b in zip(frame[:-1], frame[1:]):
        if (a >= 0 and b < 0) or (a < 0 and b >= 0):
            zc += 1
    zcr = zc / max(1, len(frame) - 1)

    # Simple autocorrelation-based periodicity clues (hum-friendly).
    lags = [20, 40, 80, 120]
    ac = []
    for lag in lags:
        if lag >= len(frame):
            ac.append(0.0)
            continue
        corr = 0.0
        for i in range(len(frame) - lag):
            corr += frame[i] * frame[i + lag]
        ac.append(corr / (len(frame) - lag))

    return [energy, zcr, *ac]


def _prepare_samples(file_bytes: bytes) -> list[float]:
    samples, sr = _read_audio_mono(file_bytes)
    if not samples:
        raise ValueError("Audio file is empty.")

    samples = _resample_linear(samples, sr, TARGET_SR)
    peak = max(abs(x) for x in samples) or 1.0
    return [x / peak for x in samples]


def _prepare_samples_raw(file_bytes: bytes) -> tuple[list[float], int]:
    samples, sr = _read_audio_mono(file_bytes)
    if not samples:
        raise ValueError("Audio file is empty.")

    peak = max(abs(x) for x in samples) or 1.0
    return [x / peak for x in samples], sr


def _compute_features(samples: list[float]) -> AudioFeatures:
    frames = _frame_iter(samples)
    feats = [_frame_features(f) for f in frames]

    # Aggregate with mean/std per feature.
    n_features = len(feats[0])
    means = [sum(row[i] for row in feats) / len(feats) for i in range(n_features)]
    stds = []
    for i in range(n_features):
        m = means[i]
        var = sum((row[i] - m) ** 2 for row in feats) / len(feats)
        stds.append(math.sqrt(var))

    vector = means + stds
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    vector = [v / norm for v in vector]

    return AudioFeatures(vector=vector, duration_s=len(samples) / TARGET_SR, sample_rate=TARGET_SR)


def _estimate_bpm(samples: list[float], sr: int) -> int | None:
    if len(samples) < sr:
        return None
    frames = _frame_iter(samples)
    energies = [sum(x * x for x in frame) for frame in frames]
    if len(energies) < 4:
        return None

    onset = [max(0.0, energies[i] - energies[i - 1]) for i in range(1, len(energies))]
    max_onset = max(onset) if onset else 0.0
    if max_onset <= 1e-8:
        return None
    onset = [v / max_onset for v in onset]

    frames_per_second = sr / HOP_SIZE
    lag_min = int(frames_per_second * 60 / 200)  # 200 BPM
    lag_max = int(frames_per_second * 60 / 60)   # 60 BPM
    if lag_max <= lag_min:
        return None

    best_lag = None
    best_score = -1.0
    for lag in range(lag_min, lag_max + 1):
        score = 0.0
        for i in range(lag, len(onset)):
            score += onset[i] * onset[i - lag]
        if score > best_score:
            best_score = score
            best_lag = lag

    if not best_lag:
        return None
    bpm = int(round(60 * frames_per_second / best_lag))
    # Normalize to a common range
    while bpm < 60:
        bpm *= 2
    while bpm > 200:
        bpm //= 2
    return bpm


def _estimate_bpm_wavelet(file_bytes: bytes, window_s: float = 3.0) -> int | None:
    try:
        import numpy as np
        import pywt
        from scipy import signal
    except Exception:
        return None

    try:
        samples, sr = _prepare_samples_raw(file_bytes)
    except Exception:
        return None

    if not samples or sr <= 0:
        return None

    data = np.asarray(samples, dtype=float)
    window_samps = int(window_s * sr)
    if window_samps <= 0 or len(data) < window_samps:
        return None

    def peak_detect(arr: np.ndarray) -> np.ndarray | None:
        if arr.size == 0:
            return None
        max_val = np.amax(np.abs(arr))
        if max_val <= 0:
            return None
        peak_ndx = np.where(arr == max_val)[0]
        if peak_ndx.size == 0:
            peak_ndx = np.where(arr == -max_val)[0]
        return peak_ndx if peak_ndx.size else None

    def bpm_detector(segment: np.ndarray, fs: int) -> float | None:
        cA = []
        cD = []
        levels = 4
        max_decimation = 2 ** (levels - 1)
        min_ndx = math.floor(60.0 / 220 * (fs / max_decimation))
        max_ndx = math.floor(60.0 / 40 * (fs / max_decimation))
        if max_ndx <= min_ndx:
            return None

        cD_sum = None
        for loop in range(0, levels):
            if loop == 0:
                cA, cD = pywt.dwt(segment, "db4")
                cD_minlen = int(len(cD) / max_decimation + 1)
                cD_sum = np.zeros(cD_minlen)
            else:
                cA, cD = pywt.dwt(cA, "db4")

            cD = signal.lfilter([0.01], [1 - 0.99], cD)
            cD = np.abs(cD[:: (2 ** (levels - loop - 1))])
            cD = cD - np.mean(cD)
            cD_sum = cD[: len(cD_sum)] + cD_sum

        if not np.any(cA):
            return None

        cA = signal.lfilter([0.01], [1 - 0.99], cA)
        cA = np.abs(cA)
        cA = cA - np.mean(cA)
        cD_sum = cA[: len(cD_sum)] + cD_sum

        correl = np.correlate(cD_sum, cD_sum, "full")
        midpoint = int(len(correl) / 2)
        correl_mid = correl[midpoint:]
        peak_ndx = peak_detect(correl_mid[min_ndx:max_ndx])
        if peak_ndx is None or peak_ndx.size == 0:
            return None
        peak_ndx_adjusted = int(peak_ndx[0]) + min_ndx
        if peak_ndx_adjusted == 0:
            return None
        bpm_val = 60.0 / peak_ndx_adjusted * (fs / max_decimation)
        return bpm_val

    max_window_ndx = int(len(data) / window_samps)
    bpms = []
    for w in range(max_window_ndx):
        seg = data[w * window_samps : (w + 1) * window_samps]
        bpm_val = bpm_detector(seg, sr)
        if bpm_val:
            bpms.append(bpm_val)

    if not bpms:
        return None
    return int(round(float(np.median(bpms))))


def _estimate_key(samples: list[float], sr: int) -> str | None:
    frames = _frame_iter(samples)
    if not frames:
        return None

    # Krumhansl-Schmuckler key profiles
    major = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    minor = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
    pitch_classes = [0.0] * 12

    min_lag = max(1, int(sr / 1000))
    max_lag = min(len(frames[0]) - 1, int(sr / 50))

    frame_step = max(1, len(frames) // 300)
    for frame in frames[::frame_step]:
        energy = sum(x * x for x in frame)
        if energy <= 1e-6:
            continue
        best_lag = None
        best_corr = -1.0
        for lag in range(min_lag, max_lag + 1):
            corr = 0.0
            for i in range(len(frame) - lag):
                corr += frame[i] * frame[i + lag]
            if corr > best_corr:
                best_corr = corr
                best_lag = lag
        if not best_lag:
            continue
        freq = sr / best_lag
        if freq < 50 or freq > 1000:
            continue
        midi = 69 + 12 * math.log2(freq / 440.0)
        pc = int(round(midi)) % 12
        pitch_classes[pc] += energy

    if max(pitch_classes) <= 0:
        return None

    def rotate(profile: list[float], n: int) -> list[float]:
        return profile[-n:] + profile[:-n]

    best_key = None
    best_score = -1.0
    is_major = True
    for i in range(12):
        maj_score = sum(p * c for p, c in zip(rotate(major, i), pitch_classes))
        min_score = sum(p * c for p, c in zip(rotate(minor, i), pitch_classes))
        if maj_score > best_score:
            best_score = maj_score
            best_key = i
            is_major = True
        if min_score > best_score:
            best_score = min_score
            best_key = i
            is_major = False

    if best_key is None:
        return None
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return f"{names[best_key]}{'m' if not is_major else ''}"


def _guess_ext(file_bytes: bytes) -> str:
    header = file_bytes[:16]
    if header.startswith(b"RIFF") and b"WAVE" in header:
        return ".wav"
    if header.startswith(b"ID3") or header[:2] == b"\xff\xfb":
        return ".mp3"
    if header.startswith(b"OggS"):
        return ".ogg"
    if header.startswith(b"\x1a\x45\xdf\xa3"):
        return ".webm"
    if len(header) >= 12 and header[4:8] == b"ftyp":
        return ".m4a"
    return ".audio"


def _find_keyfinder_cli() -> str | None:
    env_path = os.getenv("TUNEFIND_KEYFINDER_PATH")
    if env_path and Path(env_path).exists():
        return env_path
    root = Path(__file__).resolve().parent.parent
    candidates = [
        root / ".tools" / "keyfinder-cli" / "bin" / "keyfinder-cli",
        root / ".tools" / "keyfinder-cli" / "bin" / "keyfinder-cli.exe",
        root / ".tools" / "keyfinder-cli" / "keyfinder-cli",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return shutil.which("keyfinder-cli")


def _require_keyfinder_cli() -> str:
    path = _find_keyfinder_cli()
    if not path:
        raise RuntimeError(
            "keyfinder-cli is required for key detection. "
            "Run `python tunefind_cli.py setup-deps` and try again."
        )
    return path


def _estimate_key_keyfinder_cli(file_bytes: bytes) -> str:
    path = _require_keyfinder_cli()
    suffix = _guess_ext(file_bytes)
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            result = subprocess.run(
                [path, "-n", "standard", tmp.name],
                capture_output=True,
                text=True,
                timeout=20,
            )
    except Exception as exc:
        raise RuntimeError(f"Failed to run keyfinder-cli: {exc}") from exc
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        msg = stderr or "unknown error"
        raise RuntimeError(f"keyfinder-cli failed: {msg}")
    key = (result.stdout or "").strip()
    if not key:
        raise RuntimeError("keyfinder-cli returned an empty key.")
    return key


def _estimate_key_librosa(file_bytes: bytes) -> str | None:
    try:
        import numpy as np
        import librosa
    except Exception:
        return None

    try:
        samples, sr = _read_audio_mono(file_bytes)
    except Exception:
        return None
    if not samples:
        return None

    peak = max(abs(x) for x in samples) or 1.0
    y = np.asarray([x / peak for x in samples], dtype=np.float32)
    max_len = sr * 60
    if len(y) > max_len:
        y = y[:max_len]

    try:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, bins_per_octave=24)
    except Exception:
        return None

    chroma_vals = np.sum(chroma, axis=1)
    if not np.any(chroma_vals):
        return None

    pitches = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    keyfreqs = {pitches[i]: chroma_vals[i] for i in range(12)}

    maj_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    min_profile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

    best_key = None
    best_score = -1.0
    is_major = True
    for i in range(12):
        key_test = [keyfreqs.get(pitches[(i + m) % 12]) for m in range(12)]
        maj = np.corrcoef(maj_profile, key_test)[1, 0]
        minor = np.corrcoef(min_profile, key_test)[1, 0]
        if maj > best_score:
            best_score = maj
            best_key = i
            is_major = True
        if minor > best_score:
            best_score = minor
            best_key = i
            is_major = False

    if best_key is None or math.isnan(best_score):
        return None
    return f"{pitches[best_key]}{'m' if not is_major else ''}"


def analyze_audio(file_bytes: bytes) -> tuple[AudioFeatures, int | None, str | None]:
    samples = _prepare_samples(file_bytes)
    feats = _compute_features(samples)
    bpm = _estimate_bpm_wavelet(file_bytes) or _estimate_bpm(samples, TARGET_SR)
    key = _estimate_key_keyfinder_cli(file_bytes)
    return feats, bpm, key


def extract_features(file_bytes: bytes) -> AudioFeatures:
    samples = _prepare_samples(file_bytes)
    return _compute_features(samples)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / ((na * nb) + 1e-8)
