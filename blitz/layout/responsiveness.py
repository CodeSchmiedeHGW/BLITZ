"""Qt event-loop lag meter — UI responsiveness, not paint FPS or compute 1/dt."""

from __future__ import annotations

import statistics
import time
from collections import deque

# Sparkline history; label still uses a short median window.
HISTORY_S = 30.0
LABEL_WINDOW_S = 1.0
# Fixed amp Y range (ms). Spikes above clip at the top (red phase).
Y_MAX_MS = 300.0
# Traffic-light bands: OK / warn / bad (stutter).
SMOOTH_MS = 100.0
WARN_MS = 300.0


def lag_phase(lag_ms: float) -> str:
    """Return ``ok`` (<100), ``warn`` (100–300), or ``bad`` (>300)."""
    if lag_ms < SMOOTH_MS:
        return "ok"
    if lag_ms <= WARN_MS:
        return "warn"
    return "bad"


class ResponsivenessMeter:
    """Measure how late a fixed-interval timer fires (GUI-thread lag).

    Idle baseline stays near 0 ms. Blocking the event loop raises lag.
    Qt has no hidden 60 Hz paint loop — this is not display FPS.
    """

    def __init__(
        self,
        interval_s: float = 0.25,
        history_s: float = HISTORY_S,
    ) -> None:
        self._interval_s = max(1e-3, float(interval_s))
        self._history_s = max(self._interval_s, float(history_s))
        self._last: float | None = None
        # (timestamp, lag_ms)
        self._lags: deque[tuple[float, float]] = deque()

    def note_tick(self, now: float | None = None) -> float:
        """Record one timer fire. Returns lag_ms for this tick (0 on first)."""
        t = time.perf_counter() if now is None else float(now)
        lag_ms = 0.0
        if self._last is not None:
            actual = t - self._last
            lag_ms = max(0.0, (actual - self._interval_s) * 1000.0)
            self._lags.append((t, lag_ms))
        self._last = t
        self._prune(t)
        return lag_ms

    def _prune(self, now: float) -> None:
        cutoff = now - self._history_s
        lags = self._lags
        while lags and lags[0][0] < cutoff:
            lags.popleft()

    def lag_ms(self, window_s: float = LABEL_WINDOW_S) -> float:
        """Median lag over the last ``window_s`` seconds (0 if no samples)."""
        if window_s <= 0:
            return 0.0
        now = time.perf_counter()
        self._prune(now)
        cutoff = now - window_s
        vals = [lag for t, lag in self._lags if t >= cutoff]
        if not vals:
            return 0.0
        return float(statistics.median(vals))

    def samples(
        self, window_s: float | None = None
    ) -> list[tuple[float, float]]:
        """``(age_s, lag_ms)`` in the window, oldest first. ``age_s`` is ≤ 0."""
        win = self._history_s if window_s is None else float(window_s)
        if win <= 0:
            return []
        now = time.perf_counter()
        self._prune(now)
        cutoff = now - win
        return [(t - now, lag) for t, lag in self._lags if t >= cutoff]
