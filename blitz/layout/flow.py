"""View-only D8 accumulation overlay. Analysis buffer stays original height."""

from __future__ import annotations

import time
from typing import Callable, Optional

import numpy as np
import pyqtgraph as pg
from PyQt6 import sip
from PyQt6.QtCore import QRectF, QTimer
from PyQt6.QtWidgets import QLabel

from ..data.flow import accumulation_rgba, d8_accumulation
from ..data.hillshade import extract_viewport_patch
from .viewer import ImageViewer


def _qobj_alive(obj) -> bool:
    return obj is not None and not sip.isdeleted(obj)


class FlowAdapter:
    """Paint D8 accumulation on a separate ImageItem; never replaces viewer.image."""

    def __init__(
        self,
        viewer: ImageViewer,
        status_label: Optional[QLabel] = None,
        on_compute: Optional[Callable[[], None]] = None,
    ) -> None:
        self.viewer = viewer
        self._status = status_label
        self._on_compute = on_compute
        self._preview = False
        self.last_compute_s: Optional[float] = None
        self._log_scale = True
        self._overlay_rect: Optional[tuple[float, float, float, float]] = None

        self._item = pg.ImageItem()
        self._item.setZValue(0.15)
        self._item.setOpacity(0.92)
        self._item.setVisible(False)
        try:
            self._item.setOpts(axisOrder=viewer.imageItem.axisOrder)
        except Exception:
            pass
        viewer.view.addItem(self._item)

        self._timer = QTimer(viewer)
        self._timer.setSingleShot(True)
        self._timer.setInterval(80)
        self._timer.timeout.connect(self._refresh_now)
        self._view_timer = QTimer(viewer)
        self._view_timer.setSingleShot(True)
        self._view_timer.setInterval(150)
        self._view_timer.timeout.connect(self._refresh_now)

        viewer.timeLine.sigPositionChanged.connect(self._schedule)
        viewer.image_changed.connect(self._schedule)
        viewer.image_size_changed.connect(self._schedule)
        viewer.destroyed.connect(self._on_viewer_destroyed)
        try:
            self._vb = viewer.view.getViewBox()
        except Exception:
            self._vb = None

    def _notify_compute(self) -> None:
        cb = self._on_compute
        if cb is not None:
            cb()

    def set_preview(self, on: bool) -> None:
        self._preview = bool(on)
        if not self._preview:
            self._stop_timer()
            if _qobj_alive(self._item):
                try:
                    self._item.clear()
                    self._item.setVisible(False)
                except RuntimeError:
                    pass
            self._overlay_rect = None
            self._set_status("Flow off · analysis = height")
            self._set_view_tracking(False)
            self._notify_compute()
            return
        self._set_view_tracking(True)
        self._schedule()

    def set_log_scale(self, on: bool) -> None:
        want = bool(on)
        if want == self._log_scale:
            return
        self._log_scale = want
        if self._preview:
            self._schedule()

    def _stop_timer(self) -> None:
        for timer in (self._timer, getattr(self, "_view_timer", None)):
            if not _qobj_alive(timer):
                continue
            try:
                timer.stop()
            except RuntimeError:
                pass

    def _schedule(self, *_args) -> None:
        if not self._preview:
            return
        if not _qobj_alive(self._timer):
            return
        try:
            self._timer.start()
        except RuntimeError:
            return

    def _set_view_tracking(self, on: bool) -> None:
        vb = getattr(self, "_vb", None)
        if vb is None:
            return
        try:
            vb.sigRangeChanged.disconnect(self._schedule_view)
        except (TypeError, RuntimeError):
            pass
        if on:
            try:
                vb.sigRangeChanged.connect(self._schedule_view)
            except (TypeError, RuntimeError):
                pass

    def _schedule_view(self, *_args) -> None:
        if not self._preview:
            return
        timer = getattr(self, "_view_timer", None)
        if not _qobj_alive(timer):
            return
        try:
            timer.start()
        except RuntimeError:
            return

    def _on_viewer_destroyed(self, *_args) -> None:
        self._preview = False
        self._set_view_tracking(False)
        self._stop_timer()

    def _height_frame(self) -> Optional[np.ndarray]:
        img = self.viewer.image
        if img is None:
            return None
        try:
            frame = img[int(self.viewer.currentIndex)]
        except Exception:
            return None
        if frame is None or np.size(frame) == 0:
            return None
        return np.asarray(frame)

    def _view_window(
        self,
        frame: np.ndarray,
    ) -> tuple[float, float, float, float, str]:
        order = str(getattr(self.viewer.imageItem, "axisOrder", "col-major"))
        spatial = np.asarray(frame).shape[:2]
        if order == "row-major":
            ny, nx = int(spatial[0]), int(spatial[1])
        else:
            nx, ny = int(spatial[0]), int(spatial[1])
        x0, x1, y0, y1 = 0.0, float(nx), 0.0, float(ny)
        try:
            vb = self.viewer.view.getViewBox()
            (vx0, vx1), (vy0, vy1) = vb.viewRange()
            x0, x1, y0, y1 = float(vx0), float(vx1), float(vy0), float(vy1)
        except Exception:
            pass
        return x0, x1, y0, y1, order

    def _viewport_patch(
        self,
    ) -> Optional[tuple[np.ndarray, tuple[float, float, float, float]]]:
        frame = self._height_frame()
        if frame is None:
            return None
        x0, x1, y0, y1, order = self._view_window(frame)
        return extract_viewport_patch(
            frame,
            x0,
            x1,
            y0,
            y1,
            axis_order=order,
        )

    def _refresh_now(self) -> None:
        if not self._preview:
            return
        if not _qobj_alive(self._item):
            return
        spec = self._viewport_patch()
        if spec is None:
            self._item.setVisible(False)
            self._set_status("No image · load a height map first")
            return
        patch, rect = spec
        self._overlay_rect = rect
        t0 = time.perf_counter()
        try:
            acc = d8_accumulation(patch)
            rgba = accumulation_rgba(acc, log_scale=self._log_scale)
        except Exception as e:
            self.last_compute_s = None
            self._item.setVisible(False)
            self._set_status(f"Flow failed: {e}")
            self._notify_compute()
            return
        self.last_compute_s = time.perf_counter() - t0
        self._notify_compute()
        self._patch_hw = (int(acc.shape[0]), int(acc.shape[1]))
        self._item.setImage(rgba, autoLevels=False)
        rx, ry, rw, rh = rect
        self._item.setRect(QRectF(rx, ry, rw, rh))
        self._item.setVisible(True)
        scale = "log1p" if self._log_scale else "linear"
        h, w = int(acc.shape[0]), int(acc.shape[1])
        ms = 1000.0 * self.last_compute_s
        fps = (1.0 / self.last_compute_s) if self.last_compute_s > 1e-9 else 0.0
        self._set_status(
            f"D8 accumulation {scale} · {h}×{w} viewport · "
            f"{ms:.1f} ms ({fps:.0f} fps) · analysis = height"
        )

    def _set_status(self, text: str) -> None:
        if not _qobj_alive(self._status):
            return
        try:
            self._status.setText(text)
        except RuntimeError:
            pass
