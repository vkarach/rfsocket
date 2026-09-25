def text_origin(text, glyphs, gap, panel_width, panel_height, glyph_height, minute, shift):
    """Top-left of the first cell so the visible ink is centered, then offset by the per-minute burn-in shift."""
    cells = sum(glyphs[ch][0] for ch in text) + gap * (len(text) - 1)
    ink_left = glyphs[text[0]][1]
    ink_right = cells - glyphs[text[-1]][0] + glyphs[text[-1]][2]
    span = 2 * shift + 1
    x = (panel_width - (ink_right - ink_left + 1)) // 2 - ink_left + minute % span - shift
    y = (panel_height - glyph_height) // 2 + minute // span % span - shift
    return x, y
