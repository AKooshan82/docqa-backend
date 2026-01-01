import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from django.views.decorators.http import require_POST

from docqa.models import Question, Document
from docqa.services.retrieval import retrieve_documents
from docqa.services.answering import answer_question


@csrf_exempt
@require_POST
def retrieve_view(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    question_text = (payload.get("question") or "").strip()
    top_k = int(payload.get("top_k") or 5)

    if not question_text:
        return JsonResponse({"error": "Field 'question' is required"}, status=400)

    retrieved = retrieve_documents(question_text, top_k=top_k)

    # Save Question (answer empty for Day 2)
    q_obj = Question.objects.create(question_text=question_text)

    # Link related documents
    doc_ids = [r.id for r in retrieved]
    if doc_ids:
        q_obj.related_documents.set(Document.objects.filter(id__in=doc_ids))

    return JsonResponse(
        {
            "question_id": q_obj.id,
            "question": question_text,
            "results": [
                {
                    "document_id": r.id,
                    "title": r.title,
                    "score": r.score,
                    "snippets": [{"text": s.text, "score": s.score} for s in r.snippets],
                }
                for r in retrieved
            ],
        }
    )

@csrf_exempt
@require_POST
def ask_view(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    question_text = (payload.get("question") or "").strip()
    top_k = int(payload.get("top_k") or 5)
    model = (payload.get("model") or "phi3:mini").strip()

    if not question_text:
        return JsonResponse({"error": "Field 'question' is required"}, status=400)

    q_obj = answer_question(question_text, top_k=top_k, model=model)

    return JsonResponse(
        {
            "question_id": q_obj.id,
            "question": q_obj.question_text,
            "answer": q_obj.answer_text or "",
            "sources": [
                {"document_id": d.id, "title": d.title}
                for d in q_obj.related_documents.all().only("id", "title")
            ],
        }
    )
