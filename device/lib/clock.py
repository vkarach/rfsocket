import asyncio
import socket
import struct

NTP_UNIX_DELTA = 2208988800
NTP_PORT = 123
SECONDS_PER_DAY = 86400
DST_SHIFT_S = 3600
# EU clocks change at 01:00 UTC on the last Sunday of March and October.
DST_CHANGE_UTC_S = 3600


def days_from_civil(y, m, d):
    y -= m <= 2
    era = y // 400
    yoe = y - era * 400
    doy = (153 * (m - 3 if m > 2 else m + 9) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def civil_from_days(days):
    days += 719468
    era = days // 146097
    doe = days - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + 3 if mp < 10 else mp - 9
    return yoe + era * 400 + (m <= 2), m, d


def _last_sunday(y, m):
    last = days_from_civil(y, m, 31)
    return last - (last - 3) % 7


def eu_dst(unix):
    y = civil_from_days(unix // SECONDS_PER_DAY)[0]
    start = _last_sunday(y, 3) * SECONDS_PER_DAY + DST_CHANGE_UTC_S
    end = _last_sunday(y, 10) * SECONDS_PER_DAY + DST_CHANGE_UTC_S
    return start <= unix < end


def local_hm(unix, offset_s, dst):
    if dst and eu_dst(unix):
        offset_s += DST_SHIFT_S
    seconds = (unix + offset_s) % SECONDS_PER_DAY
    return seconds // 3600, seconds % 3600 // 60


def unix_from_ntp(packet):
    if len(packet) < 48:
        raise ValueError("short NTP packet")
    return struct.unpack("!I", packet[40:44])[0] - NTP_UNIX_DELTA


class Clock:
    def __init__(self, diff=lambda a, b: a - b):
        self._diff = diff
        self._base = None
        self._base_ticks = 0

    def set(self, unix, ticks_ms):
        self._base = unix
        self._base_ticks = ticks_ms

    def unix(self, ticks_ms):
        if self._base is None:
            return None
        return self._base + self._diff(ticks_ms, self._base_ticks) // 1000


async def fetch_unix(host, port=NTP_PORT, timeout_ms=2000, poll_ms=50):
    try:
        addr = socket.getaddrinfo(host, port)[0][-1]
    except OSError:
        return None
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setblocking(False)
        request = bytearray(48)
        request[0] = 0x1B
        sock.sendto(request, addr)
        for _ in range(timeout_ms // poll_ms):
            try:
                return unix_from_ntp(sock.recv(48))
            except OSError:
                pass
            except ValueError:
                return None
            await asyncio.sleep(poll_ms / 1000)
        return None
    finally:
        sock.close()
