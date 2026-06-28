"""Behaviour: the pre-flight gate validates the environment and reports ALL
problems together before any change is made (fail-fast, but only after a full
report)."""
from tooling.terminal_setup import preflight


def ok_check(name):
    return preflight.Check(name, lambda: preflight.CheckResult(True, ""))


def failing_check(name, reason):
    return preflight.Check(name, lambda: preflight.CheckResult(False, reason))


def test_all_passing_checks_yield_ok_report():
    report = preflight.run([ok_check("os"), ok_check("network")])
    assert report.ok is True
    assert report.failures == []


def test_collects_every_failure_not_just_the_first():
    report = preflight.run(
        [
            failing_check("network", "no route to host - check your connection"),
            ok_check("sudo"),
            failing_check("disk", "needs 1GB free, only 200MB available"),
        ]
    )
    assert report.ok is False
    # Both failures surfaced, in order, with their remediation reasons.
    assert [f.name for f in report.failures] == ["network", "disk"]
    assert "check your connection" in report.failures[0].reason
    assert "200MB" in report.failures[1].reason


def test_report_renders_human_summary_listing_failures():
    report = preflight.run([failing_check("sudo", "passwordless sudo unavailable")])
    summary = report.render()
    assert "sudo" in summary
    assert "passwordless sudo unavailable" in summary
