import asyncio
import deflate

import clipfmt
import display

_frame = bytearray(clipfmt.FRAME_SIZE)
_duration = bytearray(2)
_store = None
_task = None


def init(store):
    global _store
    _store = store


def active():
    return _task is not None


def play(clip_id, once):
    global _task
    if _store.get(clip_id) is None:
        return False
    stop()
    # Bookkeeping is synchronous: a task cancelled before its first run never reaches its finally.
    _task = asyncio.create_task(_run(clip_id, once))
    _store.playing = clip_id
    return True


def stop():
    global _task
    if _task is not None:
        _task.cancel()
        _task = None
        _store.playing = None


async def _play_pass(clip_id):
    shown = 0
    with open(_store.path(clip_id), "rb") as f:
        clipfmt.read_header(f)
        decoder = deflate.DeflateIO(f, deflate.ZLIB)
        while True:
            ms = clipfmt.read_record(decoder, _duration, _frame)
            if ms is None:
                return shown
            display.show_frame(_frame)
            shown += 1
            await asyncio.sleep_ms(ms)


async def _run(clip_id, once):
    global _task
    task = asyncio.current_task()
    display.begin_stream(task)
    try:
        # An empty clip ends the loop instead of spinning without ever yielding.
        while await _play_pass(clip_id) and not once:
            pass
    except (OSError, ValueError) as exc:
        print("playback failed:", clip_id, exc)
    finally:
        if _task is task:
            _task = None
            _store.playing = None
        display.end_stream(task)
