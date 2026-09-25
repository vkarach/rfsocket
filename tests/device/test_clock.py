import asyncio
import calendar
import socket
import struct
import threading

import pytest

import clock

CET = 3600


def utc(*fields):
    return calendar.timegm(fields + (0,) * (6 - len(fields)))


@pytest.mark.parametrize("days", [0, 1, 10957, 20000, 20723, 36524, 50000])
def test_civil_roundtrip(days):
    assert clock.days_from_civil(*clock.civil_from_days(days)) == days


def test_known_civil_dates():
    assert clock.days_from_civil(1970, 1, 1) == 0
    assert clock.days_from_civil(2000, 1, 1) == 10957
    assert clock.civil_from_days(utc(2026, 9, 25) // 86400) == (2026, 9, 25)


@pytest.mark.parametrize("moment, expected", [
    (utc(2026, 1, 15, 12), False),
    (utc(2026, 7, 15, 12), True),
    (utc(2026, 3, 29, 0, 59, 59), False),
    (utc(2026, 3, 29, 1), True),
    (utc(2026, 10, 25, 0, 59, 59), True),
    (utc(2026, 10, 25, 1), False),
    (utc(2027, 3, 28, 1), True),
    (utc(2027, 3, 27, 12), False),
])
def test_eu_dst_boundaries(moment, expected):
    assert clock.eu_dst(moment) is expected


def test_local_hm_applies_offset_and_dst():
    assert clock.local_hm(utc(2026, 1, 15, 12, 5), CET, True) == (13, 5)
    assert clock.local_hm(utc(2026, 7, 15, 12, 5), CET, True) == (14, 5)
    assert clock.local_hm(utc(2026, 7, 15, 12, 5), CET, False) == (13, 5)
    assert clock.local_hm(utc(2026, 7, 15, 23, 30), CET, True) == (1, 30)


def ntp_reply(unix):
    return bytes(40) + struct.pack("!I", unix + clock.NTP_UNIX_DELTA) + bytes(4)


def test_unix_from_ntp():
    assert clock.unix_from_ntp(ntp_reply(1_790_000_000)) == 1_790_000_000


def test_unix_from_short_packet_raises():
    with pytest.raises(ValueError):
        clock.unix_from_ntp(bytes(20))


def test_clock_unknown_until_set():
    assert clock.Clock().unix(0) is None


def test_clock_advances_with_ticks():
    c = clock.Clock()
    c.set(1000, 5000)

    assert c.unix(8500) == 1003


def test_clock_uses_injected_tick_diff():
    c = clock.Clock(diff=lambda a, b: (a - b) % 100_000)
    c.set(1000, 99_000)

    assert c.unix(2_000) == 1003


def fake_ntp_server(unix):
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(("127.0.0.1", 0))

    def reply():
        request, addr = server.recvfrom(48)
        assert len(request) == 48 and request[0] == 0x1B
        server.sendto(ntp_reply(unix), addr)
        server.close()

    threading.Thread(target=reply, daemon=True).start()
    return server.getsockname()[1]


def test_fetch_unix_from_server():
    port = fake_ntp_server(1_790_000_000)

    assert asyncio.run(clock.fetch_unix("127.0.0.1", port, timeout_ms=2000)) == 1_790_000_000


def test_fetch_unix_times_out_to_none():
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]

    assert asyncio.run(clock.fetch_unix("127.0.0.1", port, timeout_ms=300)) is None
    probe.close()
