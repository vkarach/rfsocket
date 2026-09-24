import numpy as np
import pytest
from PIL import Image

import convert
from protocol import FRAME_SIZE, HEIGHT, WIDTH


def blank_bits():
    return np.zeros((HEIGHT, WIDTH), dtype=bool)


def test_pack_all_off_is_zero():
    assert convert.pack_vlsb(blank_bits()) == bytes(FRAME_SIZE)


@pytest.mark.parametrize("x, y, index, value", [
    (0, 0, 0, 0x01),
    (5, 13, 128 + 5, 1 << 5),
    (127, 63, 1023, 0x80),
])
def test_pack_single_pixel_lands_in_vlsb_bit(x, y, index, value):
    bits = blank_bits()
    bits[y, x] = True

    packed = convert.pack_vlsb(bits)

    assert packed[index] == value
    assert sum(1 for b in packed if b) == 1


def test_pack_rejects_wrong_shape():
    with pytest.raises(ValueError):
        convert.pack_vlsb(np.zeros((WIDTH, HEIGHT), dtype=bool))


@pytest.mark.parametrize("size", [(10, 10), (1000, 50), (50, 1000)])
@pytest.mark.parametrize("mode", ["fit", "fill"])
def test_scale_output_is_panel_sized_grayscale(size, mode):
    out = convert.scale(Image.new("RGB", size, (200, 30, 90)), mode)

    assert out.size == (WIDTH, HEIGHT)
    assert out.mode == "L"


def test_fit_letterboxes_with_black():
    out = convert.scale(Image.new("L", (64, 64), 255), "fit")

    assert out.getpixel((0, 32)) == 0
    assert out.getpixel((64, 32)) == 255


def test_fill_covers_whole_panel():
    out = convert.scale(Image.new("L", (64, 64), 255), "fill")

    assert out.getpixel((0, 0)) == 255
    assert out.getpixel((127, 63)) == 255


def test_transparent_rgba_becomes_black():
    out = convert.scale(Image.new("RGBA", (40, 20), (255, 255, 255, 0)), "fill")

    assert out.getextrema() == (0, 0)


def test_transparent_palette_index_becomes_black():
    img = Image.new("P", (40, 20), 1)
    img.putpalette([0, 0, 0, 255, 255, 255])
    img.info["transparency"] = 1

    out = convert.scale(img, "fill")

    assert out.getextrema() == (0, 0)


@pytest.mark.parametrize("method", ["fs", "bayer", "none"])
def test_dither_uniform_black_and_white(method):
    black = convert.dither(Image.new("L", (WIDTH, HEIGHT), 0), method)
    white = convert.dither(Image.new("L", (WIDTH, HEIGHT), 255), method)

    assert black.shape == (HEIGHT, WIDTH) and black.dtype == bool
    assert not black.any()
    assert white.all()


def test_bayer_mid_gray_is_stable_and_half_lit():
    gray = Image.new("L", (WIDTH, HEIGHT), 128)

    first = convert.dither(gray, "bayer")
    second = convert.dither(gray, "bayer")

    assert np.array_equal(first, second)
    assert 0.4 <= first.mean() <= 0.6


def test_to_frame_invert_lights_black_image():
    frame = convert.to_frame(Image.new("L", (10, 10), 0), "fill", "none", True)

    assert frame == b"\xff" * FRAME_SIZE
