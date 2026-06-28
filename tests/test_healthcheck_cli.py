"""Behaviour: the healthcheck CLI is what the final role runs. It prints the
summary and returns a non-zero exit code if any probe fails."""
from tooling.terminal_setup import healthcheck_cli
from tooling.terminal_setup import healthcheck as hc


def test_returns_zero_when_all_probes_pass(capsys):
    probes = [hc.Probe("noop", lambda: hc.ProbeResult(True, "ok"))]
    code = healthcheck_cli.main(argv=[], probes=probes)
    out = capsys.readouterr().out
    assert code == 0
    assert "summary" in out.lower()


def test_returns_nonzero_when_a_probe_fails(capsys):
    probes = [hc.Probe("tmux", lambda: hc.ProbeResult(False, "did not start"))]
    code = healthcheck_cli.main(argv=[], probes=probes)
    out = capsys.readouterr().out
    assert code != 0
    assert "tmux" in out
    assert "did not start" in out


def test_default_probes_has_at_least_one_named_probe():
    probes = healthcheck_cli.build_default_probes()
    assert len(probes) >= 1
    assert all(p.name for p in probes)
