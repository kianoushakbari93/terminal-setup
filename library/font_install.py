#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Ansible module: install a Nerd Font idempotently - via Homebrew cask on
macOS, or by downloading the Nerd Fonts archive into ~/.local/share/fonts and
refreshing the font cache on Linux. Thin wrapper around the ``ts_fonts`` engine.
"""
from __future__ import annotations

DOCUMENTATION = r"""
---
module: font_install
short_description: Install a Nerd Font (Meslo/JetBrainsMono/FiraCode) per-OS.
description:
  - macOS installs via the Homebrew cask; Linux downloads the Nerd Fonts archive
    into the user font dir and runs fc-cache.
  - "Idempotent: a font already discoverable reports ok (not changed)."
options:
  name:
    description: Logical font name (meslo|jetbrains|firacode).
    required: true
    type: str
  os_family:
    description: Override detected OS family (macos|linux).
    type: str
  font_dir:
    description: Override the font install directory.
    type: str
  version:
    description: Nerd Fonts release version (Linux download).
    type: str
author:
  - Terminal Setup
"""

EXAMPLES = r"""
- name: Install the Meslo Nerd Font
  font_install:
    name: meslo
"""

RETURN = r"""
changed:
  description: Whether the font was installed by this run.
  type: bool
name:
  description: The resolved concrete font (cask) name.
  type: str
"""

import os
import platform
import tempfile
import zipfile

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils import ts_fonts
from ansible.module_utils import ts_packages


def _default_font_dir(os_family):
    home = os.path.expanduser("~")
    if os_family == "macos":
        return os.path.join(home, "Library", "Fonts")
    return os.path.join(home, ".local", "share", "fonts")


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type="str", required=True),
            os_family=dict(type="str", required=False, default=None),
            font_dir=dict(type="str", required=False, default=None),
            version=dict(type="str", required=False, default=ts_fonts.DEFAULT_NERD_FONTS_VERSION),
        ),
        supports_check_mode=True,
    )
    p = module.params
    try:
        os_family = p["os_family"] or ts_packages.detect_os_family(platform.system())
        spec = ts_fonts.resolve_font(p["name"])
    except (ts_fonts.UnknownFont, ts_packages.UnsupportedPlatform) as exc:
        module.fail_json(msg=str(exc))

    font_dir = p["font_dir"] or _default_font_dir(os_family)
    present = ts_fonts.font_files_present(font_dir, spec.family)

    if module.check_mode:
        module.exit_json(changed=not present, name=spec.cask)

    try:
        if os_family == "macos":
            def brew_install(cask):
                rc, out, err = module.run_command(ts_fonts.cask_install_cmd(cask))
                if rc != 0:
                    raise ts_fonts.FontInstallError(err.strip() or out.strip())
            changed = ts_fonts.install_macos_font(
                spec,
                is_installed_fn=lambda: present,
                brew_install_fn=brew_install,
            )
        else:
            changed = ts_fonts.install_linux_font(
                spec, font_dir, p["version"],
                present_fn=lambda: present,
                download_fn=_download,
                extract_fn=_extract_fonts,
                cache_fn=lambda d: module.run_command(["fc-cache", "-f", d]),
            )
    except ts_fonts.FontInstallError as exc:
        module.fail_json(msg="failed to install font %s: %s" % (p["name"], exc), name=spec.cask)

    module.exit_json(changed=changed, name=spec.cask)


def _download(url):
    import urllib.request
    try:
        fd, path = tempfile.mkstemp(suffix=".zip")
        os.close(fd)
        urllib.request.urlretrieve(url, path)
        return path
    except Exception as exc:  # noqa: BLE001 - surface as a clean font error
        raise ts_fonts.FontInstallError("download failed for %s: %s" % (url, exc))


def _extract_fonts(archive_path, font_dir):
    os.makedirs(font_dir, exist_ok=True)
    with zipfile.ZipFile(archive_path) as zf:
        for member in zf.namelist():
            if member.lower().endswith((".ttf", ".otf")):
                target = os.path.join(font_dir, os.path.basename(member))
                with zf.open(member) as src, open(target, "wb") as dst:
                    dst.write(src.read())


if __name__ == "__main__":
    main()
