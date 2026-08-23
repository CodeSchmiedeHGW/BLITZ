"""Sliding-window UI event-loop lag (no Qt widgets required)."""

from blitz.layout.responsiveness import ResponsivenessMeter


def test_lag_median_from_injected_ticks(monkeypatch) -> None:
    m = ResponsivenessMeter(interval_s=0.25, history_s=30.0)
    # First tick anchors; no lag sample yet
    assert m.note_tick(100.00) == 0.0
    assert m.lag_ms(1.0) == 0.0

    # On time → 0 ms lag
    assert abs(m.note_tick(100.25) - 0.0) < 1e-9
    # 50 ms late
    assert abs(m.note_tick(100.55) - 50.0) < 1e-6
    # 10 ms late
    assert abs(m.note_tick(100.81) - 10.0) < 1e-6

    monkeypatch.setattr(
        "blitz.layout.responsiveness.time.perf_counter",
        lambda: 100.81,
    )
    # Samples in 1 s: 0, 50, 10 → median 10
    assert abs(m.lag_ms(1.0) - 10.0) < 1e-6
    got = m.samples(1.0)
    assert len(got) == 3
    assert abs(got[0][1] - 0.0) < 1e-6
    assert abs(got[1][1] - 50.0) < 1e-6
    assert abs(got[2][1] - 10.0) < 1e-6
    # age_s ≤ 0, oldest first
    assert got[0][0] < got[1][0] < got[2][0] <= 0.0


def test_short_median_keeps_long_history(monkeypatch) -> None:
    m = ResponsivenessMeter(interval_s=0.25, history_s=30.0)
    m.note_tick(100.00)
    m.note_tick(100.30)  # lag sample at 100.30
    m.note_tick(101.60)  # new sample; old still in 30 s history

    monkeypatch.setattr(
        "blitz.layout.responsiveness.time.perf_counter",
        lambda: 101.60,
    )
    assert len(m.samples(1.0)) == 1
    assert len(m.samples(30.0)) == 2
    assert len(m.samples()) == 2


def test_history_prunes_beyond_retention(monkeypatch) -> None:
    m = ResponsivenessMeter(interval_s=0.25, history_s=30.0)
    m.note_tick(100.00)
    m.note_tick(100.25)
    m.note_tick(140.00)  # 40 s later — first lag ages out of 30 s

    monkeypatch.setattr(
        "blitz.layout.responsiveness.time.perf_counter",
        lambda: 140.00,
    )
    assert len(m.samples()) == 1


def test_lag_zero_when_empty() -> None:
    assert ResponsivenessMeter().lag_ms() == 0.0
    assert ResponsivenessMeter().samples() == []


def test_lag_phase_bands() -> None:
    from blitz.layout.responsiveness import lag_phase

    assert lag_phase(0.0) == "ok"
    assert lag_phase(99.9) == "ok"
    assert lag_phase(100.0) == "warn"
    assert lag_phase(300.0) == "warn"
    assert lag_phase(300.1) == "bad"