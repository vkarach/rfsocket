import pytest

import layout

# Cell width, ink left, ink right; '1' is narrow inside its cell like real fonts.
GLYPHS = {
    "0": (25, 1, 23, None), "1": (25, 5, 18, None), "2": (25, 1, 24, None),
    "4": (25, 0, 24, None), "7": (25, 2, 23, None), ":": (12, 2, 10, None),
}
GAP = 2


def ink_margins(text, minute=0, shift=0):
    x, _ = layout.text_origin(text, GLYPHS, GAP, 128, 64, 44, minute, shift)
    first_left = x + GLYPHS[text[0]][1]
    last_cell = x + sum(GLYPHS[c][0] for c in text[:-1]) + GAP * (len(text) - 1)
    last_right = last_cell + GLYPHS[text[-1]][2]
    return first_left, 127 - last_right


@pytest.mark.parametrize("text", ["12:02", "10:00", "21:47", "11:11"])
def test_ink_is_centered_without_shift(text):
    left, right = ink_margins(text)

    assert abs(left - right) <= 1


def test_vertical_center_without_shift():
    _, y = layout.text_origin("12:02", GLYPHS, GAP, 128, 64, 44, 0, 0)

    assert y == 10


def test_shift_stays_within_range_and_moves_each_minute():
    base_x, base_y = layout.text_origin("12:02", GLYPHS, GAP, 128, 64, 44, 0, 0)
    offsets = {(x - base_x, y - base_y)
               for x, y in (layout.text_origin("12:02", GLYPHS, GAP, 128, 64, 44, m, 2) for m in range(25))}

    assert len(offsets) == 25
    assert all(abs(dx) <= 2 and abs(dy) <= 2 for dx, dy in offsets)
