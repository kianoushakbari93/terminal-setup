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


def _capture_sudo_required(monkeypatch):
    captured = {}

    def fake_sudo(required=True, probe_fn=None):
        captured["required"] = required
        return preflight.Check("sudo", lambda: preflight.CheckResult(True))

    monkeypatch.setattr(preflight_cli._checks, "sudo", fake_sudo)
    return captured


def test_sudo_not_required_when_run_has_no_native_prereqs(monkeypatch):
    # Only prereq-kind packages use the native manager (and thus sudo); a run
    # with none - the default stack is pure Homebrew/Linuxbrew - must not
    # demand elevation, even on Linux.
    captured = _capture_sudo_required(monkeypatch)
    preflight_cli.build_default_checks(prereq_count=0)
    assert captured["required"] is False


def test_sudo_required_on_linux_when_native_prereqs_present(monkeypatch):
    captured = _capture_sudo_required(monkeypatch)
    monkeypatch.setattr(
        preflight_cli.platform_facts,
        "resolve",
        lambda: preflight_cli.platform_facts.PlatformFacts(
            os_family="linux", brew_prefix="/home/linuxbrew/.linuxbrew"
        ),
    )
    preflight_cli.build_default_checks(prereq_count=2)
    assert captured["required"] is True


def test_sudo_required_on_linux_when_prereq_count_unknown(monkeypatch):
    # Without the count the CLI stays conservative on Linux.
    captured = _capture_sudo_required(monkeypatch)
    monkeypatch.setattr(
        preflight_cli.platform_facts,
        "resolve",
        lambda: preflight_cli.platform_facts.PlatformFacts(
            os_family="linux", brew_prefix="/home/linuxbrew/.linuxbrew"
        ),
    )
    preflight_cli.build_default_checks()
    assert captured["required"] is True


def test_sudo_never_required_on_macos(monkeypatch):
    captured = _capture_sudo_required(monkeypatch)
    monkeypatch.setattr(
        preflight_cli.platform_facts,
        "resolve",
        lambda: preflight_cli.platform_facts.PlatformFacts(
            os_family="macos", brew_prefix="/opt/homebrew"
        ),
    )
    preflight_cli.build_default_checks(prereq_count=5)
    assert captured["required"] is False


def test_prereq_count_flag_is_parsed(capsys):
    code = preflight_cli.main(argv=["--prereq-count", "0"], checks=[ok_check("os")])
    assert code == 0
