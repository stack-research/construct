"""L1 naive retrieval: recency + similarity, top-k.

Two similarity backends, both recorded in the run_config row:
  embedding_nomic — real embeddings via an OpenAI-compatible /v1/embeddings
                    endpoint (LM Studio serves text-embedding-nomic-embed-text-v1.5).
  lexical_tfidf   — stdlib fallback; DISCLOSED as a fixture when used, since
                    Stage B's embedding-neighbor curriculum constraint needs
                    real embedding geometry.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from .records import Record

DEFAULT_EMBED_URL = "http://localhost:1234/v1"
DEFAULT_EMBED_MODEL = "text-embedding-nomic-embed-text-v1.5"


def _embed(texts: list[str], base_url: str = DEFAULT_EMBED_URL, model: str = DEFAULT_EMBED_MODEL) -> list[list[float]]:
    import json
    import urllib.request

    body = json.dumps({"model": model, "input": texts}).encode()
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/embeddings", data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    items = sorted(data["data"], key=lambda d: d["index"])
    return [d["embedding"] for d in items]


def _cos_dense(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def _tfidf_vectors(docs: list[list[str]]) -> list[dict[str, float]]:
    n = len(docs)
    df: Counter[str] = Counter()
    for doc in docs:
        df.update(set(doc))
    vecs = []
    for doc in docs:
        tf = Counter(doc)
        vec = {t: (c / len(doc)) * math.log((1 + n) / (1 + df[t]) + 1) for t, c in tf.items()} if doc else {}
        vecs.append(vec)
    return vecs


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def pairwise_similarity(texts: list[str], query: str, similarity_backend: str) -> list[float]:
    """Similarity of each text to the query, no recency blend. Used by the
    live-input contention check (SPEC_V1X §1) with the same backend as retrieval."""
    if not texts:
        return []
    if similarity_backend == "embedding_nomic":
        vecs = _embed(texts + [query])
        return [_cos_dense(v, vecs[-1]) for v in vecs[:-1]]
    if similarity_backend == "lexical_tfidf":
        docs = [_tokens(t) for t in texts] + [_tokens(query)]
        tvecs = _tfidf_vectors(docs)
        return [_cosine(v, tvecs[-1]) for v in tvecs[:-1]]
    raise ValueError(f"unknown similarity backend: {similarity_backend}")


def rank_records(
    query: str,
    records: list[Record],
    recency_weight: float = 0.3,
    similarity_backend: str = "lexical_tfidf",
) -> list[tuple[Record, float]]:
    """Score = (1 - w) * similarity + w * recency. Returns all records, ranked."""
    if not records:
        return []
    if similarity_backend == "embedding_nomic":
        vecs = _embed([r.text for r in records] + [query])
        qvec = vecs[-1]
        sims = [_cos_dense(v, qvec) for v in vecs[:-1]]
    elif similarity_backend == "lexical_tfidf":
        docs = [_tokens(r.text) for r in records] + [_tokens(query)]
        tvecs = _tfidf_vectors(docs)
        sims = [_cosine(v, tvecs[-1]) for v in tvecs[:-1]]
    else:
        raise ValueError(f"unknown similarity backend: {similarity_backend}")
    n = len(records)
    scored = []
    for i, r in enumerate(records):
        recency = (i + 1) / n  # store is append-only; later index = more recent
        scored.append((r, (1 - recency_weight) * sims[i] + recency_weight * recency))
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored
