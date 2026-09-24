import numpy as np
from PIL import Image, ImageOps

from protocol import HEIGHT, WIDTH

SCALE_MODES = ("fit", "fill")
DITHER_METHODS = ("fs", "bayer", "none")

_BAYER_2 = np.array([[0, 2], [3, 1]])


def _bayer(n):
    matrix = _BAYER_2
    while matrix.shape[0] < n:
        matrix = np.block([[4 * matrix, 4 * matrix + 2], [4 * matrix + 3, 4 * matrix + 1]])
    return matrix


_BAYER_8 = _bayer(8)
_BAYER_THRESHOLDS = np.tile((_BAYER_8 + 0.5) * 255 / 64, (HEIGHT // 8, WIDTH // 8))
_BIT_WEIGHTS = (1 << np.arange(8, dtype=np.uint16))[None, :, None]


def _flatten(img):
    rgba = img.convert("RGBA")
    return Image.alpha_composite(Image.new("RGBA", rgba.size, (0, 0, 0, 255)), rgba).convert("L")


def scale(img, mode):
    gray = _flatten(img)
    if mode == "fit":
        return ImageOps.pad(gray, (WIDTH, HEIGHT), Image.Resampling.LANCZOS, color=0)
    if mode == "fill":
        return ImageOps.fit(gray, (WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    raise ValueError("unknown scale mode: %s" % mode)


def dither(img, method):
    if method == "fs":
        return np.array(img.convert("1", dither=Image.Dither.FLOYDSTEINBERG), dtype=bool)
    pixels = np.asarray(img, dtype=np.float32)
    if method == "bayer":
        return pixels > _BAYER_THRESHOLDS
    if method == "none":
        return pixels >= 128
    raise ValueError("unknown dither method: %s" % method)


def pack_vlsb(bits):
    if bits.shape != (HEIGHT, WIDTH):
        raise ValueError("bits must have shape %s, got %s" % ((HEIGHT, WIDTH), bits.shape))
    pages = bits.reshape(HEIGHT // 8, 8, WIDTH).astype(np.uint16)
    return (pages * _BIT_WEIGHTS).sum(axis=1).astype(np.uint8).tobytes()


def to_frame(img, scale_mode, dither_method, invert):
    bits = dither(scale(img, scale_mode), dither_method)
    if invert:
        bits = ~bits
    return pack_vlsb(bits)
