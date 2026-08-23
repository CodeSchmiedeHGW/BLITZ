"""Display-only ImageItem downsample — paint, not analysis.

pyqtgraph's immediate ``autoDownsample`` rebuilds the QImage on every
ViewBox change. That blocks wheel zoom-out on large frames. We keep the
last QImage (ViewBox scales it) and rebuild after the gesture settles.
Never blank the item when device mapping is not ready.
"""

from __future__ import annotations

from PyQt6.QtCore import QTimer


def factors_changed(
    last: tuple[int, int] | None,
    new: tuple[int | None, int | None],
) -> bool:
    xds, yds = new
    if xds is None or yds is None:
        return False
    pair = (int(xds), int(yds))
    if last is None:
        return True
    return pair != (int(last[0]), int(last[1]))


def install_debounced_auto_downsample(
    item,
    *,
    settle_ms: int = 80,
) -> None:
    """Enable paint downsample; rebuild QImage only after ViewBox settles."""
    item.autoDownsample = True
    timer = QTimer(item)
    timer.setSingleShot(True)
    timer.setInterval(max(1, int(settle_ms)))

    def flush() -> None:
        if getattr(item, "image", None) is None:
            return
        try:
            new = item._computeDownsampleFactors()
        except Exception:
            return
        last = getattr(item, "_lastDownsample", (1, 1))
        if not factors_changed(last, new):
            return
        item._renderRequired = True
        item.update()

    def on_view_transform_changed() -> None:
        try:
            new = item._computeDownsampleFactors()
        except Exception:
            return
        last = getattr(item, "_lastDownsample", (1, 1))
        if not factors_changed(last, new):
            return
        timer.start()

    timer.timeout.connect(flush)
    item.viewTransformChanged = on_view_transform_changed
    item._blitz_ds_timer = timer
