"""Guard: the brew-prefix logic exists in two execution contexts - the CLI-side
tooling.platform_facts (run via `command`) and the Ansible-module-side
ts_packages (bundled by AnsiballZ). They cannot share code across that boundary,
so this test locks them to identical results and catches any drift."""
import pytest

from tooling.terminal_setup import platform_facts as cli
import ts_packages as mod


CASES = [
    ("Darwin", "arm64"),
    ("Darwin", "x86_64"),
    ("Linux", "x86_64"),
    ("Linux", "aarch64"),
]


@pytest.mark.parametrize("system,machine", CASES)
def test_brew_prefix_agrees_across_contexts(system, machine):
    cli_facts = cli.resolve(system=system, machine=machine)
    mod_family = mod.detect_os_family(system)
    mod_prefix = mod.brew_prefix(mod_family, machine)
    assert cli_facts.os_family == mod_family
    assert cli_facts.brew_prefix == mod_prefix
