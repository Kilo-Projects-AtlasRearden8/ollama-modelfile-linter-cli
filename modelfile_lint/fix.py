"""Auto-fix application for lint findings."""

from __future__ import annotations

from .models import Finding


def apply_fixes(text: str, findings: list[Finding]) -> tuple[str, list[Finding]]:
    """Apply suggested fixes to ``text``.

    Line-based fixes are applied bottom-up so line numbers stay valid.
    Only findings carrying a ``replacement`` are applied. Returns the
    patched text and the list of findings that were applied.
    """
    lines = text.split("\n")
    applied: list[Finding] = []
    fixable = [f for f in findings if f.replacement is not None]
    add_trailing_newline = any(f.replacement == "" for f in fixable)

    for finding in sorted(fixable, key=lambda f: f.line, reverse=True):
        idx = finding.line - 1
        if idx < 0 or idx >= len(lines):
            continue
        if finding.replacement == "":
            continue
        lines[idx] = finding.replacement
        applied.append(finding)

    result = "\n".join(lines)
    if add_trailing_newline and not result.endswith("\n"):
        result = result + "\n"

    return result, applied
