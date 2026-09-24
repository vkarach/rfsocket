from machine import Pin, I2C
from ssd1306 import SSD1306_I2C

I2C_ID = 0
SCL_PIN = 22
SDA_PIN = 21
WIDTH = 128
HEIGHT = 64

_oled = SSD1306_I2C(WIDTH, HEIGHT, I2C(I2C_ID, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN)))


def show(ip, states):
    _oled.fill(0)
    _oled.text("rfsocket", 0, 0)

    row = 18
    for name in sorted(states):
        _oled.text("%s: %s" % (name.upper(), "on" if states[name] else "off"), 0, row)
        row += 12

    _oled.text(ip, 0, 56)
    _oled.show()
