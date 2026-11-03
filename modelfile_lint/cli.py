"""Command-line interface for modelfile-lint."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional, Sequence

from . import __version__
from .fix import apply_fixes
from .lint import lint, parse

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2, "suggestion": 3}


def _format_text(path: str, findings: list) -> str:
    lines: list[str] = []
    for finding in findings:
        fix = f"  -> {finding.replacement}" if finding.replacement else ""
        lines.append(
            f"{path}:{finding.line}: {finding.code} {finding.severity}: {finding.message}{fix}"
        )
    return "\n".join(lines)


def _lint_text(text: str, path: str) -> list:
    mf = parse(text, path)
    return lint(mf)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="modelfile-lint",
        description=(
            "Local-first linter for Ollama Modelfiles. Checks parameter "
            "ranges, valid instructions, and readable formatting, with "
            "suggested fixes."
        ),
    )
    parser.add_argument(
        "files", nargs="*", help="Modelfile(s) to lint. Reads stdin if none given."
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply suggested fixes in place (default: report only).",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--min-severity",
        choices=["error", "warning", "info", "suggestion"],
        default="suggestion",
        help="Minimum severity to report (default: suggestion).",
    )
    args = parser.parse_args(argv)

    min_level = SEVERITY_ORDER[args.min_severity]
    targets = args.files if args.files else ["-"]

    had_error = False
    results = []

    for target in targets:
        if target == "-":
            text = sys.stdin.read()
            path = "<stdin>"
        else:
            with open(target, "r", encoding="utf-8") as handle:
                text = handle.read()
            path = target

        findings = _lint_text(text, path)
        findings = [f for f in findings if SEVERITY_ORDER[f.severity] <= min_level]

        if any(f.severity == "error" for f in findings):
            had_error = True

        if args.fix and target != "-":
            text, _applied = apply_fixes(text, findings)
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(text)
            # Re-lint after fixing so output reflects the patched file.
            findings = [f for f in _lint_text(text, path) if SEVERITY_ORDER[f.severity] >= min_level]
            if any(f.severity == "error" for f in findings):
                had_error = True

        results.append((path, findings))

    if args.format == "json":
        payload = [
            {"file": path, "findings": [f.to_dict() for f in findings]}
            for path, findings in results
        ]
        print(json.dumps(payload, indent=2))
    else:
        output = []
        for path, findings in results:
            output.append(_format_text(path, findings))
        report = "\n".join(part for part in output if part)
        if report:
            print(report)

    return 1 if had_error else 0


if __name__ == "__main__":
    sys.exit(main())
