"""Parsing and lint rules for Ollama Modelfiles.

Local-first, dependency-free logic. Reads Modelfile text, validates
instructions, parameter ranges, and formatting, and returns findings.
"""

from __future__ import annotations

from typing import Optional

from .models import Finding, Instruction, Modelfile

KNOWN_INSTRUCTIONS = frozenset(
    {"FROM", "PARAMETER", "TEMPLATE", "SYSTEM", "MESSAGE", "ADAPTER", "LICENSE"}
)

REQUIRED_INSTRUCTIONS = frozenset({"FROM"})

# Parameter validation rules. Each entry may define:
#   min / max: inclusive numeric bounds (None = unbounded)
#   strict_min: value must be strictly greater than min
#   allowed: discrete set of allowed values (takes precedence over min/max)
ParameterRule = dict

PARAMETER_RULES: dict[str, ParameterRule] = {
    "temperature": {"min": 0.0, "max": 2.0},
    "top_p": {"min": 0.0, "max": 1.0},
    "top_k": {"min": 0, "max": None},
    "repeat_penalty": {"min": 0.0, "max": None},
    "seed": {"min": None, "max": None},
    "num_ctx": {"min": 0, "max": None},
    "num_predict": {"min": -1, "max": None},
    "num_gpu": {"min": 0, "max": None},
    "num_thread": {"min": 0, "max": None},
    "mirostat": {"allowed": (0, 1, 2)},
    "mirostat_eta": {"min": 0.0, "max": None, "strict_min": True},
    "mirostat_tau": {"min": 0.0, "max": None},
    "num_keep": {"min": 0, "max": None},
    "num_seq": {"min": 1, "max": None},
    "tfs_z": {"min": 0.0, "max": None},
    "typical_p": {"min": 0.0, "max": None, "strict_min": True},
    "presence_penalty": {"min": -2.0, "max": 2.0},
    "frequency_penalty": {"min": -2.0, "max": 2.0},
}

FENCED_INSTRUCTIONS = frozenset({"TEMPLATE", "SYSTEM", "LICENSE"})

FENCE_MARKERS = ('"""', "'''")


def _is_fenced(args: str) -> Optional[str]:
    """Return the fence marker if ``args`` opens a fenced block, else None."""
    for marker in FENCE_MARKERS:
        if args.startswith(marker):
            return marker
    return None


def _close_fence(lines: list[str], start: int, n: int, marker: str, initial: str = "") -> tuple[str, int]:
    """Read a fenced block from ``lines[start+1:]`` until the closing fence.

    ``initial`` is content already gathered from the opening line. Returns the
    block content and the index of the closing line. If no closing fence is
    found, consumes to the end of the file.
    """
    content = initial
    j = start
    closed = False
    while j < n:
        if marker in lines[j]:
            before, _ = lines[j].split(marker, 1)
            content += before
            closed = True
            break
        content += "\n" + lines[j]
        j += 1
    if not closed:
        j = n - 1
    return content, j


def replacement_line(keyword: str, args: str) -> str:
    """Return a normalized instruction line text."""
    return f"{keyword} {args}".strip()


def parse(text: str, path: str = "<stdin>") -> Modelfile:
    """Parse Modelfile text into a Modelfile model."""
    lines = text.split("\n")
    mf = Modelfile(path=path)
    mf.lines = lines
    i = 0
    n = len(lines)
    while i < n:
        raw_line = lines[i]
        stripped = raw_line.strip()
        line_no = i + 1
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        parts = stripped.split(None, 1)
        keyword = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        upper = keyword.upper()
        instruction = Instruction(line=line_no, keyword=upper, raw=keyword, args=args)

        if upper in FENCED_INSTRUCTIONS:
            marker = _is_fenced(args)
            if marker is not None:
                if args.count(marker) >= 2:
                    # Single-line fenced block: SYSTEM """text here."""
                    content = args[len(marker):].split(marker, 1)[0]
                    instruction.block = content
                else:
                    # Multi-line fenced block, closing fence on a later line.
                    content = args[len(marker):]
                    content, i = _close_fence(lines, i + 1, n, marker, initial=content)
                    instruction.block = content
        mf.instructions.append(instruction)
        i += 1
    return mf


def _strip_quotes(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        return v[1:-1]
    return v


def _check_parameter(line: int, key: str, value: str, rule: ParameterRule) -> Optional[Finding]:
    klower = key.lower()
    inner = _strip_quotes(value)

    if "allowed" in rule:
        try:
            num = int(inner)
        except ValueError:
            try:
                f = float(inner)
                num = int(f) if f.is_integer() else None
            except ValueError:
                num = None
        if num is None or num not in rule["allowed"]:
            return Finding(
                "MOD003",
                "warning",
                line,
                f"Parameter '{key}'={value} must be one of {sorted(rule['allowed'])}.",
                replacement=None,
            )
        return None

    try:
        num = float(inner)
    except ValueError:
        return Finding(
            "MOD003",
            "error",
            line,
            f"Parameter '{key}' value '{value}' is not a number.",
            replacement=None,
        )

    lo = rule.get("min")
    hi = rule.get("max")
    strict_min = rule.get("strict_min", False)

    if lo is not None:
        bound_ok = num > lo if strict_min else num >= lo
        if not bound_ok:
            relation = "greater than" if strict_min else "below minimum"
            extra = f" (must be {relation} {lo})" if strict_min else ""
            fixed = lo + 0.1 if strict_min else lo
            return Finding(
                "MOD003",
                "warning",
                line,
                f"Parameter '{key}'={value} is outside the valid range{extra}.",
                replacement=replacement_line("PARAMETER", f"{key} {fixed:g}"),
            )
    if hi is not None and num > hi:
        return Finding(
            "MOD003",
            "warning",
            line,
            f"Parameter '{key}'={value} exceeds maximum {hi}.",
            replacement=replacement_line("PARAMETER", f"{key} {hi:g}"),
        )
    return None


def lint(mf: Modelfile) -> list[Finding]:
    """Lint a parsed Modelfile and return a list of findings."""
    findings: list[Finding] = []
    instructions = mf.instructions

    from_instructions = [inst for inst in instructions if inst.keyword == "FROM"]
    if not from_instructions:
        findings.append(
            Finding(
                "MOD001",
                "error",
                1,
                "Missing required FROM instruction.",
                replacement=None,
            )
        )
    else:
        first_seen = False
        for inst in instructions:
            if inst.keyword != "FROM":
                continue
            if not first_seen:
                first_seen = True
                continue
            findings.append(
                Finding(
                    "MOD007",
                    "warning",
                    inst.line,
                    "FROM appears more than once; only the first FROM is used.",
                    replacement=None,
                )
            )

    seen_params: set = set()
    for inst in instructions:
        if inst.keyword not in KNOWN_INSTRUCTIONS:
            findings.append(
                Finding(
                    "MOD002",
                    "warning",
                    inst.line,
                    f"Unknown instruction '{inst.raw}'.",
                    replacement=None,
                )
            )
            continue

        if inst.raw != inst.keyword:
            findings.append(
                Finding(
                    "MOD005",
                    "suggestion",
                    inst.line,
                    f"Instruction '{inst.raw}' should be uppercase '{inst.keyword}'.",
                    replacement=replacement_line(inst.keyword, inst.args),
                )
            )

        if inst.keyword == "PARAMETER":
            parts = inst.args.split(None, 1)
            if len(parts) < 2:
                findings.append(
                    Finding(
                        "MOD003",
                        "error",
                        inst.line,
                        "PARAMETER instruction requires both a key and a value.",
                        replacement=None,
                    )
                )
                continue
            key, value = parts[0], parts[1].strip()
            klower = key.lower()
            if klower in seen_params:
                findings.append(
                    Finding(
                        "MOD004",
                        "info",
                        inst.line,
                        f"Duplicate parameter '{key}'; the last value wins.",
                        replacement=None,
                    )
                )
            seen_params.add(klower)

            rule = PARAMETER_RULES.get(klower)
            if rule is not None:
                result = _check_parameter(inst.line, key, value, rule)
                if result is not None:
                    findings.append(result)

    if mf.lines and mf.lines[-1] != "":
        findings.append(
            Finding(
                "MOD006",
                "suggestion",
                len(mf.lines),
                "File does not end with a newline.",
                replacement="",
            )
        )

    return findings
