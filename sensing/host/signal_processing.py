"""Turn CSI amplitudes into motion / presence / breathing-rate readings.

Big picture: the TX->RX signal arrives over many paths (direct, bouncing off
walls, the floor, and the person). When the person moves, the path lengths
change and the amplitude of each subcarrier wobbles. So:

  * motion   = how much the amplitudes wobble over the last ~0.5 s
  * presence = how different the average amplitude pattern is from the empty room
  * breathing = a slow (0.1-0.6 Hz) periodic wobble, found with an FFT

Every threshold is relative to a calibration recorded with the hiding spot
empty, because the absolute numbers change with every room and board placement.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, sosfiltfilt


def normalize_gain(amplitudes: np.ndarray) -> np.ndarray:
    """Divide each frame by its own mean amplitude.

    The ESP32 receiver has automatic gain control: from packet to packet it may
    scale ALL subcarriers up or down together. Without this step a gain jump
    looks exactly like motion. A person changes subcarriers by different
    amounts, so dividing by the frame mean removes the gain but keeps the
    person's effect. Works on one frame (1-D) or many (2-D, frames x subcarriers).
    """
    amplitudes = np.asarray(amplitudes, dtype=np.float32)
    mean = amplitudes.mean(axis=-1, keepdims=True)
    return amplitudes / np.maximum(mean, 1e-6)


def motion_score(window: np.ndarray) -> float:
    """Average over subcarriers of the temporal standard deviation.

    window: frames x subcarriers, already gain-normalized. ~0.01 when nothing
    moves (just radio noise); several times higher when someone moves.
    """
    return float(window.std(axis=0).mean())


def presence_score(window: np.ndarray, empty_profile: np.ndarray) -> float:
    """Mean absolute difference between this window's average amplitude
    pattern and the empty-room pattern. A body in the link changes the static
    multipath even when it is perfectly still."""
    return float(np.abs(window.mean(axis=0) - empty_profile).mean())


@dataclass
class Calibration:
    empty_profile: np.ndarray  # mean gain-normalized amplitude per subcarrier
    motion_threshold: float
    presence_threshold: float
    motion_baseline: float  # median motion score while empty (for display)


def calibrate(
    amplitudes: np.ndarray,
    window_frames: int,
    margin: float = 1.5,
) -> Calibration:
    """Learn thresholds from a recording of the EMPTY hiding spot.

    We slide the same window used live across the recording, collect the scores
    the empty room produces (noise, people walking far away), and put the
    threshold a safety margin above the 95th percentile of those. Raise
    `margin` if you get false "moving" readings, lower it if it misses motion.
    """
    norm = normalize_gain(amplitudes)
    if len(norm) < 2 * window_frames:
        raise ValueError(f"need at least {2 * window_frames} frames to calibrate, got {len(norm)}")
    empty_profile = norm.mean(axis=0)

    hop = max(1, window_frames // 4)
    windows = [norm[i : i + window_frames] for i in range(0, len(norm) - window_frames + 1, hop)]
    motion = np.array([motion_score(w) for w in windows])
    presence = np.array([presence_score(w, empty_profile) for w in windows])
    return Calibration(
        empty_profile=empty_profile,
        motion_threshold=float(np.percentile(motion, 95) * margin),
        presence_threshold=float(np.percentile(presence, 95) * margin),
        motion_baseline=float(np.median(motion)),
    )


# At ~100 packets/s: a 0.5 s window, a new reading every 0.2 s, and 3 agreeing
# readings before the state changes (~0.6 s from movement to "MOVING").
WINDOW_FRAMES = 50
HOP_FRAMES = 20
CONFIRM_READINGS = 3

EMPTY = "EMPTY"
MOVING = "MOVING"
STILL = "STILL"


def classify(motion: float, presence: float, cal: Calibration) -> str:
    """Raw (un-debounced) state for one window."""
    if motion > cal.motion_threshold:
        return MOVING
    if presence > cal.presence_threshold:
        return STILL
    return EMPTY


class Debouncer:
    """Only change the reported state after `needed` identical raw readings in a
    row (CLAUDE.md: "change state only after 3 consistent readings"). Stops a
    single noisy window from eliminating a player."""

    def __init__(self, needed: int = 3, initial: str = EMPTY):
        self.needed = needed
        self.state = initial
        self._candidate = initial
        self._count = 0

    def update(self, raw: str) -> str:
        if raw == self.state:
            self._candidate, self._count = raw, 0
        elif raw == self._candidate:
            self._count += 1
            if self._count >= self.needed:
                self.state, self._count = raw, 0
        else:
            self._candidate, self._count = raw, 1
            if self.needed <= 1:
                self.state, self._count = raw, 0
        return self.state


class LiveDetector:
    """Feed frames one at a time; get a (state, motion, presence) reading every
    `hop_frames` frames."""

    def __init__(self, cal: Calibration, window_frames: int, hop_frames: int, confirm: int = 3):
        self.cal = cal
        self.window = deque(maxlen=window_frames)
        self.hop_frames = hop_frames
        self.debouncer = Debouncer(confirm)
        self._since_last = 0

    def push(self, amplitude: np.ndarray) -> tuple[str, float, float] | None:
        self.window.append(normalize_gain(amplitude))
        self._since_last += 1
        if len(self.window) < self.window.maxlen or self._since_last < self.hop_frames:
            return None
        self._since_last = 0
        w = np.array(self.window)
        m = motion_score(w)
        p = presence_score(w, self.cal.empty_profile)
        return self.debouncer.update(classify(m, p, self.cal)), m, p


# ---------------------------------------------------------------- breathing

BREATHING_BAND = (0.1, 0.6)  # Hz = 6-36 breaths per minute
HEART_BAND = (0.8, 2.0)  # Hz = 48-120 bpm. Experimental: ESP32 is usually too noisy.


def resample_uniform(times: np.ndarray, amplitudes: np.ndarray, fs: float) -> np.ndarray:
    """Packets don't arrive exactly every 10 ms (and some are lost). An FFT
    needs evenly spaced samples, so linearly interpolate onto a fixed grid."""
    t_uniform = np.arange(times[0], times[-1], 1.0 / fs)
    return np.stack([np.interp(t_uniform, times, amplitudes[:, k]) for k in range(amplitudes.shape[1])], axis=1)


@dataclass
class RateEstimate:
    per_minute: float
    confidence: float  # 0-1: share of in-band power at the peak; > 0.6 is a clear rhythm


def estimate_rate(
    times: np.ndarray,
    amplitudes: np.ndarray,
    band: tuple[float, float] = BREATHING_BAND,
    fs: float = 20.0,
    top_k: int = 10,
) -> RateEstimate:
    """Dominant periodic rate in `band` across the best subcarriers.

    times: seconds (frames,); amplitudes: frames x subcarriers (raw |H|).
    Use >= 20 s of data for breathing so a few full breaths fit in the window.
    """
    x = resample_uniform(np.asarray(times), normalize_gain(amplitudes), fs)
    x = x - x.mean(axis=0)
    # Band-pass: removes slow drift (below band) and fast motion/noise (above).
    # sosfiltfilt runs forward and backward so the signal isn't time-shifted.
    sos = butter(2, band, btype="bandpass", fs=fs, output="sos")
    x = sosfiltfilt(sos, x, axis=0)

    # Zero-pad to 8x for a finer frequency grid (pure interpolation of the
    # spectrum; doesn't add real resolution, but makes the peak easier to locate).
    n_fft = 8 * len(x)
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x))[:, None], n=n_fft, axis=0)) ** 2
    freqs = np.fft.rfftfreq(n_fft, 1.0 / fs)
    in_band = (freqs >= band[0]) & (freqs <= band[1])
    band_spec = spectrum[in_band]

    # Some subcarriers barely see the chest; keep the ones with the sharpest peak.
    peakiness = band_spec.max(axis=0) / (np.median(band_spec, axis=0) + 1e-12)
    best = np.argsort(peakiness)[-top_k:]
    combined = band_spec[:, best].mean(axis=1)

    # Confidence = how much of the in-band power sits within +-0.05 Hz
    # (+-3 per minute) of the peak. A real rhythm concentrates its power
    # there (~0.8-1.0); noise spreads out (~0.3 in our synthetic tests).
    band_freqs = freqs[in_band]
    peak = int(np.argmax(combined))
    near_peak = np.abs(band_freqs - band_freqs[peak]) <= 0.05
    return RateEstimate(
        per_minute=float(band_freqs[peak] * 60.0),
        confidence=float(combined[near_peak].sum() / (combined.sum() + 1e-12)),
    )
