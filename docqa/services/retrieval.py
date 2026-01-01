from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from docqa.models import Document


@dataclass(frozen=True)
class RetrievedSnippet:
    text: str
    score: float


@dataclass(frozen=True)
class RetrievedDoc:
    id: int
    title: str
    score: float
    snippets: list[RetrievedSnippet]


def _normalize_ws(s: str) -> str:
    return " ".join((s or "").split())


def _doc_text_for_index(title: str, text: str) -> str:
    # Lightly weight title by repeating it
    title = _normalize_ws(title)
    body = text or ""
    return f"{title}\n{title}\n{body}"


def _split_into_chunks(text: str) -> list[str]:
    # Paragraph-ish chunks
    raw = [t.strip() for t in (text or "").split("\n\n")]
    chunks = [c for c in raw if c]
    return chunks if chunks else [text or ""]


def retrieve_documents(
    question: str,
    top_k: int = 5,
    snippets_per_doc: int = 2,
    max_chunk_chars: int = 450,
) -> list[RetrievedDoc]:
    question = (question or "").strip()
    if not question:
        return []

    docs = list(Document.objects.all().only("id", "title", "text"))
    if not docs:
        return []

    corpus = [_doc_text_for_index(d.title, d.extracted_text or d.text or "") for d in docs]


    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=50000)
    X = vectorizer.fit_transform(corpus)
    q = vectorizer.transform([question])

    sims = cosine_similarity(X, q).ravel()
    if sims.size == 0:
        return []

    top_idx = np.argsort(-sims)[:top_k]

    results: list[RetrievedDoc] = []
    for i in top_idx:
        d = docs[int(i)]
        d_score = float(sims[int(i)])

        # Snippet scoring using same vectorizer vocabulary
        chunks = _split_into_chunks(d.extracted_text or d.text or "")
        chunk_vecs = vectorizer.transform(chunks)
        chunk_sims = cosine_similarity(chunk_vecs, q).ravel()

        best_idx = np.argsort(-chunk_sims)[:snippets_per_doc]
        snippets: list[RetrievedSnippet] = []
        for ci in best_idx:
            raw = _normalize_ws(chunks[int(ci)])
            if len(raw) > max_chunk_chars:
                raw = raw[:max_chunk_chars].rstrip() + "…"
            snippets.append(RetrievedSnippet(text=raw, score=float(chunk_sims[int(ci)])))

        results.append(
            RetrievedDoc(
                id=d.id,
                title=d.title,
                score=d_score,
                snippets=snippets,
            )
        )

    return results
