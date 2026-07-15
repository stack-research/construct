"""Deterministic version and date comparison for production scope checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


class CompareDomainError(ValueError):
    pass


def parse_iso_date(value: str) -> date:
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value.strip())
    if not m:
        raise CompareDomainError(f"invalid iso date: {value!r}")
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError as e:
        raise CompareDomainError(f"invalid iso date: {value!r}") from e


def _tokenize_version(value: str) -> tuple[int | str, ...]:
    parts = re.split(r"[.\-+]", value.strip())
    out: list[int | str] = []
    for p in parts:
        if p.isdigit():
            out.append(int(p))
        elif p:
            out.append(p)
    if not out:
        raise CompareDomainError(f"empty version: {value!r}")
    return tuple(out)


def compare_versions(left: str, right: str) -> int:
    """Return -1 if left < right, 0 if equal, 1 if left > right."""
    a = _tokenize_version(left)
    b = _tokenize_version(right)
    n = max(len(a), len(b))
    for i in range(n):
        av = a[i] if i < len(a) else 0
        bv = b[i] if i < len(b) else 0
        if isinstance(av, str) or isinstance(bv, str):
            if av == bv:
                continue
            return -1 if str(av) < str(bv) else 1
        if av < bv:
            return -1
        if av > bv:
            return 1
    return 0


@dataclass(frozen=True)
class RangeConstraint:
    op: str
    bound: str


_GHSA_OPERATORS = (">=", "<=", "<", ">", "=")
# Population GHSA bounds use numeric dotted tokens only (e.g. 7.23.0, 1.8.3).
_VERSION_TOKEN_RE = re.compile(r"^\d+(?:\.\d+)*$")
_UNSUPPORTED_BOUND_MARKERS = re.compile(r"[<>=|,*^~]")


def validate_version_token(token: str) -> str:
    """Accept one numeric_dotted version token; reject improvised forms."""
    bound = token.strip()
    if not bound:
        raise CompareDomainError("empty version token")
    if " " in bound or _UNSUPPORTED_BOUND_MARKERS.search(bound):
        raise CompareDomainError(f"invalid version token: {bound!r}")
    if not _VERSION_TOKEN_RE.fullmatch(bound):
        raise CompareDomainError(f"invalid version token: {bound!r}")
    return bound


def _parse_ghsa_fragment(part: str) -> RangeConstraint:
    fragment = part.strip()
    if not fragment:
        raise CompareDomainError("empty range fragment")
    for op in _GHSA_OPERATORS:
        if fragment.startswith(op):
            bound = fragment[len(op):].strip()
            if not bound:
                raise CompareDomainError(f"malformed range fragment: {part!r}")
            return RangeConstraint(op, validate_version_token(bound))
    raise CompareDomainError(f"unknown range fragment: {part!r}")


def parse_ghsa_range(text: str) -> tuple[RangeConstraint, ...]:
    """Parse comma-separated AND comparators; OR only at outer range_strings."""
    if not text.strip():
        raise CompareDomainError("empty range")
    if "||" in text:
        raise CompareDomainError(f"unsupported range operator in: {text!r}")
    raw_parts = text.split(",")
    if not raw_parts:
        raise CompareDomainError("empty range")
    constraints: list[RangeConstraint] = []
    for part in raw_parts:
        if not part.strip():
            raise CompareDomainError("empty range fragment")
        constraints.append(_parse_ghsa_fragment(part))
    return tuple(constraints)


def version_satisfies_constraints(version: str,
                                  constraints: tuple[RangeConstraint, ...]) -> bool:
    for c in constraints:
        cmp = compare_versions(version, c.bound)
        if c.op == "<" and not (cmp < 0):
            return False
        if c.op == "<=" and not (cmp <= 0):
            return False
        if c.op == ">" and not (cmp > 0):
            return False
        if c.op == ">=" and not (cmp >= 0):
            return False
        if c.op == "=" and cmp != 0:
            return False
    return True


def version_in_any_range(version: str,
                         ranges: tuple[tuple[RangeConstraint, ...], ...]) -> bool:
    return any(version_satisfies_constraints(version, r) for r in ranges)
