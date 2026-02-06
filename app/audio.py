from __future__ import annotations

import io
import math
import wave
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


def extract_features(file_bytes: bytes) -> AudioFeatures:
    samples, sr = _read_wav_mono(file_bytes)
    if not samples:
        raise ValueError("Audio file is empty.")

    samples = _resample_linear(samples, sr, TARGET_SR)
    peak = max(abs(x) for x in samples) or 1.0
    samples = [x / peak for x in samples]

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


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / ((na * nb) + 1e-8)
