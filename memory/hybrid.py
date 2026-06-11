"""Hybrid retrieval：BM25 + local sentence-transformers embedding similarity.

注意：
- 不修改 bm25_search()，保留純 BM25 給公開/隱藏測試。
- 這個檔案提供任務二用的 hybrid_search()。
- embedding 使用本地 sentence-transformers；第一次執行會下載模型，之後使用本機快取。
"""
from __future__ import annotations

import math
import os
from functools import lru_cache

from .bm25 import bm25_search


DEFAULT_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer

    model_name = os.environ.get("PI_MEMORY_EMBEDDING_MODEL", DEFAULT_MODEL_NAME)
    return SentenceTransformer(model_name)


def _cosine_similarity(a, b) -> float:
    a = [float(x) for x in a]
    b = [float(y) for y in b]

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def _normalize_scores(score_by_id: dict[str, float]) -> dict[str, float]:
    if not score_by_id:
        return {}

    values = list(score_by_id.values())
    min_score = min(values)
    max_score = max(values)

    if max_score == min_score:
        return {doc_id: 0.0 for doc_id in score_by_id}

    return {
        doc_id: (score - min_score) / (max_score - min_score)
        for doc_id, score in score_by_id.items()
    }


def hybrid_search(
    query: str,
    docs: list[dict],
    k: int = 8,
    alpha: float = 0.6,
) -> list[dict]:
    """Return top-k docs using a weighted BM25 + embedding score.

    Args:
        query: user query.
        docs: [{"id": str, "text": str}, ...].
        k: number of results.
        alpha: BM25 weight. 0.6 means 60% BM25 + 40% embedding.

    Returns:
        [{"id": str, "score": float, "bm25_score": float, "embedding_score": float}, ...]
    """
    if not docs or k <= 0:
        return []

    # 1. Pure BM25 score for every document.
    bm25_results = bm25_search(query, docs, len(docs))
    bm25_by_id = {row["id"]: row["score"] for row in bm25_results}
    normalized_bm25 = _normalize_scores(bm25_by_id)

    # 2. Embedding cosine similarity for every document.
    model = _get_model()
    texts = [doc.get("text", "") for doc in docs]

    embeddings = model.encode([query, *texts], convert_to_numpy=False)
    query_embedding = embeddings[0]
    doc_embeddings = embeddings[1:]

    embedding_by_id = {}
    for doc, doc_embedding in zip(docs, doc_embeddings):
        embedding_by_id[doc["id"]] = _cosine_similarity(query_embedding, doc_embedding)

    normalized_embedding = _normalize_scores(embedding_by_id)

    # 3. Weighted hybrid score.
    results = []
    for index, doc in enumerate(docs):
        doc_id = doc["id"]
        bm25_score = normalized_bm25.get(doc_id, 0.0)
        embedding_score = normalized_embedding.get(doc_id, 0.0)
        hybrid_score = alpha * bm25_score + (1 - alpha) * embedding_score

        results.append({
            "id": doc_id,
            "score": hybrid_score,
            "bm25_score": bm25_by_id.get(doc_id, 0.0),
            "embedding_score": embedding_by_id.get(doc_id, 0.0),
            "_index": index,
        })

    # Python sort is stable, but include index explicitly for deterministic tie handling.
    results.sort(key=lambda row: (-row["score"], row["_index"]))

    for row in results:
        row.pop("_index", None)

    return results[:k]