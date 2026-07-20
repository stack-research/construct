# Frontier obligation admission findings

Status: **CLOSED 2026-07-19 —
`admission_refused(commitment_invalid)`**.

This is an admission-surface result, not a memory finding. It closes the
consequence-bound-obligation admission lineage without answering the underlying
conjecture.

## Exact run

- packet index:
  `5da170547db2a779880bcfdb01827aa2d30ae9471357f6c6c53ccf977489a3b2`;
- implementation manifest:
  `8a20aba44499d1e55a78fc93f5fe48bd4e32b2cea96d779225da0bf31d217aef`;
- implementation review: ended thread
  `frontier-obligation-wire-review`, two exact-hash endorsements;
- execution pin:
  `36fc289158df1a983b30a2d5b376303968c8d6e965c71614e9f23b30259f5845`;
- pin review: ended thread
  `frontier-obligation-execution-pin-review`, two exact-hash endorsements;
- candidate: `mistralai/ministral-3-3b`;
- receipt:
  [`20260719T221820Z-ministral-3-3b.json`](../runs/frontier_obligation/admission/20260719T221820Z-ministral-3-3b.json),
  SHA-256
  `67f3708f9301e0c2af70a30fa2d401a85959a72d0dfa9a4eae94e9a4080a24e3`;
- checker report:
  [`20260719T221820Z-ministral-3-3b.check.json`](../runs/frontier_obligation/admission/20260719T221820Z-ministral-3-3b.check.json),
  SHA-256
  `b387b75caf635dc8c7bcf5b7ff121003e32e294784e57ba22c4041d14227e24b`.

The runner made all twelve stateless calls in canonical order at temperature
zero with zero retries. Requested and observed model identities matched. No
tool calls appeared. Total output was 305 tokens against the precommitted
6,144-token ceiling.

## Computed result

The independent checker returned:

```text
outcome:                    admission_refused(commitment_invalid)
valid commitments:          8 / 12
correct commitments:        8 / 12
paired output changes:      6 / 6
valid PROMOTE selections:   6
valid WAIT selections:      2
valid first positions:      5
valid second positions:     3
```

Four calls failed the closed wire:

| Fixture | Expected exact label | Returned enum | Refusal |
| --- | --- | --- | --- |
| `P1-later` | `WAIT adm-cedar-17` | `WAIT` | `unknown_enum` |
| `P2-later` | `WAIT adm-flint-28` | `WAIT` | `unknown_enum` |
| `P3-later` | `WAIT adm-harbor-39` | `WAIT` | `unknown_enum` |
| `P5-first` | `WAIT adm-juniper-52` | `WAIT` | `unknown_enum` |

The JSON objects were extractable; code fences were allowed by the frozen
extractor. The failure was narrower: four responses omitted the artifact id
from the action label. All six expected `PROMOTE` actions and two of six
expected `WAIT` actions used exact labels.

Every valid commitment matched the latest-status rule. The four invalid
commitments also pointed in the semantically appropriate `WAIT` direction, but
the precommit explicitly forbade output repair or reinterpretation. They
therefore cannot be promoted into valid actions or policy evidence. The passed
pair-change check is likewise non-dispositive once wire competence fails.

## What this establishes

The admission gate separated policy understanding from executable commitment
discipline. This candidate appeared to understand the explicit rule but did not
reliably emit an artifact-qualified action on the frozen wire. That is exactly
the surface risk the gate was built to consume before treatment.

It does **not** establish that:

- a consequence-bound obligation persists across a cold session;
- an action-boundary recheck improves safety or liveness;
- offering and rechecking differ;
- any memory mechanism works or fails.

No `G/O/S/N` packet was implemented or contacted.

## Terminal disposition

The reviewed proposal made the first typed miss terminal. Accordingly:

- no response was repaired;
- no call was retried;
- no decoding or prompt parameter changed;
- no replacement candidate was selected;
- no second execution pin will be authored;
- no treatment or scored experimental call is licensed.

The concept remains a coherent, cold-endorsed proposal, but this admission
lineage is closed. The lab returns to frontier search rather than adapting the
surface around the observed model.
