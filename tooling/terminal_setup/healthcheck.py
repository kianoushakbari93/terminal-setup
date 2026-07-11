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
    section: str = ""


@dataclass(frozen=True)
class ProbeGroup:
    """A named section of the suite (zsh, bash, tmux) whose runner yields many
    outcomes at once - the deep shell probes measure one live session and
    report every check from it, so they cannot be one-callable-per-check."""
    section: str
    run: Callable[[], List]  # items expose .name / .ok / .detail


@dataclass(frozen=True)
class Outcome:
    name: str
    ok: bool
    detail: str
    section: str = ""


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
        current_section = None
        for o in self.outcomes:
            if o.section != current_section:
                current_section = o.section
                if o.section:
                    lines.append(o.section)
            mark = "PASS" if o.ok else "FAIL"
            line = f"  [{mark}] {o.name}"
            if o.detail and not o.ok:
                line += f" - {o.detail}"
            lines.append(line)
        passed = sum(1 for o in self.outcomes if o.ok)
        lines.append(f"{passed}/{len(self.outcomes)} probes passed")
        if self.outcomes:
            lines.append(
                "all checks passed - terminal is healthy" if self.ok
                else "some checks FAILED - see above"
            )
        return "\n".join(lines)


def run(probes: List) -> Report:
    """Run probes and probe groups in order; nothing they raise may crash the suite."""
    outcomes: List[Outcome] = []
    for probe in probes:
        if isinstance(probe, ProbeGroup):
            try:
                for res in probe.run():
                    outcomes.append(Outcome(res.name, res.ok, res.detail, probe.section))
            except Exception as exc:
                outcomes.append(
                    Outcome(f"{probe.section} probes", False, f"probe error: {exc}", probe.section)
                )
            continue
        try:
            result = probe.run()
            outcomes.append(Outcome(probe.name, result.ok, result.detail, probe.section))
        except Exception as exc:  # a probe must never crash the suite
            outcomes.append(Outcome(probe.name, False, f"probe error: {exc}", probe.section))
    return Report(outcomes=outcomes)
