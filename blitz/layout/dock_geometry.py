"""DockArea / QSplitter helpers.

pyqtgraph ``Dock.hide()`` is a normal ``QWidget.hide()``. The parent
``QSplitter`` keeps a 0 px slice, so ``show()`` plus ``setMinimumHeight``
still leaves a dead strip the user must drag open. Restore the pane size
explicitly when T>1 data arrives.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QSplitter, QWidget


def splitter_widget_extent(widget: QWidget) -> int:
    """Current px of ``widget`` along its parent splitter, or 0."""
    if widget is None:
        return 0
    parent = widget.parentWidget()
    if not isinstance(parent, QSplitter):
        return 0
    idx = parent.indexOf(widget)
    if idx < 0:
        return 0
    sizes = parent.sizes()
    if idx >= len(sizes):
        return 0
    return int(sizes[idx])


def restore_splitter_widget_extent(
    widget: QWidget,
    min_px: int,
    *,
    preferred_px: int | None = None,
    keep_sibling_px: int = 200,
) -> bool:
    """Give ``widget`` at least ``min_px`` in its parent ``QSplitter``.

    Steals pixels from the largest *visible* sibling so a hidden neighbour
    (e.g. Polyline) is not allocated space. No-op when the pane is already
    tall enough. Returns True if ``setSizes`` ran.
    """
    if widget is None or min_px <= 0:
        return False
    parent = widget.parentWidget()
    if not isinstance(parent, QSplitter):
        return False
    idx = parent.indexOf(widget)
    if idx < 0:
        return False
    sizes = list(parent.sizes())
    if idx >= len(sizes):
        return False
    if sizes[idx] >= min_px:
        return False
    target = max(min_px, int(preferred_px or 0))
    need = target - sizes[idx]
    candidates: list[int] = []
    for i in range(len(sizes)):
        if i == idx:
            continue
        sibling = parent.widget(i)
        if sibling is None or sibling.isHidden():
            continue
        candidates.append(i)
    if not candidates:
        return False
    steal_i = max(candidates, key=lambda i: sizes[i])
    take = min(need, max(0, sizes[steal_i] - keep_sibling_px))
    if take <= 0:
        return False
    sizes[steal_i] -= take
    sizes[idx] += take
    parent.setSizes(sizes)
    return True
