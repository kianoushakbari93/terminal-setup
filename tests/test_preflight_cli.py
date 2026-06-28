"""Behaviour: the pre-flight CLI is what the playbook gate runs. It prints the
report and returns exit 0 when the environment is fine, non-zero otherwise."""
from tooling.terminal_setup import preflight_cli
from tooling.terminal_setup import preflight


def ok_check(name):
    return preflight.Check(name, lambda: preflight.CheckResult(True, ""))


def bad_check(name, reason):
    return preflight.Check(name, lambda: preflight.CheckResult(False, reason))


def test_returns_zero_and_success_text_when_all_pass(capsys):
    code = preflight_cli.main(argv=[], checks=[ok_check("os")])
    out = capsys.readouterr().out
    assert code == 0
    assert "passed" in out


def test_returns_nonzero_and_lists_failures(capsys):
    code = preflight_cli.main(argv=[], checks=[bad_check("network", "cannot reach github.com")])
    out = capsys.readouterr().out
    assert code != 0
    assert "network" in out
    assert "cannot reach github.com" in out


def test_default_checks_cover_the_required_dimensions():
    names = {c.name for c in preflight_cli.build_default_checks()}
    assert {"os", "writable", "disk", "network", "sudo"} <= names
