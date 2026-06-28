"""Health-suite harness: run named probes after provisioning, render a pass/fail
summary, and expose a process exit code.

Probe-agnostic like the pre-flight gate: callers supply probes, so the suite can
grow (zsh, bash, tmux, fonts...) without changing the harness. A probe that
raises is captured as a failure, never a crash.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List


@dataclass(frozen=True)
class ProbeResult:
    ok: bool
    detail: str = ""


@dataclass(frozen=True)
class Probe:
    name: str
    run: Callable[[], ProbeResult]


@dataclass(frozen=True)
class Outcome:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class Report:
    outcomes: List[Outcome] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(o.ok for o in self.outcomes)

    @property
    def exit_code(self) -> int:
        return 0 if self.ok else 1

    def render(self) -> str:
        lines = ["health-check summary:"]
        for o in self.outcomes:
            mark = "PASS" if o.ok else "FAIL"
            line = f"  [{mark}] {o.name}"
            if o.detail and not o.ok:
                line += f" - {o.detail}"
            lines.append(line)
        passed = sum(1 for o in self.outcomes if o.ok)
        lines.append(f"{passed}/{len(self.outcomes)} probes passed")
        return "\n".join(lines)


def run(probes: List[Probe]) -> Report:
    outcomes: List[Outcome] = []
    for probe in probes:
        try:
            result = probe.run()
            outcomes.append(Outcome(probe.name, result.ok, result.detail))
        except Exception as exc:  # a probe must never crash the suite
            outcomes.append(Outcome(probe.name, False, f"probe error: {exc}"))
    return Report(outcomes=outcomes)
