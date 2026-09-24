from machine import Pin
from esp32 import RMT

rmt = RMT(0, pin=Pin(23), clock_div=80)

def send_pulses(pulses, repeat=8):
    for _ in range(repeat):
        rmt.write_pulses(pulses, 1)
        rmt.wait_done(timeout=1000)
