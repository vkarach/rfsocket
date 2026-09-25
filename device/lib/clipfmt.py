import struct

# Mirrors host/clip.py.
MAGIC = b"RFCL"
VERSION = 1
FRAME_SIZE = 1024
RECORD_SIZE = 2 + FRAME_SIZE


def read_header(f):
    if f.read(4) != MAGIC:
        raise ValueError("not a clip file")
    fixed = f.read(6)
    if len(fixed) != 6:
        raise ValueError("truncated clip header")
    version, frames, name_length = struct.unpack(">BIB", fixed)
    if version != VERSION:
        raise ValueError("unsupported clip version %d" % version)
    return frames, f.read(name_length).decode()


def _fill(decoder, buf):
    view = memoryview(buf)
    got = 0
    while got < len(buf):
        count = decoder.readinto(view[got:])
        if not count:
            break
        got += count
    return got


def read_record(decoder, duration_buf, frame_buf):
    got = _fill(decoder, duration_buf)
    if got == 0:
        return None
    if got != len(duration_buf) or _fill(decoder, frame_buf) != len(frame_buf):
        raise ValueError("truncated clip record")
    return duration_buf[0] << 8 | duration_buf[1]
