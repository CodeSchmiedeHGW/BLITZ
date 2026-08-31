"""QSplitter pane restore after hide()/show() (offscreen Qt)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QSplitter, QWidget

from blitz.layout.dock_geometry import (
    restore_splitter_widget_extent,
    splitter_widget_extent,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["test_dock_geometry"])
    return app


def _vertical_split(qapp, *, height: int = 600) -> tuple[QSplitter, QWidget, QWidget]:
    split = QSplitter()
    split.setOrientation(Qt.Orientation.Vertical)
    top = QWidget()
    bottom = QWidget()
    split.addWidget(top)
    split.addWidget(bottom)
    split.resize(400, height)
    split.setSizes([height - 120, 120])
    split.show()
    qapp.processEvents()
    return split, top, bottom


def test_restore_after_collapsed_show(qapp) -> None:
    split, _top, bottom = _vertical_split(qapp)
    bottom.hide()
    qapp.processEvents()
    bottom.show()
    qapp.processEvents()
    split.setSizes([600, 0])
    qapp.processEvents()
    assert split.sizes()[1] < 20
    assert restore_splitter_widget_extent(bottom, 100, preferred_px=120)
    qapp.processEvents()
    assert split.sizes()[1] >= 100


def test_restore_skips_hidden_sibling(qapp) -> None:
    split = QSplitter()
    split.setOrientation(Qt.Orientation.Vertical)
    top = QWidget()
    hidden = QWidget()
    bottom = QWidget()
    split.addWidget(top)
    split.addWidget(hidden)
    split.addWidget(bottom)
    split.resize(400, 600)
    split.setSizes([500, 80, 20])
    split.show()
    qapp.processEvents()
    hidden.hide()
    qapp.processEvents()
    split.setSizes([580, 0, 0])
    qapp.processEvents()
    assert restore_splitter_widget_extent(bottom, 100)
    qapp.processEvents()
    sizes = split.sizes()
    assert sizes[2] >= 100
    # Hidden middle pane stays collapsed.
    assert sizes[1] <= 10


def test_restore_noop_when_already_tall(qapp) -> None:
    split, _top, bottom = _vertical_split(qapp)
    before = list(split.sizes())
    assert not restore_splitter_widget_extent(bottom, 80)
    assert split.sizes() == before


def test_restore_false_without_splitter(qapp) -> None:
    w = QWidget()
    w.show()
    qapp.processEvents()
    assert not restore_splitter_widget_extent(w, 100)
    assert splitter_widget_extent(w) == 0
