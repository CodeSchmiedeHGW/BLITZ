"""BLITZ colormap presets on top of pyqtgraph Gradients.

Importing this module registers ``event`` so the LUT combo and Auto can
use it for EVT polarity **states** (uint8 0 / 85 / 170 / 255).
Ticks: black → red → green → yellow (none / OFF / ON / both).
"""
from __future__ import annotations

from pyqtgraph.graphicsItems.GradientEditorItem import Gradients

EVENT_CMAP = "event"

_EVENT_GRADIENT = {
    "ticks": [
        (0.0, (0, 0, 0, 255)),
        (1.0 / 3.0, (255, 0, 0, 255)),
        (2.0 / 3.0, (0, 255, 0, 255)),
        (1.0, (255, 255, 0, 255)),
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
