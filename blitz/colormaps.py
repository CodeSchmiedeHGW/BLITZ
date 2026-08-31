"""BLITZ colormap presets on top of pyqtgraph Gradients.

Importing this module registers ``event`` so the LUT combo and Auto can
use it. Tick colours: black → dark blue → amber (sparse event counts;
occupancy only hits the endpoints).
"""
from __future__ import annotations

from pyqtgraph.graphicsItems.GradientEditorItem import Gradients

EVENT_CMAP = "event"

_EVENT_GRADIENT = {
    "ticks": [
        (0.0, (0, 0, 0, 255)),
        (0.28, (8, 28, 88, 255)),
        (0.62, (36, 96, 168, 255)),
        (1.0, (255, 196, 48, 255)),
    ],
    "mode": "rgb",
}

_registered = False


def ensure_registered() -> None:
    """Idempotent: add the event preset to pyqtgraph Gradients."""
    global _registered
    if _registered and EVENT_CMAP in Gradients:
        return
    Gradients[EVENT_CMAP] = _EVENT_GRADIENT
    _registered = True


ensure_registered()
