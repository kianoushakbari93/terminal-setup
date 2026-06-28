"""Behaviour: the health suite runs named probes, prints a pass/fail summary,
and signals failure via a non-zero exit code if any probe fails."""
from tooling.terminal_setup import healthcheck as hc


def passing(name):
    return hc.Probe(name, lambda: hc.ProbeResult(True, "ok"))


def failing(name, detail):
    return hc.Probe(name, lambda: hc.ProbeResult(False, detail))


def test_all_probes_pass_yields_exit_zero():
    report = hc.run([passing("zsh starts"), passing("tmux starts")])
    assert report.ok is True
    assert report.exit_code == 0


def test_any_probe_failure_yields_nonzero_exit():
    report = hc.run([passing("zsh starts"), failing("tmux starts", "server did not boot")])
    assert report.ok is False
    assert report.exit_code != 0


def test_summary_names_each_probe_and_its_status():
    report = hc.run([passing("zsh starts"), failing("tmux starts", "server did not boot")])
    summary = report.render()
    assert "zsh starts" in summary
    assert "tmux starts" in summary
    # The failing probe's detail is surfaced so the reason is actionable.
    assert "server did not boot" in summary


def test_probe_that_raises_is_reported_as_failure_not_crash():
    def boom():
        raise RuntimeError("unexpected blow up")

    report = hc.run([hc.Probe("flaky", boom)])
    assert report.ok is False
    assert "unexpected blow up" in report.render()
