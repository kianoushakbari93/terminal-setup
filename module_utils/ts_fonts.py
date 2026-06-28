"""Fonts layer: resolve logical Nerd Font names to install specs, build the
per-OS commands/URLs, probe discoverability, and orchestrate installation with
injected IO so the network/disk effects stay unit-testable.

Pure logic (no Ansible imports); reused by the ``font_install`` module via
``ansible.module_utils``.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Dict, Optional

# Default Nerd Fonts release the Linux path downloads from.
DEFAULT_NERD_FONTS_VERSION = "3.4.0"


class UnknownFont(Exception):
    """Raised for a logical font name not in the catalog."""


class FontInstallError(Exception):
    """Raised when a font cannot be installed (e.g. download failure)."""


@dataclass(frozen=True)
class FontSpec:
    logical: str
    cask: str      # Homebrew cask name (macOS)
    family: str    # substring identifying the font's files (discoverability)
    archive: str   # Nerd Fonts release archive base name (Linux)


_CATALOG: Dict[str, FontSpec] = {
    "meslo": FontSpec("meslo", "font-meslo-lg-nerd-font", "Meslo", "Meslo"),
    "jetbrains": FontSpec("jetbrains", "font-jetbrains-mono-nerd-font", "JetBrainsMono", "JetBrainsMono"),
    "firacode": FontSpec("firacode", "font-fira-code-nerd-font", "FiraCode", "FiraCode"),
}


def resolve_font(logical: str, catalog: Optional[Dict[str, FontSpec]] = None) -> FontSpec:
    catalog = catalog or _CATALOG
    try:
        return catalog[logical]
    except KeyError:
        raise UnknownFont(
            f"Unknown font: {logical!r}. Known fonts: {', '.join(sorted(catalog))}."
        )


def cask_install_cmd(cask: str):
    return ["brew", "install", "--cask", cask]


def cask_is_installed_cmd(cask: str):
    return ["brew", "list", "--cask", cask]


def linux_archive_url(archive: str, version: str = DEFAULT_NERD_FONTS_VERSION) -> str:
    return (
        "https://github.com/ryanoasis/nerd-fonts/releases/download/"
        f"v{version}/{archive}.zip"
    )


_FONT_EXTENSIONS = (".ttf", ".otf")


def font_files_present(font_dir: str, family: str) -> bool:
    """True if any font file whose name contains ``family`` lives in font_dir."""
    font_dir = os.path.expanduser(font_dir)
    if not os.path.isdir(font_dir):
        return False
    family_lower = family.lower()
    for entry in os.listdir(font_dir):
        lower = entry.lower()
        if family_lower in lower and lower.endswith(_FONT_EXTENSIONS):
            return True
    return False


def install_macos_font(
    spec: FontSpec,
    *,
    is_installed_fn: Callable[[], bool],
    brew_install_fn: Callable[[str], None],
) -> bool:
    """Install a font via Homebrew cask, idempotently. Returns whether it
    changed anything. IO is injected so the orchestration is testable."""
    if is_installed_fn():
        return False
    brew_install_fn(spec.cask)
    return True


def install_linux_font(
    spec: FontSpec,
    font_dir: str,
    version: str = DEFAULT_NERD_FONTS_VERSION,
    *,
    present_fn: Callable[[], bool],
    download_fn: Callable[[str], str],
    extract_fn: Callable[[str, str], None],
    cache_fn: Callable[[str], None],
) -> bool:
    """Install a font on Linux: download the Nerd Fonts archive, extract it into
    font_dir, and refresh the font cache. Idempotent; IO injected for testing.

    A download failure raises FontInstallError before anything is extracted, so
    a failed font leaves the system unchanged.
    """
    if present_fn():
        return False
    url = linux_archive_url(spec.archive, version)
    archive_path = download_fn(url)
    extract_fn(archive_path, font_dir)
    cache_fn(font_dir)
    return True
