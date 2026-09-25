import framebuf
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C

import bigfont
import idle
import layout

I2C_ID = 0
SCL_PIN = 22
SDA_PIN = 21
I2C_FREQ = 1000000
WIDTH = 128
HEIGHT = 64
FRAME_SIZE = WIDTH * HEIGHT // 8
# Must match SHIFT_MARGIN in host/gen_bigfont.py: the big clock moves +-2 px per minute.
CLOCK_SHIFT = 2

_oled = SSD1306_I2C(WIDTH, HEIGHT, I2C(I2C_ID, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN), freq=I2C_FREQ))
_glyph_buffers = {ch: framebuf.FrameBuffer(bytearray(glyph[3]), glyph[0], bigfont.HEIGHT, framebuf.MONO_HLSB)
                  for ch, glyph in bigfont.GLYPHS.items()}
_status = None
_time = None
_screen = idle.STATUS
_streaming = False
_powered = True


def show(ip, states):
    global _status
    _status = (ip, states)
    _redraw()


def set_time(hm):
    global _time
    if hm != _time:
        _time = hm
        _redraw()


def set_screen(screen):
    global _screen
    if screen != _screen:
        _screen = screen
        _redraw()


def streaming():
    return _streaming


def begin_stream():
    global _streaming
    _streaming = True
    _power(True)


def end_stream():
    global _streaming
    _streaming = False
    _redraw()


def show_frame(frame):
    _oled.buffer[:] = frame
    _oled.show()


def _power(on):
    global _powered
    if on != _powered:
        _powered = on
        if on:
            _oled.poweron()
        else:
            _oled.poweroff()


def _redraw():
    if _streaming:
        return
    if _screen == idle.OFF:
        _power(False)
        return
    _power(True)
    if _screen == idle.CLOCK and _time is not None:
        _draw_clock(*_time)
    elif _status is not None:
        _draw_status(*_status)


def _draw_status(ip, states):
    _oled.fill(0)
    _oled.text("rfsocket", 0, 0)
    clock_text = "%02d:%02d" % _time if _time is not None else "--:--"
    _oled.text(clock_text, WIDTH - 8 * len(clock_text), 0)

    row = 18
    for name in sorted(states):
        _oled.text("%s: %s" % (name.upper(), "on" if states[name] else "off"), 0, row)
        row += 12

    _oled.text(ip, 0, 56)
    _oled.show()


def _draw_clock(hour, minute):
    text = "%02d:%02d" % (hour, minute)
    x, y = layout.text_origin(text, bigfont.GLYPHS, bigfont.GAP, WIDTH, HEIGHT, bigfont.HEIGHT,
                              minute, CLOCK_SHIFT)

    _oled.fill(0)
    for ch in text:
        _oled.blit(_glyph_buffers[ch], x, y)
        x += bigfont.GLYPHS[ch][0] + bigfont.GAP
    _oled.show()
