import socket
import struct
import time
from dataclasses import dataclass

from protocol import MSG_STORE, STORE_ACCEPT, frame_message

_END = object()
UPLOAD_CHUNK = 4096


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


def hold(sock, poll=0.5):
    # Short polls keep Ctrl+C responsive on Windows, where a blocking recv ignores it.
    sock.settimeout(poll)
    while True:
        try:
            if not sock.recv(1):
                return
        except socket.timeout:
            continue
        except OSError:
            return


def _recv_status(sock):
    status = sock.recv(1)
    if not status:
        raise SenderError("connection lost: device closed the connection")
    return status[0]


def store(host, port, clip, keep, timeout=10.0):
    """Upload a clip over STORE and return the device's final status byte."""
    sock = connect(host, port, timeout)
    try:
        name = clip.name.encode("ascii")
        sock.sendall(struct.pack(">B12sBB", MSG_STORE, clip.id.encode("ascii"), int(keep), len(name)) + name
                     + struct.pack(">II", clip.frames, len(clip.data)))
        status = _recv_status(sock)
        if status != STORE_ACCEPT:
            return status
        for offset in range(0, len(clip.data), UPLOAD_CHUNK):
            sock.sendall(clip.data[offset:offset + UPLOAD_CHUNK])
        return _recv_status(sock)
    except OSError as exc:
        raise SenderError("connection lost: %s" % exc)
    finally:
        sock.close()


def play(sock, frames, clock=time.monotonic, sleep=time.sleep, stats=None):
    stats = stats if stats is not None else PlayStats()
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
