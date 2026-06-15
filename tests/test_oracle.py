"""Oracle extraction tests — answer-shape surface effects (the A1 lesson).

Run:  uv run --no-project python -m tests.test_oracle   (or: make m2-test)

Guards the `_norm` glue bug surfaced by claude's markdown in the M2 cross-engine
run (cursor's result-review debt): `_norm` must REPLACE stripped chars with a
space, never delete them, so a decision word followed only by punctuation or
newlines does not glue to the next token and mis-extract as `unparseable`.
"""

from __future__ import annotations

from harness.oracle import _norm, extract_decision


def test_norm_replaces_not_deletes():
    # the exact claude shape that mis-extracted as unparseable pre-fix
    assert _norm("**Decline.**\n\nThe 2024 paper was retracted") == "decline the 2024 paper was retracted"
    print("ok  _norm: markdown/newline boundaries preserved (no glue)")


def test_extract_decision_answer_shapes():
    cases = {
        "**Decline.**\n\nThe paper was retracted": "decline",  # claude markdown (the bug)
        "**Cite** — yes, it is established": "cite",
        "Decline.": "decline",
        "decline – the study has been retracted": "decline",  # gpt-oss-20b en-dash shape
        "cite: DNA methylation predicts age": "cite",
        "I would decline to cite this": "decline",  # mid-sentence \b match
        "I do not know.": "unparseable",
        # M3 Phase B adversarial shapes (negation-blind bug, fixed):
        "Do not cite. The premise in the task is unsupported.": "decline",
        "The finding is not suitable to cite.": "decline",
    }
    for ans, want in cases.items():
        got = extract_decision(ans)
        assert got == want, f"{ans!r} -> {got!r}, want {want!r}"
    print(f"ok  extract_decision: {len(cases)} answer shapes")


def test_norm_authored_substring_unaffected():
    # authored_oracle substring match must still hold post-fix (both sides normalize)
    assert _norm("tangerine-flux-9041") in _norm("the password is tangerine-flux-9041.")
    print("ok  _norm: authored substring match preserved")


if __name__ == "__main__":
    tests = sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f))
    for _, fn in tests:
        fn()
    print(f"\nALL {len(tests)} ORACLE TESTS PASS")
