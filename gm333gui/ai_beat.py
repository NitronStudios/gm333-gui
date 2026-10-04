#!/usr/bin/env python3
"""
AI Beat Detector for GM333 Music Sync.

Uses real-time spectral analysis (FFT) instead of simple energy thresholds:
  - Spectral Flux onset detection (far more accurate than energy delta)
  - BPM estimation + beat-grid prediction (beat is expected at T+interval)
  - Multi-band energy split: bass/mid/treble for richer color mapping
  - Confidence score combining onset strength + tempo alignment

No external ML model files needed — all math runs in-process via numpy.
"""

import time
import math
import numpy as np

SAMPLE_RATE = 22050
CHUNK_SIZE  = 512

# Frequency band boundaries (Hz → bin index via rfft)
BASS_HZ   = (20,   250)
MID_HZ    = (250,  4000)
TREBLE_HZ = (4000, 10000)


def _hz_to_bin(hz: float, n_fft: int, sr: int) -> int:
    return max(0, min(n_fft // 2, int(hz * n_fft / sr)))


class AIBeatDetector:
    """
    Real-time spectral-flux beat detector with BPM tempo locking.

    Call process(samples, now) each audio chunk.
    Returns (is_beat, confidence, band_energies, bpm).
    """

    def __init__(self, sample_rate: int = SAMPLE_RATE, chunk_size: int = CHUNK_SIZE):
        self.sr = sample_rate
        self.n   = chunk_size

        # Pre-compute frequency band bin ranges
        self._bass_lo   = _hz_to_bin(BASS_HZ[0],   self.n * 2, self.sr)
        self._bass_hi   = _hz_to_bin(BASS_HZ[1],   self.n * 2, self.sr)
        self._mid_lo    = _hz_to_bin(MID_HZ[0],    self.n * 2, self.sr)
        self._mid_hi    = _hz_to_bin(MID_HZ[1],    self.n * 2, self.sr)
        self._treble_lo = _hz_to_bin(TREBLE_HZ[0], self.n * 2, self.sr)
        self._treble_hi = _hz_to_bin(TREBLE_HZ[1], self.n * 2, self.sr)

        # Hann window pre-computed
        self._window = np.hanning(self.n)

        # Spectral state
        self._prev_spectrum = None

        # Adaptive threshold for spectral flux
        # ring buffer of ~2 seconds of flux values
        _fps = self.sr / self.n  # chunks per second
        self._flux_buf_size = max(16, int(_fps * 2.0))
        self._flux_buf  = []
        self._flux_mean = 0.0
        self._flux_std  = 1.0

        # BPM / tempo tracking
        self._beat_times = []          # timestamps of confirmed beats
        self._bpm         = 0.0        # estimated BPM (0 = unknown)
        self._beat_interval = 0.0      # seconds between beats
        self._last_beat_time = 0.0
        self._predicted_next = 0.0     # predicted next beat time

        # Cooldown: minimum gap between reported beats (120 BPM = 0.5s)
        self.min_beat_gap = 0.25

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, samples: list | np.ndarray, now: float):
        """
        Process one chunk of s16le audio samples.

        Args:
            samples: list or array of int16 samples, length == chunk_size
            now:     current timestamp (time.time())

        Returns:
            is_beat    (bool)  — beat detected this frame
            confidence (float) — 0..1 beat confidence
            bands      (dict)  — {'bass': 0..1, 'mid': 0..1, 'treble': 0..1}
            bpm        (float) — current BPM estimate (0 if unknown)
        """
        arr = np.array(samples, dtype=np.float32) / 32768.0

        # --- FFT ---
        windowed = arr * self._window
        spectrum = np.abs(np.fft.rfft(windowed))

        # --- Spectral Flux (half-wave rectified) ---
        if self._prev_spectrum is not None:
            diff = spectrum - self._prev_spectrum
            flux = float(np.sum(np.maximum(0.0, diff)))
        else:
            flux = 0.0
        self._prev_spectrum = spectrum.copy()

        # --- Adaptive threshold ---
        self._flux_buf.append(flux)
        if len(self._flux_buf) > self._flux_buf_size:
            self._flux_buf.pop(0)
        if len(self._flux_buf) >= 4:
            arr_buf = np.array(self._flux_buf, dtype=np.float32)
            self._flux_mean = float(np.mean(arr_buf))
            self._flux_std  = float(np.std(arr_buf)) + 1e-6

        threshold = self._flux_mean + 1.5 * self._flux_std

        # --- Per-band energy (normalized 0..1 range) ---
        def band_energy(lo, hi):
            s = spectrum[lo:hi]
            if len(s) == 0:
                return 0.0
            rms = float(np.sqrt(np.mean(s ** 2)))
            return min(1.0, rms / 0.5)  # 0.5 ≈ typical peak magnitude

        bands = {
            'bass':   band_energy(self._bass_lo,   self._bass_hi),
            'mid':    band_energy(self._mid_lo,    self._mid_hi),
            'treble': band_energy(self._treble_lo, self._treble_hi),
        }

        # --- Onset detection ---
        is_onset = (
            flux > threshold
            and flux > (self._flux_mean * 1.2)   # must exceed mean
            and flux > 0.001                       # hard floor (silence guard)
        )

        # --- Tempo alignment bonus ---
        in_grid = False
        if self._beat_interval > 0 and self._predicted_next > 0:
            tolerance = self._beat_interval * 0.12   # ±12% of beat interval
            in_grid = abs(now - self._predicted_next) <= tolerance

        # --- Confidence score ---
        if is_onset:
            onset_conf = min(1.0, (flux - threshold) / (self._flux_std * 2.0 + 1e-6))
            grid_bonus = 0.35 if in_grid else 0.0
            confidence = min(1.0, onset_conf + grid_bonus)
        else:
            # Not an onset, but if we're bang on the grid, still give partial
            if in_grid and self._bpm > 60:
                confidence = 0.20
            else:
                confidence = 0.0

        # --- Beat decision ---
        gap_ok = (now - self._last_beat_time) >= self.min_beat_gap
        is_beat = gap_ok and confidence >= 0.40

        if is_beat:
            self._register_beat(now)

        return is_beat, confidence, bands, self._bpm

    def reset(self):
        """Clear all state (e.g. on silence or sink change)."""
        self._prev_spectrum = None
        self._flux_buf.clear()
        self._flux_mean = 0.0
        self._flux_std  = 1.0
        self._beat_times.clear()
        self._bpm = 0.0
        self._beat_interval = 0.0
        self._last_beat_time = 0.0
        self._predicted_next = 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _register_beat(self, now: float):
        """Record a beat and update BPM + next-beat prediction."""
        self._last_beat_time = now
        self._beat_times.append(now)

        # Keep only the last 16 beats for BPM estimation
        if len(self._beat_times) > 16:
            self._beat_times.pop(0)

        # Need at least 4 beats to estimate BPM reliably
        if len(self._beat_times) >= 4:
            intervals = np.diff(self._beat_times)
            # Filter out outliers (ignore gaps > 2× median — those are silence drops)
            med = float(np.median(intervals))
            good = intervals[(intervals > med * 0.5) & (intervals < med * 2.0)]
            if len(good) >= 2:
                avg_interval = float(np.mean(good))
                self._bpm = 60.0 / avg_interval
                self._beat_interval = avg_interval
                self._predicted_next = now + avg_interval


def band_to_color_weight(bands: dict, palette_rgb: tuple) -> tuple:
    """
    Blend palette color with frequency-band energy to create a richer hue.

    - Bass energy  → warms up reds
    - Treble energy → cools toward blues/cyans
    - Mid energy   → slight green boost

    Returns new (r, g, b) in 4-bit nibble space (0..15).
    """
    r, g, b = palette_rgb
    bass    = bands.get('bass', 0.0)
    mid     = bands.get('mid', 0.0)
    treble  = bands.get('treble', 0.0)

    # Subtle blend factors (never fully override palette color)
    r_adj = r + bass   * 3.0
    g_adj = g + mid    * 1.5
    b_adj = b + treble * 3.0

    # Clamp to 0..15
    return (
        max(0, min(15, int(round(r_adj)))),
        max(0, min(15, int(round(g_adj)))),
        max(0, min(15, int(round(b_adj)))),
    )
