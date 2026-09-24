import asyncio
import time

from machine import Pin
from esp32 import RMT

POLL_MS = 5
DONE_TIMEOUT_MS = 1000

rmt = RMT(0, pin=Pin(23), clock_div=80)

async def send_pulses(pulses, repeat=8):
    for _ in range(repeat):
        rmt.write_pulses(pulses, 1)
        started = time.ticks_ms()
        while not rmt.wait_done() and time.ticks_diff(time.ticks_ms(), started) < DONE_TIMEOUT_MS:
            await asyncio.sleep_ms(POLL_MS)
