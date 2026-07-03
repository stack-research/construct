"""Closed predicate AST — SPEC_PAUSE_RESUME v0.1 §5.

Shared by the obligation rulebook (trigger/satisfaction predicates), the reopen
rules, and the fixture gate. The discipline is X2/WB `match_rule` one level up:
no prose rules, no post-hoc extension, one library hash pinned at
`population_precommit`. Fail-closed on any unknown node, field, or operator —
a predicate the validator cannot fully walk is refused, never partially
evaluated.

Field vocabulary and operators are the CLOSED sets from SPEC §5. Explicitly
out (v0.1): substring/regex over body text, semantic entity extraction, answer
fields, branch route references, read-order win conditions, token counts,
model-produced tags. If an episode needs those it is v0.2/open-semantic, not a
rulebooked run.

AST node shapes (JSON, canonical):
  {"op": "eq"|"neq", "field": <field>, "value": <scalar>}
  {"op": "in"|"not_in", "field": <field>, "values": [<scalar>, ...]}
  {"op": "exists"|"not_exists", "field": <field>}
  {"op": "and"|"or", "args": [<node>, ...]}
  {"op": "not", "arg": <node>}
  {"op": "changed"}                  # sha(surface_hash_t0) != sha(surface_hash_t1)
  {"op": "read_has_tag", "tag": <tag>}   # witness_read context only
"""

from __future__ import annotations

import hashlib
import json

# Closed field vocabulary (SPEC §5). `catalog_key` is the alias-class of
# `status_key`: a rule uses one or the other, never both (gate-enforced).
FIELDS = frozenset({
    "surface_id", "surface_hash_t0", "surface_hash_t1", "surface_text_changed",
    "surface_tag", "surface_kind", "certificate_eligible",
    "option_id", "option_status",
    "obligation_id", "obligation_kind", "obligation_status",
    "match_key_id", "catalog_key", "status_key",
    "status_value_t0", "status_value_t1",
    "seam_id", "timestamp", "continuation_step_id",
    "frontier_artifact_id", "frontier_artifact_hash",
    "reopen_rule_id", "world_leg", "catalog_epoch", "relation_code",
    # witness_read evaluation context (SPEC §5: trigger predicates fire on
    # witnessed pre-seam reads, not catalog rows alone)
    "read_index",
})

OPERATORS = frozenset({
    "eq", "neq", "in", "not_in", "exists", "not_exists",
    "and", "or", "not", "changed", "read_has_tag",
})

OBLIGATION_KINDS = frozenset({"read", "verify", "reopen", "discard", "continue"})
OBLIGATION_STATUSES = frozenset({"pending", "satisfied", "invalidated"})


class PredicateClosureError(ValueError):
    """A predicate stepped outside the closed vocabulary. Fail-closed."""


def _refuse(msg: str) -> None:
    raise PredicateClosureError(msg)


def validate(node: dict) -> None:
    """Walk the AST; refuse on any unknown operator, field, key, or shape.
    Numeric scalar values are refused everywhere (no token counts, no scores —
    the answer-axis exclusions are structural, not advisory)."""
    if not isinstance(node, dict):
        _refuse(f"AST node must be an object, got {type(node).__name__}")
    op = node.get("op")
    if op not in OPERATORS:
        _refuse(f"unknown operator {op!r} — closed set is {sorted(OPERATORS)}")

    keys = set(node) - {"op"}
    if op in ("eq", "neq"):
        if keys != {"field", "value"}:
            _refuse(f"{op} takes exactly field+value, got {sorted(keys)}")
        _check_field(node["field"])
        _check_scalar(node["value"], op)
    elif op in ("in", "not_in"):
        if keys != {"field", "values"}:
            _refuse(f"{op} takes exactly field+values, got {sorted(keys)}")
        _check_field(node["field"])
        if not isinstance(node["values"], list) or not node["values"]:
            _refuse(f"{op}.values must be a non-empty list")
        for v in node["values"]:
            _check_scalar(v, op)
    elif op in ("exists", "not_exists"):
        if keys != {"field"}:
            _refuse(f"{op} takes exactly field, got {sorted(keys)}")
        _check_field(node["field"])
    elif op in ("and", "or"):
        if keys != {"args"}:
            _refuse(f"{op} takes exactly args, got {sorted(keys)}")
        if not isinstance(node["args"], list) or len(node["args"]) < 2:
            _refuse(f"{op}.args must list >= 2 nodes")
        for child in node["args"]:
            validate(child)
    elif op == "not":
        if keys != {"arg"}:
            _refuse(f"not takes exactly arg, got {sorted(keys)}")
        validate(node["arg"])
    elif op == "changed":
        if keys:
            _refuse(f"changed takes no arguments, got {sorted(keys)}")
    elif op == "read_has_tag":
        if keys != {"tag"}:
            _refuse(f"read_has_tag takes exactly tag, got {sorted(keys)}")
        if not isinstance(node["tag"], str):
            _refuse("read_has_tag.tag must be a string")


def _check_field(field) -> None:
    if field not in FIELDS:
        _refuse(f"field {field!r} outside the closed vocabulary")


def _check_scalar(value, op: str) -> None:
    # bool is admitted (certificate_eligible); int/float are the answer-axis
    # smuggling shapes (scores, weights, counts) and are refused.
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        _refuse(f"{op} carries numeric value {value!r} — scalar valuation is "
                "refused in predicates (SPEC §5 exclusions)")
    if not isinstance(value, str):
        _refuse(f"{op} value must be string/bool, got {type(value).__name__}")


def evaluate(node: dict, ctx: dict) -> bool:
    """Evaluate a VALIDATED node against a context. ctx maps field -> value;
    for `read_has_tag`, ctx carries `surface_tags` (the witness_read context).
    A field absent from ctx is absent — eq/neq/in on it are False, exists is
    False, not_exists is True. Evaluation never mutates ctx."""
    op = node["op"]
    if op == "eq":
        return ctx.get(node["field"]) == node["value"]
    if op == "neq":
        f = node["field"]
        return f in ctx and ctx[f] != node["value"]
    if op == "in":
        return ctx.get(node["field"]) in node["values"]
    if op == "not_in":
        f = node["field"]
        return f in ctx and ctx[f] not in node["values"]
    if op == "exists":
        return node["field"] in ctx and ctx[node["field"]] is not None
    if op == "not_exists":
        return not (node["field"] in ctx and ctx[node["field"]] is not None)
    if op == "and":
        return all(evaluate(a, ctx) for a in node["args"])
    if op == "or":
        return any(evaluate(a, ctx) for a in node["args"])
    if op == "not":
        return not evaluate(node["arg"], ctx)
    if op == "changed":
        t0, t1 = ctx.get("surface_hash_t0"), ctx.get("surface_hash_t1")
        return t0 is not None and t1 is not None and t0 != t1
    if op == "read_has_tag":
        return node["tag"] in ctx.get("surface_tags", [])
    raise PredicateClosureError(f"unreachable operator {op!r}")  # pragma: no cover


def library_hash(library: dict[str, dict]) -> str:
    """Canonical hash of a predicate library {predicate_id: ast}. Pinned at
    `population_precommit`; every predicate is validated before hashing so an
    out-of-closure library can never be pinned."""
    for pid, ast in sorted(library.items()):
        try:
            validate(ast)
        except PredicateClosureError as e:
            _refuse(f"library predicate {pid!r}: {e}")
    return hashlib.sha256(
        json.dumps(library, sort_keys=True).encode()).hexdigest()
