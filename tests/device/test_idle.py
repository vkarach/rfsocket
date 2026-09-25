import pytest

import idle


def timer(now=0):
    return idle.IdleTimer(clock_after_ms=60_000, sleep_after_ms=300_000, now_ms=now)


@pytest.mark.parametrize("elapsed, screen", [
    (0, idle.STATUS),
    (59_999, idle.STATUS),
    (60_000, idle.CLOCK),
    (299_999, idle.CLOCK),
    (300_000, idle.OFF),
    (10_000_000, idle.OFF),
])
def test_screen_by_idle_time(elapsed, screen):
    assert timer().screen(elapsed) == screen


def test_touch_restarts_countdown():
    t = timer()
    t.touch(250_000)

    assert t.screen(300_000) == idle.STATUS
    assert t.screen(550_000) == idle.OFF


@pytest.mark.parametrize("screen", [idle.STATUS, idle.CLOCK, idle.OFF])
def test_pinned_screen_ignores_idle_time(screen):
    t = timer()
    t.pin(screen)

    assert t.screen(0) == screen
    assert t.screen(10_000_000) == screen


def test_touch_keeps_pin():
    t = timer()
    t.pin(idle.CLOCK)
    t.touch(5_000)

    assert t.screen(6_000) == idle.CLOCK


def test_unpin_resumes_timers_from_last_touch():
    t = timer()
    t.pin(idle.CLOCK)
    t.touch(1_000_000)
    t.pin(None)

    assert t.screen(1_000_000) == idle.STATUS
    assert t.screen(1_300_000) == idle.OFF


def test_pinned_reports_pin():
    t = timer()
    assert t.pinned is None

    t.pin(idle.OFF)
    assert t.pinned == idle.OFF

    t.pin(None)
    assert t.pinned is None


def test_pin_rejects_unknown_screen():
    with pytest.raises(ValueError):
        timer().pin("disco")


def test_injected_diff_handles_tick_wrap():
    t = idle.IdleTimer(60_000, 300_000, now_ms=990_000, diff=lambda a, b: (a - b) % 1_000_000)

    assert t.screen(60_000) == idle.CLOCK
