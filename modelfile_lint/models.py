"""Data models for the Ollama Modelfile linter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Finding:
    """A single lint finding."""

    code: str
    severity: str  # error, warning, info, suggestion
    line: int
    message: str
    replacement: Optional[str] = None  # full replacement line text for auto-fix

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "line": self.line,
            "message": self.message,
            "replacement": self.replacement,
        }


@dataclass
class Instruction:
    """A parsed Modelfile instruction."""

    line: int
    keyword: str  # normalized uppercase keyword
    raw: str  # keyword exactly as written
    args: str  # remainder of the line after the keyword
    block: Optional[str] = None  # fenced-block content (TEMPLATE/SYSTEM/LICENSE)


@dataclass
class Modelfile:
    """A parsed Modelfile."""

    path: str
    lines: list = field(default_factory=list)
    instructions: list = field(default_factory=list)
