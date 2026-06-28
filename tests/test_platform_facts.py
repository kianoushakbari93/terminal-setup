"""Behaviour: the tool resolves OS-specific facts (Homebrew prefix, package
manager family) so later roles render correct paths per platform."""
import pytest

from tooling.terminal_setup import platform_facts as pf


def test_macos_arm_uses_opt_homebrew():
    facts = pf.resolve(system="Darwin", machine="arm64")
    assert facts.brew_prefix == "/opt/homebrew"
    assert facts.os_family == "macos"


def test_macos_intel_uses_usr_local():
    facts = pf.resolve(system="Darwin", machine="x86_64")
    assert facts.brew_prefix == "/usr/local"
    assert facts.os_family == "macos"


def test_linux_uses_linuxbrew_prefix():
    facts = pf.resolve(system="Linux", machine="x86_64")
    assert facts.brew_prefix == "/home/linuxbrew/.linuxbrew"
    assert facts.os_family == "linux"


def test_unsupported_system_raises_clear_error():
    with pytest.raises(pf.UnsupportedPlatform) as exc:
        pf.resolve(system="Windows", machine="AMD64")
    assert "Windows" in str(exc.value)
