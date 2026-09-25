import io
import os
import sys
import zlib

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "host"))

import clip
import clipfmt

FRAME = 1024


class ZlibReader:
    """CPython stand-in for deflate.DeflateIO; short reads on purpose to exercise refill loops."""

    def __init__(self, f, max_read=300):
        self._f = f
        self._d = zlib.decompressobj()
        self._pending = b""
        self._max_read = max_read

    def readinto(self, buf):
        while len(self._pending) < len(buf):
            chunk = self._f.read(64)
            if not chunk:
                self._pending += self._d.flush()
                break
            self._pending += self._d.decompress(chunk)
        count = min(len(buf), len(self._pending), self._max_read)
        buf[:count] = self._pending[:count]
        self._pending = self._pending[count:]
        return count


def make_clip(durations, name="cat.gif"):
    builder = clip.ClipBuilder(name)
    frames = [bytes([i]) * FRAME for i in range(len(durations))]
    for frame, duration in zip(frames, durations):
        builder.add(frame, duration)
    return builder.finish(), frames


def open_clip(data):
    f = io.BytesIO(data)
    frames, name = clipfmt.read_header(f)
    return frames, name, ZlibReader(f)


def test_header_roundtrip():
    built, _ = make_clip([0.1, 0.2])

    frames, name, _ = open_clip(built.data)

    assert (frames, name) == (2, "cat.gif")


def test_records_decode_in_order():
    built, frames = make_clip([0.05, 0.1, 0.25])
    _, _, decoder = open_clip(built.data)
    duration_buf = bytearray(2)
    frame_buf = bytearray(FRAME)

    decoded = []
    while True:
        duration = clipfmt.read_record(decoder, duration_buf, frame_buf)
        if duration is None:
            break
        decoded.append((duration, bytes(frame_buf)))

    assert decoded == [(50, frames[0]), (100, frames[1]), (250, frames[2])]


def test_bad_magic_raises():
    built, _ = make_clip([0.1])

    with pytest.raises(ValueError):
        clipfmt.read_header(io.BytesIO(b"XXXX" + built.data[4:]))


def test_unknown_version_raises():
    built, _ = make_clip([0.1])
    data = bytearray(built.data)
    data[4] = 99

    with pytest.raises(ValueError):
        clipfmt.read_header(io.BytesIO(bytes(data)))


def test_truncated_record_raises():
    built, _ = make_clip([0.1, 0.1, 0.1])
    header_length = 10 + len("cat.gif")
    records = zlib.decompress(built.data[header_length:])
    truncated = built.data[:header_length] + zlib.compress(records[:-100], 9)
    _, _, decoder = open_clip(truncated)
    duration_buf = bytearray(2)
    frame_buf = bytearray(FRAME)

    with pytest.raises(ValueError):
        while clipfmt.read_record(decoder, duration_buf, frame_buf) is not None:
            pass
