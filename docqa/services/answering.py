from __future__ import annotations

from dataclasses import dataclass

from docqa.models import Document, Question
from docqa.services.retrieval import retrieve_documents


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    used_document_ids: list[int]


def build_context(question: str, top_k: int = 5) -> tuple[str, list[int]]:
    retrieved = retrieve_documents(question, top_k=top_k, snippets_per_doc=2)
    doc_ids = [r.id for r in retrieved]

    # Build compact context from snippets
    parts: list[str] = []
    for r in retrieved:
        parts.append(f"[Document #{r.id}] {r.title}")
        for snip in r.snippets:
            parts.append(f"- {snip.text}")
        parts.append("")  # spacing

    context = "\n".join(parts).strip()
    return context, doc_ids


def answer_with_langchain_ollama(question: str, context: str, model: str = "phi3:mini") -> str:
    """
    Uses LangChain + Ollama (running in docker-compose as service 'ollama').
    """
    from langchain_community.chat_models import ChatOllama
    from langchain_core.prompts import ChatPromptTemplate

    llm = ChatOllama(base_url="http://ollama:11434", model=model, temperature=0)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful assistant. Answer using ONLY the provided context. "
                "If the answer is not in the context, say: 'I don't know based on the provided documents.' "
                "Be concise and cite which Document numbers you used in one short line at the end.",
            ),
            ("human", "Question:\n{question}\n\nContext:\n{context}\n\nAnswer:"),
        ]
    )

    chain = prompt | llm
    result = chain.invoke({"question": question, "context": context})

    # result is an AIMessage
    return getattr(result, "content", str(result)).strip()


def answer_question(
    question_text: str,
    top_k: int = 5,
    model: str = "phi3:mini",
) -> Question:
    """
    End-to-end: create Question, retrieve docs, generate answer, save.
    """
    question_text = (question_text or "").strip()
    q_obj = Question.objects.create(question_text=question_text)

    context, doc_ids = build_context(question_text, top_k=top_k)

    if doc_ids:
        q_obj.related_documents.set(Document.objects.filter(id__in=doc_ids))

    if not context:
        q_obj.answer_text = "I don't know based on the provided documents."
        q_obj.save(update_fields=["answer_text"])
        return q_obj

    answer = answer_with_langchain_ollama(question_text, context, model=model)
    q_obj.answer_text = answer
    q_obj.save(update_fields=["answer_text"])

    return q_obj


def fill_answer_for_question(
    q_obj: Question,
    top_k: int = 5,
    model: str = "phi3:mini",
) -> Question:
    question_text = (q_obj.question_text or "").strip()
    retrieved = retrieve_documents(question_text, top_k=top_k, snippets_per_doc=2)

    doc_ids = [r.id for r in retrieved]
    if doc_ids:
        q_obj.related_documents.set(Document.objects.filter(id__in=doc_ids))
    else:
        q_obj.related_documents.clear()

    # Build context from snippets
    parts = []
    for r in retrieved:
        parts.append(f"[Document #{r.id}] {r.title}")
        for s in r.snippets:
            parts.append(f"- {s.text}")
        parts.append("")
    context = "\n".join(parts).strip()

    if not context:
        q_obj.answer_text = "I don't know based on the provided documents."
        q_obj.save(update_fields=["answer_text"])
        return q_obj

    # Use your existing Ollama+LangChain call
    from docqa.services.answering import answer_with_langchain_ollama  # (this function already exists in your file)
    answer = answer_with_langchain_ollama(question_text, context, model=model)

    q_obj.answer_text = answer
    q_obj.save(update_fields=["answer_text"])
    return q_obj
