"""LUT-corner HUD: always-on UI event-loop lag (responsiveness amp)."""

import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget

from ..theme import COLOR_GREEN, COLOR_RED, COLOR_YELLOW, get_plot_bg
from .responsiveness import (
    HISTORY_S,
    SMOOTH_MS,
    WARN_MS,
    Y_MAX_MS,
    lag_phase,
)

# Curve / label colors (Tokyo Night)
_PHASE_RGB = {
    "ok": (158, 206, 106),
    "warn": (224, 175, 104),
    "bad": (247, 118, 142),
}
_PHASE_HEX = {
    "ok": COLOR_GREEN,
    "warn": COLOR_YELLOW,
    "bad": COLOR_RED,
}


def _mini_plot(parent: QWidget, h: int = 40) -> tuple[pg.PlotWidget, pg.PlotDataItem]:
    """Sparkline: last HISTORY_S s, Y 0..Y_MAX_MS, green/yellow bands."""
    pw = pg.PlotWidget(background=get_plot_bg(), parent=parent)
    pw.setFixedSize(96, h)
    pw.hideAxis("left")
    pw.hideAxis("bottom")
    pw.setMouseEnabled(False, False)
    vb = pw.getViewBox()
    vb.setRange(xRange=(-HISTORY_S, 0.0), yRange=(0.0, Y_MAX_MS), padding=0.0)
    vb.disableAutoRange()
    vb.setLimits(
        xMin=-HISTORY_S,
        xMax=0.0,
        yMin=0.0,
        yMax=Y_MAX_MS,
    )
    for lo, hi, rgba in (
        (0.0, SMOOTH_MS, (158, 206, 106, 55)),
        (SMOOTH_MS, Y_MAX_MS, (224, 175, 104, 55)),
    ):
        band = pg.LinearRegionItem(
            values=(lo, hi),
            orientation="horizontal",
            brush=rgba,
            pen=pg.mkPen(None),
            movable=False,
        )
        band.setZValue(-10)
        pw.addItem(band)
    curve = pw.plot(pen=pg.mkPen(_PHASE_RGB["ok"], width=1.4))
    return pw, curve


class BenchCompact(QFrame):
    """Bottom-right LUT HUD: UI lag label + ampel amp. No CPU/RAM here."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(96)
        self.setMaximumWidth(128)
        self.setToolTip(
            f"UI event-loop lag. Label = median ~1 s; amp = last {HISTORY_S:.0f} s "
            f"(Y 0–{Y_MAX_MS:.0f} ms). "
            f"Green under {SMOOTH_MS:.0f} ms (smooth); "
            f"yellow {SMOOTH_MS:.0f}–{WARN_MS:.0f}; "
            f"red over {WARN_MS:.0f} (clips at top). "
            "Not paint FPS, not Shade/Flow 1/dt."
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self._plot_lag, self._curve_lag = _mini_plot(self)
        self._label_lag = QLabel("UI: —")
        self._label_lag.setStyleSheet("font-size: 9pt;")
        layout.addWidget(self._plot_lag)
        layout.addWidget(self._label_lag)

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self._set_phase(None)

    def _set_phase(self, phase: str | None) -> None:
        if phase is None:
            self._label_lag.setStyleSheet("font-size: 9pt;")
            self._curve_lag.setPen(pg.mkPen(_PHASE_RGB["ok"], width=1.4))
            return
        hex_c = _PHASE_HEX[phase]
        self._label_lag.setStyleSheet(
            f"font-size: 9pt; font-weight: bold; color: {hex_c};"
        )
        self._curve_lag.setPen(pg.mkPen(_PHASE_RGB[phase], width=1.4))

    def set_ui_lag(
        self,
        lag_ms: float | None,
        samples: list[tuple[float, float]] | None = None,
    ) -> None:
        if lag_ms is None:
            self._label_lag.setText("UI: —")
            self._set_phase(None)
        else:
            phase = lag_phase(lag_ms)
            self._label_lag.setText(f"UI {lag_ms:.0f} ms")
            self._set_phase(phase)
        if samples is None:
            return
        if not samples:
            self._curve_lag.setData([], [])
            return
        x = np.asarray([age for age, _ in samples], dtype=float)
        y = np.clip(
            np.asarray([lag for _, lag in samples], dtype=float),
            0.0,
            Y_MAX_MS,
        )
        self._curve_lag.setData(x, y)
