# EFC v2 menu composition rules — SPEC §B

Status: v2 lineage (fork of v1 §2.5.5 mechanics with role-set change).

## Role set

Roles are `{commit, non_commit}` only. There is no `baseline` role; the
four-action menu has two commit-class and two non-commit-class members.

## Mapping rule (relevant fixtures)

Each relevant fixture pins at authoring time:

- `coherent_commit_action` — unique commit-class member from visible task facts
- `coherent_non_commit_action` — unique non-commit-class member from visible facts
- `scope_bit` — `covers` or `misses`

Expected enum:

```text
scope_bit == covers ? coherent_commit_action : coherent_non_commit_action
```

Authoring ties are design errors resolved by rewriting the item, never by
score-time tie-breaks.

## Irrelevant fixtures

`expected_commitment_enum` is pinned directly from visible facts at authoring.

## Mechanical discipline

Inherited from v1 §2.5.5: total, override-free, manifest-recomputable mapping.
All pinned fields enter the fixture hash.
