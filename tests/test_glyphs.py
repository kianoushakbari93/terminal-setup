"""Behaviour: the glyphs filter resolves powerline/Nerd glyphs by name to their
real codepoints. The source uses \\uXXXX escapes so editors/tools never strip the
glyphs to empty - the whole point of routing glyphs through this filter."""
import pytest

import glyphs


def test_powerline_half_circles_resolve_to_real_codepoints():
    assert glyphs.glyph("right_half_circle") == ""
    assert glyphs.glyph("left_half_circle") == ""
    assert glyphs.glyph("right_half_circle_thin") == ""
    assert glyphs.glyph("left_half_circle_thin") == ""


def test_resolved_glyph_is_a_single_nonempty_char():
    g = glyphs.glyph("left_half_circle")
    assert g and len(g) == 1
    assert ord(g) == 0xE0B6


def test_unknown_glyph_raises_clear_error():
    with pytest.raises(glyphs.UnknownGlyph) as exc:
        glyphs.glyph("definitely_not_a_glyph")
    assert "definitely_not_a_glyph" in str(exc.value)


def test_filter_module_exposes_glyph_filter():
    fm = glyphs.FilterModule()
    assert "glyph" in fm.filters()
    assert fm.filters()["glyph"]("right_half_circle") == ""
