"""Behaviour: the iTerm2 helper sets the profile font and window transparency on
every profile, idempotently, touching only those two keys. Pure logic."""
import copy

import ts_iterm2


def plist_with(font, transparency, name="Default"):
    return {
        "New Bookmarks": [
            {"Name": name, "Guid": "abc", "Normal Font": font, "Transparency": transparency},
        ],
        "Default Bookmark Guid": "abc",
    }


def test_sets_font_and_transparency_when_different():
    plist = plist_with("OldFont 12", 0.0)
    new, changed = ts_iterm2.apply_settings(plist, font="MesloLGSNF-Regular 16", transparency=0.2)
    prof = new["New Bookmarks"][0]
    assert prof["Normal Font"] == "MesloLGSNF-Regular 16"
    assert prof["Transparency"] == 0.2
    assert changed is True


def test_touches_only_font_and_transparency_keys():
    plist = plist_with("OldFont 12", 0.0)
    before_keys = set(plist["New Bookmarks"][0].keys())
    new, _ = ts_iterm2.apply_settings(plist, font="X 16", transparency=0.2)
    assert set(new["New Bookmarks"][0].keys()) == before_keys
    # Unrelated keys are preserved untouched.
    assert new["New Bookmarks"][0]["Guid"] == "abc"
    assert new["Default Bookmark Guid"] == "abc"


def test_idempotent_when_already_set():
    plist = plist_with("MesloLGSNF-Regular 16", 0.2)
    new, changed = ts_iterm2.apply_settings(plist, font="MesloLGSNF-Regular 16", transparency=0.2)
    assert changed is False
    assert new == plist


def test_applies_to_all_profiles():
    plist = {"New Bookmarks": [
        {"Name": "A", "Normal Font": "x 1", "Transparency": 0.0},
        {"Name": "B", "Normal Font": "y 2", "Transparency": 0.5},
    ]}
    new, changed = ts_iterm2.apply_settings(plist, font="F 16", transparency=0.2)
    assert changed is True
    assert all(p["Normal Font"] == "F 16" and p["Transparency"] == 0.2 for p in new["New Bookmarks"])


def test_no_profiles_is_a_safe_noop():
    new, changed = ts_iterm2.apply_settings({"Other": 1}, font="F 16", transparency=0.2)
    assert changed is False
    assert new == {"Other": 1}
