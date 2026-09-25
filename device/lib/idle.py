STATUS = "status"
CLOCK = "clock"
OFF = "off"
SCREENS = (STATUS, CLOCK, OFF)


class IdleTimer:
    def __init__(self, sleep_after_ms, now_ms, diff=lambda a, b: a - b):
        self._sleep_after = sleep_after_ms
        self._diff = diff
        self._last = now_ms
        self._pinned = None

    def touch(self, now_ms):
        self._last = now_ms

    @property
    def pinned(self):
        return self._pinned

    def pin(self, screen):
        if screen is not None and screen not in SCREENS:
            raise ValueError("unknown screen: %s" % screen)
        self._pinned = screen

    def screen(self, now_ms):
        if self._pinned is not None:
            return self._pinned
        elapsed = self._diff(now_ms, self._last)
        if elapsed >= self._sleep_after:
            return OFF
        return CLOCK
