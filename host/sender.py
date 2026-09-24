import socket
import time
from dataclasses import dataclass

from protocol import frame_message

_END = object()


class SenderError(Exception):
    pass


@dataclass
class PlayStats:
    sent: int = 0
    dropped: int = 0


def connect(host, port, timeout=5.0):
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
    except OSError as exc:
        raise SenderError("cannot connect to %s:%d: %s" % (host, port, exc))
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return sock


def play(sock, frames, clock=time.monotonic, sleep=time.sleep):
    stats = PlayStats()
    frames = iter(frames)
    current = next(frames, _END)
    start = clock()
    due = start
    while current is not _END:
        frame, duration = current
        upcoming = next(frames, _END)
        now = clock()
        if upcoming is not _END and now > due + duration:
            stats.dropped += 1
        else:
            if due > now:
                sleep(due - now)
            try:
                sock.sendall(frame_message(frame))
            except OSError as exc:
                raise SenderError("connection lost: %s" % exc)
            stats.sent += 1
        due += duration
        current = upcoming
    return stats
