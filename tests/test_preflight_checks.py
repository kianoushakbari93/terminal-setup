"""Behaviour: the concrete pre-flight checks each pass/fail on the right
condition and carry an actionable reason. Probes are injected so checks are
deterministic and side-effect free."""
from tooling.terminal_setup import preflight, checks


def test_os_supported_passes_on_macos_arm():
    result = checks.os_supported(system="Darwin", machine="arm64").run()
    assert result.ok is True


def test_os_supported_fails_with_reason_on_windows():
    result = checks.os_supported(system="Windows", machine="AMD64").run()
    assert result.ok is False
    assert "Windows" in result.reason


def test_target_writable_passes_for_writable_dir(tmp_path):
    target = tmp_path / "subdir" / ".zshrc"  # parent will be created/owned by us
    result = checks.target_writable(str(target)).run()
    assert result.ok is True


def test_target_writable_fails_when_parent_not_writable():
    result = checks.target_writable("/this/does/not/exist/and/is/not/creatable").run()
    assert result.ok is False
    assert "writable" in result.reason.lower()


def test_disk_space_fails_when_below_minimum():
    result = checks.disk_space(
        path="/", min_bytes=1_000_000_000, free_bytes_fn=lambda p: 200_000_000
    ).run()
    assert result.ok is False
    assert "disk" in result.reason.lower()


def test_network_check_uses_injected_probe():
    reachable = checks.network(probe_fn=lambda host: True).run()
    unreachable = checks.network(probe_fn=lambda host: False).run()
    assert reachable.ok is True
    assert unreachable.ok is False
    assert "network" in unreachable.reason.lower()


def test_sudo_check_uses_injected_probe():
    assert checks.sudo(probe_fn=lambda: True).run().ok is True
    failed = checks.sudo(probe_fn=lambda: False).run()
    assert failed.ok is False
    assert "sudo" in failed.reason.lower()


def test_sudo_check_passes_when_not_required_even_without_sudo():
    # macOS terminal stack needs no sudo; an unavailable sudo must not block it.
    result = checks.sudo(required=False, probe_fn=lambda: False).run()
    assert result.ok is True


def test_sudo_check_enforced_when_required():
    result = checks.sudo(required=True, probe_fn=lambda: False).run()
    assert result.ok is False


def test_checks_compose_into_a_preflight_report():
    report = preflight.run(
        [
            checks.os_supported(system="Darwin", machine="arm64"),
            checks.network(probe_fn=lambda host: False),
        ]
    )
    assert report.ok is False
    assert [f.name for f in report.failures] == ["network"]
