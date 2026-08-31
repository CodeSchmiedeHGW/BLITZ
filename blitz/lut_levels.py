"""LUT level calculation. Pure logic, numpy only, for easy unit testing."""
from __future__ import annotations

from typing import Literal

import numpy as np

GrayLutKind = Literal["occupancy", "counts", "signed", "generic"]

_UNIQUE_SAMPLE_CAP = 1_000_000
_COUNTS_ZERO_FRAC = 0.5


def calculate_lut_levels(image: np.ndarray, percentile: float) -> tuple[float, float]:
    """Compute LUT min/max from percentile or min/max (percentile=0)."""
    with np.errstate(invalid="ignore", over="ignore"):
        if percentile <= 0:
            return float(np.nanmin(image)), float(np.nanmax(image))
        p_lo, p_hi = percentile, 100.0 - percentile
        mn, mx = np.nanpercentile(image, [p_lo, p_hi])
        return float(mn), float(mx)


def _positive_p99_hi(arr: np.ndarray) -> float:
    """Top of an unsigned count ladder: p99 of strictly positive values."""
    with np.errstate(invalid="ignore", over="ignore"):
        mx = float(np.nanmax(arr)) if arr.size else 1.0
    if not np.isfinite(mx):
        mx = 1.0
    pos = arr[np.isfinite(arr) & (arr > 0)]
    if pos.size == 0:
        return max(mx, 1.0)
    return max(float(np.percentile(pos, 99.0)), 1.0)


def rgb_display_levels(image: np.ndarray) -> tuple[float, float]:
    """LUT range for RGB cubes (photos, occupancy, or event counts).

    uint8 → 0…255 (photos and EVT occupancy).
    float with max ≤ 1 → 0…1 (legacy EVT rungs).
    Otherwise (uint16 / float counts) → 0 … p99 of **positive** values so
    R and G share one ladder (yellow mixed pixels stay yellow).
    """
    arr = np.asarray(image)
    if arr.size == 0:
        return 0.0, 1.0
    if arr.dtype == np.uint8:
        return 0.0, 255.0
    with np.errstate(invalid="ignore", over="ignore"):
        mx = float(np.nanmax(arr)) if arr.size else 1.0
    if not np.isfinite(mx):
        mx = 1.0
    if arr.dtype.kind == "f" and mx <= 1.0 + 1e-3:
        return 0.0, 1.0
    return 0.0, _positive_p99_hi(arr)


def occupancy_display_levels(image: np.ndarray) -> tuple[float, float]:
    """Pin occupancy: 0…1 for 0/1 cubes, otherwise 0…255."""
    arr = np.asarray(image)
    if arr.size == 0:
        return 0.0, 255.0
    with np.errstate(invalid="ignore", over="ignore"):
        mx = float(np.nanmax(arr))
    if not np.isfinite(mx) or mx <= 1.0 + 1e-3:
        return 0.0, 1.0
    return 0.0, 255.0


def counts_display_levels(image: np.ndarray) -> tuple[float, float]:
    """Unsigned event counts: 0 … p99 of positive values."""
    arr = np.asarray(image)
    if arr.size == 0:
        return 0.0, 1.0
    return 0.0, _positive_p99_hi(arr)


def _as_gray(image: np.ndarray) -> np.ndarray:
    arr = np.asarray(image)
    if arr.ndim >= 1 and arr.shape[-1] == 1:
        return arr[..., 0]
    return arr


def _sample_flat(arr: np.ndarray) -> np.ndarray:
    flat = np.asarray(arr).ravel()
    n = int(flat.size)
    if n == 0:
        return flat
    if n > _UNIQUE_SAMPLE_CAP:
        step = max(1, n // _UNIQUE_SAMPLE_CAP)
        return flat[::step]
    return flat


def _unique_ints(sample: np.ndarray) -> set[int]:
    u = np.unique(sample)
    if u.dtype.kind == "f":
        u = u[np.isfinite(u)]
    return {int(x) for x in u.tolist()}


def classify_gray_lut(image: np.ndarray) -> GrayLutKind:
    """How Auto should colour a grayscale cube (no Qt).

    occupancy — integer unique ⊆ {0, 255} or ⊆ {0, 1} (EVT who-fired).
    counts — unsigned integer, >2 rungs, mostly zeros (sparse event counts).
    signed — values straddle zero (ON−OFF).
    generic — float, dense photos, everything else (plasma + Trim).
    """
    arr = _as_gray(image)
    if arr.size == 0:
        return "generic"
    with np.errstate(invalid="ignore", over="ignore"):
        mn = float(np.nanmin(arr))
        mx = float(np.nanmax(arr))
    if not np.isfinite(mn) or not np.isfinite(mx):
        return "generic"
    if mn < 0 < mx:
        return "signed"
    if arr.dtype.kind == "f":
        return "generic"
    if arr.dtype.kind not in "iu":
        return "generic"

    sample = _sample_flat(arr)
    vals = _unique_ints(sample)
    if vals <= {0, 1} or vals <= {0, 255}:
        return "occupancy"

    if mn >= 0 and len(vals) > 2:
        # uint8 photos have hundreds of gray levels; EVT 8-bit counts do not.
        if arr.dtype == np.uint8 and len(vals) > 64:
            return "generic"
        zero_frac = float(np.count_nonzero(sample == 0)) / float(sample.size)
        if zero_frac > _COUNTS_ZERO_FRAC:
            return "counts"
    return "generic"


def gray_auto_colormap(
    image: np.ndarray,
) -> tuple[str, tuple[float, float] | None]:
    """Colormap name and optional level override for grayscale Auto.

    ``None`` levels means keep Trim / min-max from ``calculate_lut_levels``.
    """
    kind = classify_gray_lut(image)
    if kind == "occupancy":
        return "event", occupancy_display_levels(image)
    if kind == "counts":
        return "event", counts_display_levels(image)
    if kind == "signed":
        with np.errstate(invalid="ignore", over="ignore"):
            mn = float(np.nanmin(image))
            mx = float(np.nanmax(image))
        if not np.isfinite(mn):
            mn = -1.0
        if not np.isfinite(mx):
            mx = 1.0
        r = max(abs(mn), abs(mx), 1.0)
        return "bipolar", (-r, r)
    return "plasma", None
