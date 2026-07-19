"""Body-1 packet-bound action surface and deterministic replay primitives.

The model never supplies executable source. A strict AST classifier maps its
reply to one of two reviewed ids, and the runtime executes only the
corresponding packet-authored expression. Scope is derived from the frozen
program structure, independently of both the model reply and runtime result.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
import selectors
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from .body0 import (
    protected_projection,
    protected_projection_hash,
    record_dict,
    replay_hot_snapshots,
    sha256_json,
    token_cost,
)
from .records import Record

ROOT = Path(__file__).resolve().parent.parent
PACKET_DIR = ROOT / "episodes" / "body1" / "partial-binding"
PACKET_INDEX = PACKET_DIR / "packet_index.json"
ENDORSED_PACKET_INDEX_SHA256 = (
    "22d7e46d4f1598247acefdbb47bf60b3b02050a16697a4ab5cb1ba077b1685f5"
)

BRANCH_R = "B1-R"
BRANCH_C = "B1-C"
BRANCH_A = "B1-A"
BRANCH_X = "B1-X"
RECURRENCE_BRANCHES = (BRANCH_R, BRANCH_C, BRANCH_A, BRANCH_X)

BRANCH_L0 = "B1-L0"
BRANCH_L1 = "B1-L1"
BRANCH_L2 = "B1-L2"
BRANCH_L1_ABLATION = "B1-L1-ablation"
SCOPE_BRANCHES = (BRANCH_L0, BRANCH_L1, BRANCH_L2)

FORM_BARE = "bare_partial"
FORM_NONBINDING = "nonbinding_partial"
FORMS = (FORM_BARE, FORM_NONBINDING)

RENDERER_PREFIX = "body1-expression-renderer-v0.1"


class Body1ContractError(ValueError):
    """Fail-closed Body-1 contract violation."""


@dataclass(frozen=True)
class ExpressionSelection:
    status: str
    form: str | None
    refusal: str | None
    raw_sha256: str
    raw_utf8_bytes: int


@dataclass(frozen=True)
class ScopeDerivation:
    callable_required_positional: int
    bound_positional: int
    post_partial_required_positional: int
    instance_call_user_positional: int
    descriptor_slot: int
    placement: str
    class_name: str
    attribute_name: str

    @property
    def eligible(self) -> bool:
        return self.placement == "class_attribute" and self.descriptor_slot == 0


@dataclass(frozen=True)
class RuntimeResult:
    fixture_id: str
    form: str
    status: str
    outcome: str
    exit_code: int | None
    signal: int | None
    program_sha256: str
    stdout_sha256: str
    stderr_sha256: str
    stdout_bytes: int
    stderr_bytes: int
    elapsed_ms: int
    address_space_limit: str
    invocation: tuple[str, ...]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def packet_index_sha256(path: Path = PACKET_INDEX) -> str:
    return file_sha256(path)


def verify_packet_index(path: Path = PACKET_INDEX) -> list[str]:
    """Return binding errors for the exact reviewed packet."""
    errors: list[str] = []
    if packet_index_sha256(path) != ENDORSED_PACKET_INDEX_SHA256:
        errors.append("packet_index_hash_mismatch")
    index = load_json(path)
    seen: set[str] = set()
    for entry in index.get("entries", []):
        rel = str(entry.get("path", ""))
        if not rel or rel in seen:
            errors.append(f"packet_index_duplicate_or_empty:{rel}")
            continue
        seen.add(rel)
        target = ROOT / rel
        if not target.is_file():
            errors.append(f"packet_file_missing:{rel}")
        elif file_sha256(target) != entry.get("sha256"):
            errors.append(f"packet_file_hash_mismatch:{rel}")
    if len(seen) != 13:
        errors.append(f"packet_entry_count:{len(seen)}")
    indexed_packet_files = {
        Path(rel).name
        for rel in seen
        if Path(rel).parent == Path("episodes/body1/partial-binding")
    }
    actual_packet_files = {
        target.name for target in PACKET_DIR.glob("*.json")
    }
    expected_packet_files = indexed_packet_files | {PACKET_INDEX.name}
    if actual_packet_files != expected_packet_files:
        errors.append(
            "packet_file_set_mismatch:"
            + ",".join(sorted(actual_packet_files ^ expected_packet_files))
        )
    return errors


def _partial_call_matches(node: ast.AST, fixture: dict) -> bool:
    bound_args = fixture["bound_args"]
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "partial"
        and not node.keywords
        and len(node.args) == 1 + len(bound_args)
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == fixture["callable_name"]
        and all(
            isinstance(arg, ast.Constant)
            and isinstance(arg.value, str)
            and arg.value == expected
            for arg, expected in zip(node.args[1:], bound_args)
        )
    )


def classify_expression(
    raw: str | bytes,
    fixture: dict,
    contract: dict | None = None,
) -> ExpressionSelection:
    """Classify raw bytes without executing or semantically normalizing them."""
    contract = contract or load_json(PACKET_DIR / "expression_contract.json")
    normalization = contract["normalization"]
    try:
        raw_bytes = raw if isinstance(raw, bytes) else raw.encode("utf-8")
        text = raw_bytes.decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        digest = hashlib.sha256(
            raw if isinstance(raw, bytes) else raw.encode("utf-8", errors="replace")
        ).hexdigest()
        return ExpressionSelection("unparseable", None, "invalid_utf8", digest, 0)
    digest = hashlib.sha256(raw_bytes).hexdigest()
    if len(raw_bytes) > int(normalization["max_utf8_bytes"]):
        return ExpressionSelection(
            "blocked", None, "blocked(expression_output_limit)",
            digest, len(raw_bytes),
        )
    stripped = text.strip()
    if "\n" in stripped or "\r" in stripped:
        return ExpressionSelection(
            "unparseable", None, "forbidden_multiline",
            digest, len(raw_bytes),
        )
    try:
        body = ast.parse(stripped, mode="eval").body
    except (SyntaxError, ValueError):
        return ExpressionSelection(
            "unparseable", None, "no_match", digest, len(raw_bytes)
        )
    matches: list[str] = []
    if _partial_call_matches(body, fixture):
        matches.append(FORM_BARE)
    if (
        isinstance(body, ast.Call)
        and isinstance(body.func, ast.Name)
        and body.func.id == "staticmethod"
        and not body.keywords
        and len(body.args) == 1
        and _partial_call_matches(body.args[0], fixture)
    ):
        matches.append(FORM_NONBINDING)
    if len(matches) > 1:
        return ExpressionSelection(
            "blocked", None, "blocked(expression_grammar_ambiguous)",
            digest, len(raw_bytes),
        )
    if not matches:
        return ExpressionSelection(
            "unparseable", None, "no_match", digest, len(raw_bytes)
        )
    return ExpressionSelection("selected", matches[0], None, digest, len(raw_bytes))


def _required_positional(function: ast.FunctionDef) -> int:
    positional = [*function.args.posonlyargs, *function.args.args]
    required = len(positional) - len(function.args.defaults)
    if function.args.vararg or function.args.kwarg or function.args.kwonlyargs:
        raise Body1ContractError("fixture callable leaves the closed positional surface")
    return required


def derive_scope(fixture: dict) -> ScopeDerivation:
    """Derive eligibility inputs from packet source, not fixture labels."""
    if fixture["program_template"].count("???") != 1:
        raise Body1ContractError("fixture must contain exactly one placeholder")
    tree = ast.parse(fixture["program_template"].replace("???", "None"))
    functions = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == fixture["callable_name"]
    ]
    if len(functions) != 1:
        raise Body1ContractError("fixture callable is not unique")
    required = _required_positional(functions[0])
    bound = len(fixture["bound_args"])
    post_partial = required - bound
    assignments: list[tuple[str, str]] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and isinstance(stmt.value, ast.Constant)
                and stmt.value.value is None
            ):
                assignments.append((node.name, stmt.targets[0].id))
    if len(assignments) != 1:
        raise Body1ContractError("class-attribute placeholder is not unique")
    class_name, attribute_name = assignments[0]
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        owner = node.func.value
        if (
            node.func.attr == attribute_name
            and isinstance(owner, ast.Call)
            and isinstance(owner.func, ast.Name)
            and owner.func.id == class_name
            and not owner.args
            and not owner.keywords
        ):
            calls.append(node)
    if len(calls) != 1 or calls[0].keywords:
        raise Body1ContractError("instance assertion call is not unique and positional")
    user_positional = len(calls[0].args)
    return ScopeDerivation(
        callable_required_positional=required,
        bound_positional=bound,
        post_partial_required_positional=post_partial,
        instance_call_user_positional=user_positional,
        descriptor_slot=post_partial - user_positional,
        placement="class_attribute",
        class_name=class_name,
        attribute_name=attribute_name,
    )


def scope_matches_declared(fixture: dict, derived: ScopeDerivation) -> bool:
    declared = fixture["scope_inputs"]
    return all(
        declared.get(key) == value
        for key, value in {
            "bound_positional": derived.bound_positional,
            "post_partial_required_positional": (
                derived.post_partial_required_positional
            ),
            "instance_call_user_positional": (
                derived.instance_call_user_positional
            ),
            "descriptor_slot": derived.descriptor_slot,
            "placement": derived.placement,
        }.items()
    )


def build_body1_prompt(
    fixture: dict,
    offered: Iterable[Record] = (),
    foreground: Iterable[dict] = (),
) -> str:
    """The single pre-contact rendering path for every Body-1 fork."""
    sections: list[str] = []
    foreground = list(foreground)
    offered = list(offered)
    if foreground:
        sections.append(
            "\n".join(
                f"Live observation ({row['channel']}, observed "
                f"{row['observed_at']}): {row['text']}"
                for row in foreground
            )
        )
    if offered:
        sections.append(
            "Context records:\n"
            + "\n".join(f"- [{record.record_id}] {record.text}" for record in offered)
        )
    sections.append(fixture["prompt"])
    return "\n\n".join(sections)


def renderer_sha256() -> str:
    source = RENDERER_PREFIX + inspect.getsource(build_body1_prompt)
    return hashlib.sha256(source.encode()).hexdigest()


def _runtime_identity(executable: Path) -> dict:
    probe = (
        "import json,platform,sys;"
        "print(json.dumps({"
        "'implementation':sys.implementation.name,"
        "'python_version':platform.python_version(),"
        "'sys_hexversion':sys.hexversion,"
        "'sys_version':sys.version,"
        "'machine':platform.machine(),"
        "'platform':platform.platform()"
        "},sort_keys=True))"
    )
    proc = subprocess.run(
        [str(executable), "-I", "-S", "-B", "-c", probe],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        timeout=2,
        check=False,
    )
    if proc.returncode or proc.stderr:
        raise Body1ContractError("pinned runtime identity probe failed")
    return json.loads(proc.stdout)


def verify_runtime_pin(runtime: dict | None = None) -> tuple[bool, dict]:
    runtime = runtime or load_json(PACKET_DIR / "runtime_pin.json")
    executable = Path(runtime["executable"]["resolved_at_authoring"])
    build_details = Path(runtime["build_details"]["path_at_authoring"])
    checks = {
        "executable_exists": executable.is_file(),
        "build_details_exists": build_details.is_file(),
    }
    if checks["executable_exists"]:
        checks["executable_sha256"] = (
            file_sha256(executable) == runtime["executable"]["sha256"]
        )
    if checks["build_details_exists"]:
        checks["build_details_sha256"] = (
            file_sha256(build_details) == runtime["build_details"]["sha256"]
        )
    if all(checks.values()):
        identity = _runtime_identity(executable)
        checks.update({
            "implementation": identity["implementation"] == runtime["implementation"],
            "python_version": identity["python_version"] == runtime["python_version"],
            "sys_hexversion": identity["sys_hexversion"] == runtime["sys_hexversion"],
            "sys_version": identity["sys_version"] == runtime["sys_version"],
            "machine": identity["machine"] == runtime["machine"],
            "platform": identity["platform"] == runtime["platform"],
        })
    else:
        identity = {}
    return all(checks.values()), {"checks": checks, "identity": identity}


def _address_space_limiter(limit: int):
    def apply_limit() -> None:
        import resource

        _soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        resource.setrlimit(resource.RLIMIT_AS, (limit, hard))

    return apply_limit


def _collect_bounded(
    process: subprocess.Popen,
    *,
    timeout_seconds: float,
    output_limit: int,
) -> tuple[bytes, bytes, str | None]:
    selector = selectors.DefaultSelector()
    streams = {"stdout": process.stdout, "stderr": process.stderr}
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    for name, stream in streams.items():
        if stream is None:
            continue
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, data=name)
    deadline = time.monotonic() + timeout_seconds
    refusal: str | None = None
    while selector.get_map():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            refusal = "blocked(runtime_timeout)"
            process.kill()
            break
        events = selector.select(min(remaining, 0.05))
        if not events and process.poll() is not None:
            events = [
                (key, selectors.EVENT_READ) for key in selector.get_map().values()
            ]
        for key, _mask in events:
            chunk = os.read(key.fileobj.fileno(), 1024)
            if not chunk:
                selector.unregister(key.fileobj)
                continue
            buffers[key.data].extend(chunk)
            if len(buffers["stdout"]) + len(buffers["stderr"]) > output_limit:
                refusal = "blocked(runtime_output_limit)"
                process.kill()
                break
        if refusal:
            break
    try:
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    return bytes(buffers["stdout"]), bytes(buffers["stderr"]), refusal


def execute_packet_form(
    fixture: dict,
    form: str,
    runtime: dict | None = None,
) -> RuntimeResult:
    """Execute only the packet-authored expression selected by ``form``."""
    runtime = runtime or load_json(PACKET_DIR / "runtime_pin.json")
    if form not in FORMS or form not in fixture["packet_expressions"]:
        raise Body1ContractError(f"unknown packet expression form {form!r}")
    pin_ok, _detail = verify_runtime_pin(runtime)
    if not pin_ok:
        raise Body1ContractError("blocked(runtime_pin_mismatch)")
    expression = fixture["packet_expressions"][form]
    source = fixture["program_template"].replace("???", expression)
    program_sha = hashlib.sha256(source.encode()).hexdigest()
    executable = Path(runtime["executable"]["resolved_at_authoring"])
    flags = tuple(runtime["invocation_flags"])
    limits = runtime["subprocess_limits"]
    started = time.monotonic()
    address_status = "not_attempted"
    with tempfile.TemporaryDirectory(prefix="b1-runtime-") as tmp:
        script = Path(tmp) / "fixture.py"
        script.write_text(source)
        command = (str(executable), *flags, str(script))
        kwargs = {
            "cwd": tmp,
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "env": {"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
            "shell": False,
            "start_new_session": True,
        }
        limiter = _address_space_limiter(
            int(limits["address_space_bytes_target"])
        )
        try:
            process = subprocess.Popen(command, preexec_fn=limiter, **kwargs)
            address_status = "enforced"
        except subprocess.SubprocessError:
            # Darwin exposes RLIMIT_AS but rejects lowering it in this launch
            # path. The reviewed contract makes the 64 MiB value a target only
            # where supported; all other limits remain mandatory.
            process = subprocess.Popen(command, **kwargs)
            address_status = "unsupported_by_launch_path"
        stdout, stderr, refusal = _collect_bounded(
            process,
            timeout_seconds=float(limits["timeout_seconds"]),
            output_limit=int(limits["combined_output_bytes"]),
        )
    elapsed_ms = int((time.monotonic() - started) * 1000)
    returncode = process.returncode
    signal_number = -returncode if returncode is not None and returncode < 0 else None
    if refusal:
        status, outcome = "blocked", refusal
    elif signal_number is not None:
        status, outcome = "blocked", f"blocked(runtime_signal_{signal_number})"
    elif (
        returncode == 0
        and stdout == b"B1_ORACLE_PASS\n"
        and stderr == b""
    ):
        status, outcome = "scored", "pass"
    elif returncode != 0 and b"TypeError:" in stderr:
        status, outcome = "scored", "TypeError"
    elif returncode == 0:
        status, outcome = "blocked", "blocked(runtime_unexpected_output)"
    else:
        status, outcome = "blocked", "blocked(runtime_unrecognized_failure)"
    return RuntimeResult(
        fixture_id=fixture["fixture_id"],
        form=form,
        status=status,
        outcome=outcome,
        exit_code=returncode,
        signal=signal_number,
        program_sha256=program_sha,
        stdout_sha256=hashlib.sha256(stdout).hexdigest(),
        stderr_sha256=hashlib.sha256(stderr).hexdigest(),
        stdout_bytes=len(stdout),
        stderr_bytes=len(stderr),
        elapsed_ms=elapsed_ms,
        address_space_limit=address_status,
        invocation=(str(executable), *flags, "<fresh-temporary-program>"),
    )


def runtime_row(result: RuntimeResult) -> dict:
    return asdict(result)


def ballast_records(sequence: dict | None = None) -> list[Record]:
    sequence = sequence or load_json(PACKET_DIR / "sequence_contract.json")
    return [
        Record(
            record_id=row["record_id"],
            text=row["text"],
            created_at="2026-07-19T00:00:00Z",
            predeclared_usage="context",
            vocabulary_kind="memory",
            trust=1.0,
            provenance={"source": "body1_frozen_ballast"},
        )
        for row in sequence["cost_contract"]["ballast_records"]
    ]


def earned_record_from_mint(
    *,
    source_run_id: str,
    source_runtime: RuntimeResult,
    counterfactual_runtime: RuntimeResult,
) -> Record:
    authored = load_json(PACKET_DIR / "earned_record.json")
    return Record(
        record_id=authored["record_id"],
        text=authored["text"],
        created_at=authored["created_at"],
        predeclared_usage=authored["predeclared_usage"],
        vocabulary_kind=authored["vocabulary_kind"],
        trust=float(authored["trust"]),
        provenance={
            "minted_by": "harness",
            "source_run_id": source_run_id,
            "mint_basis": "external_runtime_consequence",
            "runtime_contract_id": authored["authority_basis"]["oracle"],
            "selected_program_sha256": source_runtime.program_sha256,
            "counterfactual_program_sha256": (
                counterfactual_runtime.program_sha256
            ),
        },
    )


def mint_conditions_hold(
    fixture: dict,
    selection: ExpressionSelection,
    observed: RuntimeResult,
    counterfactual: RuntimeResult,
) -> bool:
    derived = derive_scope(fixture)
    return (
        selection.status == "selected"
        and selection.form == FORM_BARE
        and observed.status == "scored"
        and observed.outcome == "TypeError"
        and derived.descriptor_slot == 0
        and scope_matches_declared(fixture, derived)
        and counterfactual.status == "scored"
        and counterfactual.outcome == "pass"
    )


def body1_projection(
    records: Iterable[Record],
    authority_seed: dict[str, float],
    earned_record_id: str,
) -> dict:
    return protected_projection(records, authority_seed, earned_record_id)


def body1_projection_hash(projection: dict) -> str:
    return protected_projection_hash(projection)


def cost_state_preflight(
    records: Iterable[Record],
    earned_record_id: str,
    residence_count: int,
) -> dict:
    record_texts = {record.record_id: record.text for record in records}
    all_ids = set(record_texts)
    if earned_record_id not in all_ids:
        raise Body1ContractError("earned record absent from cost state")
    full = token_cost(record_texts, all_ids)
    cold = token_cost(record_texts, all_ids - {earned_record_id})
    cost_r = full * (residence_count + 1)
    cost_c = cold * residence_count + full
    return {
        "gate_open": residence_count == 3 and cost_c < cost_r,
        "residence_count": residence_count,
        "full_hot_tokens": full,
        "cold_hot_tokens": cold,
        "rematerialization_hot_tokens": full - cold,
        "cost_R": cost_r,
        "cost_C": cost_c,
        "margin": cost_r - cost_c,
    }


def replay_costs(
    all_ids: Iterable[str],
    record_texts: dict[str, str],
    operations: Iterable[dict],
    seq_indexes: Iterable[int],
) -> tuple[dict[int, frozenset[str]], dict[int, int]]:
    snapshots = replay_hot_snapshots(all_ids, operations, seq_indexes)
    return snapshots, {
        seq: token_cost(record_texts, hot)
        for seq, hot in snapshots.items()
    }


def projection_from_rows(
    rows: Iterable[dict],
    authority_seed: dict[str, float],
    earned_record_id: str,
) -> dict:
    records = [
        Record(**{**row, "supersedes": tuple(row.get("supersedes", ()))})
        for row in rows
    ]
    return body1_projection(records, authority_seed, earned_record_id)


def fixture_path(name: str) -> Path:
    return PACKET_DIR / f"{name}.json"


def fixture(name: str) -> dict:
    return load_json(fixture_path(name))


def records_as_rows(records: Iterable[Record]) -> list[dict]:
    return [record_dict(record) for record in records]


def canonical_digest(value) -> str:
    return sha256_json(value)
