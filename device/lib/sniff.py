import time

from machine import Pin

RX_PIN = 19
GAP_US = 20000  # a pause longer than this means a new frame starts
MIN_EDGES = 40  # ignore short bursts of noise
MAX_EDGES = 1200  # one frame is about 515 pulses, so this is a safe cap

FIRST_SHORT_US = 400
FIRST_LONG_US = 1100
FIRST_HEADER_US = 2388

SECOND_SHORT_US = 570
SECOND_LONG_US = 1500
SECOND_HEADER_US = 7292

TOLERANCE = 0.3


def capture(timeout_s=10):
    """Record pulse durations (us) from the receiver until a frame boundary is seen."""
    pin = Pin(RX_PIN, Pin.IN)
    deadline = time.ticks_add(time.ticks_ms(), int(timeout_s * 1000))

    edges = []
    last_level = pin.value()
    last_time = time.ticks_us()

    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        level = pin.value()
        if level == last_level:
            continue

        now = time.ticks_us()
        duration = time.ticks_diff(now, last_time)
        last_level = level
        last_time = now

        if duration > GAP_US:
            if len(edges) >= MIN_EDGES:
                return edges
            edges = []
            continue

        edges.append(duration)

        if len(edges) >= MAX_EDGES:
            return edges

    return edges


def _close(value, expected):
    """Check that a measured duration is within tolerance of the expected one."""
    return abs(value - expected) < expected * TOLERANCE


def _decode_blocks(pulses, short_us, long_us, header_us, bit_count):
    """Decode every repetition of a block found in the frame."""
    values = []
    start = 0

    while start < len(pulses) - 1:
        # a block starts with a short HIGH followed by the long header LOW
        if not (_close(pulses[start], short_us)
                and _close(pulses[start + 1], header_us)):
            start += 1
            continue

        value = 0
        decoded = 0
        index = start + 2
        while decoded < bit_count and index + 1 < len(pulses):
            high, low = pulses[index], pulses[index + 1]
            if _close(high, long_us) and _close(low, short_us):
                value = (value << 1) | 1
            elif _close(high, short_us) and _close(low, long_us):
                value = value << 1
            else:
                break
            decoded += 1
            index += 2

        if decoded == bit_count:
            values.append(value)
            start = index
        else:
            start += 1

    return values


def _vote(counts):
    """Return the most frequently seen value."""
    return max(counts, key=counts.get)


def learn(timeout_s=8, top=3):
    deadline = time.ticks_add(time.ticks_ms(), int(timeout_s * 1000))
    first_counts = {}
    second_counts = {}

    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        pulses = capture(timeout_s=1)

        for value in _decode_blocks(pulses, FIRST_SHORT_US, FIRST_LONG_US,
                                    FIRST_HEADER_US, 24):
            first_counts[value] = first_counts.get(value, 0) + 1

        for value in _decode_blocks(pulses, SECOND_SHORT_US, SECOND_LONG_US,
                                    SECOND_HEADER_US, 32):
            second_counts[value] = second_counts.get(value, 0) + 1

    def ranked(counts):
        return sorted(counts.items(), key=lambda item: -item[1])[:top]

    return ranked(first_counts), ranked(second_counts)
