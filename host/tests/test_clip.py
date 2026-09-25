import os
import random
import struct
import zlib

import clip
from protocol import FRAME_SIZE


def frames(count, seed=0):
    rng = random.Random(seed)
    return [bytes(rng.getrandbits(8) for _ in range(FRAME_SIZE)) for _ in range(count)]


def build(pairs, name="anim.gif"):
    builder = clip.ClipBuilder(name)
    for frame, duration in pairs:
        builder.add(frame, duration)
    return builder.finish()


def split(data):
    assert data[:4] == clip.MAGIC
    version, count, name_len = struct.unpack(">BIB", data[4:10])
    name = data[10:10 + name_len].decode("ascii")
    return version, count, name, data[10 + name_len:]


def test_header_and_records_roundtrip():
    pairs = list(zip(frames(3), [0.05, 0.1, 0.2]))
    result = build(pairs)

    version, count, name, stream = split(result.data)
    records = zlib.decompress(stream)

    assert (version, count, name) == (clip.VERSION, 3, "anim.gif")
    assert result.frames == 3
    expected = b"".join(struct.pack(">H", round(d * 1000)) + f for f, d in pairs)
    assert records == expected


def test_stream_declares_one_kb_window():
    stream = split(build(zip(frames(1), [0.1])).data)[3]

    assert stream[0] == 0x28


def test_id_is_stable_and_content_sensitive():
    base = list(zip(frames(2), [0.1, 0.1]))
    changed_frame = [(base[0][0][:-1] + b"\x00", 0.1), base[1]]
    changed_duration = [base[0], (base[1][0], 0.2)]

    first = build(base).id
    assert first == build(base, name="other.gif").id
    assert len(first) == 12 and int(first, 16) >= 0
    assert build(changed_frame).id != first
    assert build(changed_duration).id != first


def test_size_grows_as_frames_are_added():
    builder = clip.ClipBuilder("x")
    sizes = []
    for frame in frames(40):
        builder.add(frame, 0.1)
        sizes.append(builder.size)

    assert sizes[-1] > sizes[0]
    assert sizes == sorted(sizes)


def test_name_is_ascii_and_truncated():
    name = "kot-" + "ëž" * 3 + "a" * 50
    stored = build(zip(frames(1), [0.1]), name=name).name

    assert stored.isascii()
    assert len(stored) <= clip.NAME_MAX
    assert stored.startswith("kot-")


def test_duration_is_clamped_to_u16_ms():
    stream = split(build(zip(frames(2), [0, 100])).data)[3]
    records = zlib.decompress(stream)

    assert struct.unpack(">H", records[:2])[0] == 1
    assert struct.unpack(">H", records[FRAME_SIZE + 2:FRAME_SIZE + 4])[0] == 65535


def test_name_uses_basename_only():
    assert build(zip(frames(1), [0.1]), name=os.path.join("a", "b", "cat.gif")).name == "cat.gif"
