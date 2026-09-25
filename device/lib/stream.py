import asyncio
import struct

import clips
import display
import rf

MSG_FRAME = 0x01
MSG_STORE = 0x02
STORE_CHUNK = 4096

_frame = bytearray(display.FRAME_SIZE)
_frame_view = memoryview(_frame)
_header = bytearray(1)
_header_view = memoryview(_header)
_store_fixed = bytearray(14)
_store_sizes = bytearray(8)
_chunk = bytearray(STORE_CHUNK)
_chunk_view = memoryview(_chunk)
_current = None
_store = None


async def _read_exact(reader, view):
    got = 0
    while got < len(view):
        count = await reader.readinto(view[got:])
        if count is None:
            continue
        if count == 0:
            return False
        got += count
    return True


def streaming():
    return _current is not None


async def _reply(writer, status):
    writer.write(bytes((status,)))
    await writer.drain()


async def _serve_frames(reader):
    global _current
    # Cancel instead of closing the old socket: cancel() unhooks the task from the IO poller.
    if _current is not None:
        _current.cancel()
    task = asyncio.current_task()
    _current = task
    display.begin_stream()
    try:
        while True:
            if not await _read_exact(reader, _frame_view):
                break
            display.show_frame(_frame)
            if not await _read_exact(reader, _header_view) or _header[0] != MSG_FRAME:
                break
    finally:
        if _current is task:
            _current = None
            display.end_stream()


async def _serve_store(reader, writer):
    if not await _read_exact(reader, memoryview(_store_fixed)):
        return
    clip_id, keep, name_length = struct.unpack(">12sBB", _store_fixed)
    name = bytearray(name_length)
    if not await _read_exact(reader, memoryview(name)) or not await _read_exact(reader, memoryview(_store_sizes)):
        return
    frames, size = struct.unpack(">II", _store_sizes)
    clip_id = clip_id.decode()

    if streaming():
        await _reply(writer, clips.STORE_FAILED)
        return
    async with rf.lock:
        status = _store.check(clip_id, size, bool(keep))
    await _reply(writer, status)
    if status != clips.STORE_ACCEPT:
        return

    async with rf.lock:
        clip_writer = _store.open_writer(clip_id, name.decode(), frames, size, bool(keep))
    remaining = size
    try:
        while remaining:
            count = min(remaining, STORE_CHUNK)
            # A live stream must never share the loop with flash writes.
            if streaming() or not await _read_exact(reader, _chunk_view[:count]):
                raise OSError("upload interrupted")
            async with rf.lock:
                clip_writer.write(_chunk_view[:count])
            remaining -= count
    except BaseException:
        async with rf.lock:
            clip_writer.abort()
        raise
    async with rf.lock:
        status = clip_writer.commit()
    await _reply(writer, status)


async def _serve_client(reader, writer):
    try:
        if not await _read_exact(reader, _header_view):
            return
        if _header[0] == MSG_FRAME:
            await _serve_frames(reader)
        elif _header[0] == MSG_STORE:
            await _serve_store(reader, writer)
    except Exception as exc:
        print("stream failed:", exc)
    finally:
        await writer.wait_closed()


async def serve(port, store):
    global _store
    _store = store
    return await asyncio.start_server(_serve_client, "0.0.0.0", port)
