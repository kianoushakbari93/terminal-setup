"""Pre-flight gate: run a set of named environment checks, collect EVERY
failure, and present them together before the tool makes any change.

The aggregator is pure and check-agnostic: callers pass in the checks, so it is
fully testable with fakes and the real checks can grow independently.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    reason: str = ""


@dataclass(frozen=True)
class Check:
    name: str
    run: Callable[[], CheckResult]


@dataclass(frozen=True)
class Failure:
    name: str
    reason: str


@dataclass(frozen=True)
class Report:
    ok: bool
    failures: List[Failure] = field(default_factory=list)

    def render(self) -> str:
        if self.ok:
            return "pre-flight: all checks passed"
        lines = ["pre-flight failed - resolve these before re-running:"]
        for f in self.failures:
            lines.append(f"  - {f.name}: {f.reason}")
        return "\n".join(lines)


def run(checks: List[Check]) -> Report:
    """Run all checks, never stopping at the first failure, and aggregate."""
    failures: List[Failure] = []
    for check in checks:
        result = check.run()
        if not result.ok:
            failures.append(Failure(check.name, result.reason))
    return Report(ok=not failures, failures=failures)
