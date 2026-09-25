import hashlib
import os
import struct
import zlib
from dataclasses import dataclass

from protocol import FRAME_SIZE

MAGIC = b"RFCL"
VERSION = 1
NAME_MAX = 32
ID_LENGTH = 12
# 1 KB window keeps the device-side DeflateIO buffer small; mirrored in device/lib/clipfmt.py.
ZLIB_WBITS = 10
DURATION_MAX_MS = 0xFFFF


@dataclass
class Clip:
    id: str
    name: str
    frames: int
    data: bytes


def sanitize_name(name):
    base = os.path.basename(name)
    return "".join(ch if " " <= ch <= "~" else "_" for ch in base)[:NAME_MAX]


class ClipBuilder:
    """Header: MAGIC, version u8, frame count u32, name length u8, name; then zlib records (u16 ms + frame)."""

    def __init__(self, name):
        self.name = sanitize_name(name)
        self.frames = 0
        self._hash = hashlib.sha1()
        self._compressor = zlib.compressobj(9, zlib.DEFLATED, ZLIB_WBITS)
        self._chunks = []
        self.size = 0

    def add(self, frame, duration_s):
        if len(frame) != FRAME_SIZE:
            raise ValueError("frame must be %d bytes, got %d" % (FRAME_SIZE, len(frame)))
        duration_ms = min(max(round(duration_s * 1000), 1), DURATION_MAX_MS)
        record = struct.pack(">H", duration_ms) + bytes(frame)
        self._hash.update(record)
        chunk = self._compressor.compress(record)
        self._chunks.append(chunk)
        self.size += len(chunk)
        self.frames += 1

    def finish(self):
        self._chunks.append(self._compressor.flush())
        name = self.name.encode("ascii")
        header = MAGIC + struct.pack(">BIB", VERSION, self.frames, len(name)) + name
        data = header + b"".join(self._chunks)
        return Clip(self._hash.hexdigest()[:ID_LENGTH], self.name, self.frames, data)
