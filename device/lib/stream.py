import asyncio

import display

MSG_FRAME = 0x01

_frame = bytearray(display.FRAME_SIZE)
_frame_view = memoryview(_frame)
_header = bytearray(1)
_header_view = memoryview(_header)
_current = None


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


async def _serve_client(reader, writer):
    global _current
    # Cancel instead of closing the old socket: cancel() unhooks the task from the IO poller.
    if _current is not None:
        _current.cancel()
    task = asyncio.current_task()
    _current = task
    display.begin_stream()
    try:
        while await _read_exact(reader, _header_view):
            if _header[0] != MSG_FRAME:
                break
            if not await _read_exact(reader, _frame_view):
                break
            display.show_frame(_frame)
    except Exception as exc:
        print("stream failed:", exc)
    finally:
        if _current is task:
            _current = None
            display.end_stream()
        await writer.wait_closed()


async def serve(port):
    return await asyncio.start_server(_serve_client, "0.0.0.0", port)
