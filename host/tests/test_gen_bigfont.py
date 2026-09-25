import os

import numpy as np

import gen_bigfont
from protocol import HEIGHT, WIDTH

CHARS = "0123456789:"


def unpack(font, ch):
    width, _, _, data = font.glyphs[ch]
    rows = np.frombuffer(data, dtype=np.uint8).reshape(font.height, -1)
    return np.unpackbits(rows, axis=1)[:, :width].astype(bool)


def test_glyphs_share_height_and_digits_share_width():
    font = gen_bigfont.render()

    assert set(font.glyphs) == set(CHARS)
    assert len({font.glyphs[d][0] for d in "0123456789"}) == 1
    for width, _, _, data in font.glyphs.values():
        assert len(data) == (width + 7) // 8 * font.height


def test_clock_text_fits_panel_with_shift_margin():
    font = gen_bigfont.render()
    digit = font.glyphs["0"][0]
    colon = font.glyphs[":"][0]

    total = 4 * digit + colon + 4 * gen_bigfont.GAP
    assert total <= WIDTH - gen_bigfont.SHIFT_MARGIN
    assert font.height <= HEIGHT - gen_bigfont.SHIFT_MARGIN
    assert font.height >= 40


def test_default_font_is_vendored_with_license():
    assert os.path.isfile(gen_bigfont.DEFAULT_FONT)
    assert os.path.isfile(os.path.join(os.path.dirname(gen_bigfont.DEFAULT_FONT), "OFL.txt"))


def test_ink_bounds_match_bitmap():
    font = gen_bigfont.render()

    for ch in CHARS:
        _, ink_left, ink_right, _ = font.glyphs[ch]
        columns = np.where(unpack(font, ch).any(axis=0))[0]
        assert (ink_left, ink_right) == (columns.min(), columns.max())


def test_module_source_roundtrips():
    font = gen_bigfont.render()
    namespace = {}

    exec(gen_bigfont.module_source(font), namespace)

    assert namespace["HEIGHT"] == font.height
    assert namespace["GAP"] == gen_bigfont.GAP
    assert namespace["GLYPHS"] == font.glyphs
