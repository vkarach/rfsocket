import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import convert
from protocol import HEIGHT, WIDTH

OUT = os.path.join(os.path.dirname(__file__), "..", "android", "app", "src", "test",
                    "resources", "convert_fixtures")


def gradient_image():
    row = np.linspace(0, 255, WIDTH, dtype=np.uint8)
    gray = np.tile(row, (HEIGHT, 1))
    return Image.fromarray(gray, mode="L")


def checkerboard_bits():
    bits = np.zeros((HEIGHT, WIDTH), dtype=bool)
    bits[::2, ::2] = True
    bits[1::2, 1::2] = True
    return bits


def write(name, data):
    with open(os.path.join(OUT, name), "wb") as f:
        f.write(data)


def main():
    os.makedirs(OUT, exist_ok=True)
    img = gradient_image()
    write("gradient_input.bin", np.asarray(img, dtype=np.uint8).tobytes())
    for method in ("bayer", "none"):
        bits = convert.dither(img, method)
        write("dither_%s.bin" % method, convert.pack_vlsb(bits))
        write("dither_%s_inverted.bin" % method, convert.pack_vlsb(~bits))
    write("checkerboard_packed.bin", convert.pack_vlsb(checkerboard_bits()))


if __name__ == "__main__":
    main()
