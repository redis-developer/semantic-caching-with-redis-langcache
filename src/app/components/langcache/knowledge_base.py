from __future__ import annotations

from dataclasses import dataclass

from app.components.langcache.embedding import embed_text, cosine_similarity


@dataclass(frozen=True, slots=True)
class KnowledgeBaseEntry:
    prompt: str
    answer: str
    embedding: list[float]


def build_knowledge_base() -> list[KnowledgeBaseEntry]:
    entries = [
        (
            "How do I reset my password?",
            "To reset your password, open account settings, choose Password, and follow the reset link sent to your email.",
        ),
        (
            "Where is my invoice?",
            "You can find invoices in Billing > Documents. The latest receipt is available for download there.",
        ),
        (
            "How do I track my order?",
            "Open Orders, pick the shipment you want, and use the tracking number shown in the order details.",
        ),
    ]

    return [
        KnowledgeBaseEntry(prompt=prompt, answer=answer, embedding=embed_text(prompt))
        for prompt, answer in entries
    ]


KNOWLEDGE_BASE = build_knowledge_base()


def choose_best_knowledge_answer(question: str) -> tuple[KnowledgeBaseEntry | None, float]:
    question_embedding = embed_text(question)
    best_entry: KnowledgeBaseEntry | None = None
    best_similarity = 0.0

    for entry in KNOWLEDGE_BASE:
        similarity = cosine_similarity(question_embedding, entry.embedding)
        if similarity > best_similarity:
            best_similarity = similarity
            best_entry = entry

    return best_entry, best_similarity

