"""Behaviour: the fonts layer resolves logical Nerd Font names to install specs,
builds correct commands/URLs, probes discoverability, and orchestrates install
with injected IO (so network/disk effects stay testable). Pure logic."""
import pytest

import ts_fonts as fonts


def test_catalog_resolves_the_three_nerd_fonts():
    meslo = fonts.resolve_font("meslo")
    jb = fonts.resolve_font("jetbrains")
    fc = fonts.resolve_font("firacode")

    assert meslo.cask == "font-meslo-lg-nerd-font"
    assert "Meslo" in meslo.family
    assert meslo.archive == "Meslo"

    assert jb.cask == "font-jetbrains-mono-nerd-font"
    assert "JetBrainsMono" in jb.family
    assert jb.archive == "JetBrainsMono"

    assert fc.cask == "font-fira-code-nerd-font"
    assert "FiraCode" in fc.family
    assert fc.archive == "FiraCode"


def test_unknown_font_raises_clear_error():
    with pytest.raises(fonts.UnknownFont) as exc:
        fonts.resolve_font("comic-sans")
    assert "comic-sans" in str(exc.value)


def test_cask_commands():
    assert fonts.cask_install_cmd("font-meslo-lg-nerd-font") == [
        "brew", "install", "--cask", "font-meslo-lg-nerd-font"
    ]
    assert fonts.cask_is_installed_cmd("font-meslo-lg-nerd-font") == [
        "brew", "list", "--cask", "font-meslo-lg-nerd-font"
    ]


def test_linux_archive_url_uses_release_version_and_archive():
    url = fonts.linux_archive_url("Meslo", version="3.4.0")
    assert url == (
        "https://github.com/ryanoasis/nerd-fonts/releases/download/v3.4.0/Meslo.zip"
    )


def test_font_files_present_detects_matching_files(tmp_path):
    # No files yet -> not present.
    assert fonts.font_files_present(str(tmp_path), "MesloLG") is False

    (tmp_path / "MesloLGLDZNerdFont-Regular.ttf").write_bytes(b"\x00")
    (tmp_path / "SomeOtherFont.otf").write_bytes(b"\x00")

    assert fonts.font_files_present(str(tmp_path), "MesloLG") is True
    # A family with no files present stays False.
    assert fonts.font_files_present(str(tmp_path), "JetBrainsMono") is False


def test_font_files_present_is_false_for_missing_dir():
    assert fonts.font_files_present("/no/such/dir", "Meslo") is False


def test_macos_install_is_noop_when_already_present():
    spec = fonts.resolve_font("meslo")
    calls = []
    changed = fonts.install_macos_font(
        spec,
        is_installed_fn=lambda: True,
        brew_install_fn=lambda cask: calls.append(cask),
    )
    assert changed is False
    assert calls == []  # nothing installed


def test_macos_install_runs_cask_when_missing():
    spec = fonts.resolve_font("jetbrains")
    calls = []
    changed = fonts.install_macos_font(
        spec,
        is_installed_fn=lambda: False,
        brew_install_fn=lambda cask: calls.append(cask),
    )
    assert changed is True
    assert calls == ["font-jetbrains-mono-nerd-font"]


def _recorder(log, name, ret=None):
    def fn(*args):
        log.append((name, args))
        return ret
    return fn


def test_linux_install_downloads_extracts_and_refreshes_cache_when_missing(tmp_path):
    spec = fonts.resolve_font("firacode")
    log = []
    changed = fonts.install_linux_font(
        spec, font_dir=str(tmp_path), version="3.4.0",
        present_fn=lambda: False,
        download_fn=_recorder(log, "download", ret="/tmp/FiraCode.zip"),
        extract_fn=_recorder(log, "extract"),
        cache_fn=_recorder(log, "cache"),
    )
    assert changed is True
    names = [c[0] for c in log]
    assert names == ["download", "extract", "cache"]
    # download got the right URL; extract got (archive, font_dir).
    assert log[0][1][0].endswith("/v3.4.0/FiraCode.zip")
    assert log[1][1] == ("/tmp/FiraCode.zip", str(tmp_path))
    assert log[2][1] == (str(tmp_path),)


def test_linux_install_is_noop_when_present():
    spec = fonts.resolve_font("meslo")
    log = []
    changed = fonts.install_linux_font(
        spec, font_dir="/whatever", version="3.4.0",
        present_fn=lambda: True,
        download_fn=_recorder(log, "download"),
        extract_fn=_recorder(log, "extract"),
        cache_fn=_recorder(log, "cache"),
    )
    assert changed is False
    assert log == []


def test_linux_install_download_failure_fails_fast_without_extracting():
    spec = fonts.resolve_font("meslo")
    log = []

    def failing_download(url):
        raise fonts.FontInstallError("404 Not Found")

    with pytest.raises(fonts.FontInstallError):
        fonts.install_linux_font(
            spec, font_dir="/tmp/x", version="3.4.0",
            present_fn=lambda: False,
            download_fn=failing_download,
            extract_fn=_recorder(log, "extract"),
            cache_fn=_recorder(log, "cache"),
        )
    # Nothing was extracted or cached - the system is left unchanged.
    assert log == []
