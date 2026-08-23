"""Display-downsample factor gate (no widget)."""

from blitz.layout.display_downsample import factors_changed


def test_none_factors_do_not_rebuild() -> None:
    assert factors_changed((1, 1), (None, None)) is False
    assert factors_changed((1, 1), (2, None)) is False


def test_same_factors_do_not_rebuild() -> None:
    assert factors_changed((2, 2), (2, 2)) is False


def test_zoom_out_rebuilds() -> None:
    assert factors_changed((1, 1), (2, 2)) is True
    assert factors_changed(None, (1, 1)) is True
