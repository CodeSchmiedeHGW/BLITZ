"""Tests for LUT panel: level calculation (unit) and manual integration procedure.

Run unit tests: pytest _aux/tests/test_lut.py -v
Unit tests need only numpy (no Qt).
"""
from __future__ import annotations

import numpy as np
import pytest

from blitz.lut_levels import (
    calculate_lut_levels,
    classify_gray_lut,
    counts_display_levels,
    gray_auto_colormap,
    occupancy_display_levels,
    rgb_display_levels,
)


class TestCalculateLutLevels:
    """Unit tests for LUT level computation."""

    def test_minmax_percentile_zero(self) -> None:
        img = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        mn, mx = calculate_lut_levels(img, 0)
        assert mn == 10.0
        assert mx == 50.0

    def test_minmax_percentile_negative(self) -> None:
        img = np.array([1.0, 2.0, 3.0])
        mn, mx = calculate_lut_levels(img, -1)
        assert mn == 1.0
        assert mx == 3.0

    def test_percentile_1pct_clips_extrema(self) -> None:
        img = np.concatenate([
            [0.0, 100.0],
            np.linspace(10, 90, 98),
        ])
        mn, mx = calculate_lut_levels(img, 1.0)
        assert 0.0 < mn < 10.0
        assert 90.0 < mx < 100.0

    def test_percentile_handles_nans(self) -> None:
        img = np.array([1.0, np.nan, 5.0, np.nan, 10.0], dtype=np.float32)
        mn, mx = calculate_lut_levels(img, 0)
        assert mn == 1.0
        assert mx == 10.0

    def test_percentile_3d_stack(self) -> None:
        np.random.seed(42)
        img = np.random.rand(50, 64, 64).astype(np.float32)
        mn, mx = calculate_lut_levels(img, 1.0)
        global_min, global_max = float(np.nanmin(img)), float(np.nanmax(img))
        assert mn >= global_min
        assert mx <= global_max
        assert mn < mx

    def test_percentile_symmetric_bipolar(self) -> None:
        img = np.array([-100.0, -10.0, 0.0, 10.0, 100.0])
        mn, mx = calculate_lut_levels(img, 0)
        assert mn == -100.0
        assert mx == 100.0


class TestRgbDisplayLevels:
    def test_uint8_photos_and_occupancy(self) -> None:
        img = np.zeros((4, 4, 3), dtype=np.uint8)
        img[1, 1] = (255, 255, 0)
        mn, mx = rgb_display_levels(img)
        assert mn == 0.0
        assert mx == 255.0

    def test_float_rungs_zero_to_one(self) -> None:
        img = np.zeros((2, 2, 3), dtype=np.float32)
        img[0, 0, 1] = 0.5
        mn, mx = rgb_display_levels(img)
        assert mn == 0.0
        assert mx == 1.0

    def test_uint16_counts_use_p99(self) -> None:
        img = np.zeros((100, 100, 3), dtype=np.uint16)
        img[:, :, 1] = 3
        img[0, 0, 1] = 1000
        mn, mx = rgb_display_levels(img)
        assert mn == 0.0
        assert mx == 3.0

    def test_empty_and_zeros(self) -> None:
        assert rgb_display_levels(np.zeros((0,))) == (0.0, 1.0)
        mn, mx = rgb_display_levels(np.zeros((2, 2, 3), dtype=np.uint16))
        assert mn == 0.0
        assert mx == 1.0


class TestClassifyGrayLut:
    def test_occupancy_uint8_0_255(self) -> None:
        img = np.zeros((8, 8), dtype=np.uint8)
        img[2, 3] = 255
        assert classify_gray_lut(img) == "occupancy"
        assert occupancy_display_levels(img) == (0.0, 255.0)
        cmap, levels = gray_auto_colormap(img)
        assert cmap == "event"
        assert levels == (0.0, 255.0)

    def test_occupancy_uint8_0_1(self) -> None:
        img = np.zeros((8, 8), dtype=np.uint8)
        img[1, 1] = 1
        assert classify_gray_lut(img) == "occupancy"
        assert occupancy_display_levels(img) == (0.0, 1.0)
        cmap, levels = gray_auto_colormap(img)
        assert cmap == "event"
        assert levels == (0.0, 1.0)

    def test_occupancy_squeezes_channel_axis(self) -> None:
        img = np.zeros((2, 4, 4, 1), dtype=np.uint8)
        img[0, 1, 1, 0] = 255
        assert classify_gray_lut(img) == "occupancy"

    def test_uint16_sparse_counts_p99(self) -> None:
        img = np.zeros((200, 200), dtype=np.uint16)
        img[:20, :] = 3
        img[0, 0] = 1000
        assert classify_gray_lut(img) == "counts"
        mn, mx = counts_display_levels(img)
        assert mn == 0.0
        assert mx == 3.0
        cmap, levels = gray_auto_colormap(img)
        assert cmap == "event"
        assert levels == (0.0, 3.0)

    def test_signed_int16_bipolar(self) -> None:
        img = np.array([[-4, 0, 2]], dtype=np.int16)
        assert classify_gray_lut(img) == "signed"
        cmap, levels = gray_auto_colormap(img)
        assert cmap == "bipolar"
        assert levels == (-4.0, 4.0)

    def test_float_stays_plasma(self) -> None:
        img = np.linspace(0.0, 10.0, 64).reshape(8, 8).astype(np.float32)
        assert classify_gray_lut(img) == "generic"
        cmap, levels = gray_auto_colormap(img)
        assert cmap == "plasma"
        assert levels is None

    def test_dense_uint16_stays_generic(self) -> None:
        img = np.arange(256, dtype=np.uint16).reshape(16, 16)
        img = img + 10
        assert classify_gray_lut(img) == "generic"
