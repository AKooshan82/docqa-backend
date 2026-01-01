from django.contrib import admin
from .models import Document, Tag, Question
from django import forms
from django.contrib import admin, messages
from .models import Question
from docqa.services.answering import fill_answer_for_question

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ("name", "slug")
    list_display = ("name", "slug")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "date", "tag_list", "has_pdf", "short_extracted", "created_at")
    search_fields = ("title", "text", "extracted_text")
    list_filter = ("date", "tags")
    filter_horizontal = ("tags",)
    ordering = ("-created_at",)

    def has_pdf(self, obj):
        return bool(obj.pdf)
    has_pdf.boolean = True
    has_pdf.short_description = "PDF"

    def short_extracted(self, obj):
        preview = (obj.extracted_text or obj.text or "").strip().replace("\n", " ")
        return (preview[:120] + "…") if len(preview) > 120 else preview
    short_extracted.short_description = "Preview"

    def short_text(self, obj: Document) -> str:
        preview = (obj.text or "").strip().replace("\n", " ")
        return (preview[:120] + "…") if len(preview) > 120 else preview

    short_text.short_description = "Preview"

    def tag_list(self, obj: Document) -> str:
        return ", ".join(obj.tags.values_list("name", flat=True))

    tag_list.short_description = "Tags"

class QuestionAdminForm(forms.ModelForm):
    generate_answer_now = forms.BooleanField(
        required=False,
        initial=True,
        help_text="If checked, saving will run retrieval + LLM and fill the answer."
    )
    top_k = forms.IntegerField(required=False, initial=5, min_value=1, max_value=20)
    model = forms.CharField(required=False, initial="phi3:mini")

    class Meta:
        model = Question
        fields = "__all__"


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    form = QuestionAdminForm

    list_display = ("short_question", "has_answer", "created_at", "updated_at")
    search_fields = ("question_text", "answer_text")
    filter_horizontal = ("related_documents",)
    ordering = ("-created_at",)

    # Show answer + sources on the edit page
    readonly_fields = ("created_at", "updated_at")
    fields = (
        "question_text",
        "generate_answer_now",
        "top_k",
        "model",
        "answer_text",
        "related_documents",
        "created_at",
        "updated_at",
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        generate = form.cleaned_data.get("generate_answer_now", False)
        top_k = form.cleaned_data.get("top_k") or 5
        model = (form.cleaned_data.get("model") or "phi3:mini").strip()

        # Only generate if requested and there's no answer yet (prevents overwriting)
        if generate and not (obj.answer_text and obj.answer_text.strip()):
            try:
                fill_answer_for_question(obj, top_k=top_k, model=model)
                self.message_user(request, "Answer generated and saved.", level=messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f"Failed to generate answer: {e}", level=messages.ERROR)

    def short_question(self, obj: Question) -> str:
        q = (obj.question_text or "").strip().replace("\n", " ")
        return (q[:120] + "…") if len(q) > 120 else q
    short_question.short_description = "Question"

    def has_answer(self, obj: Question) -> bool:
        return bool(obj.answer_text and obj.answer_text.strip())
    has_answer.boolean = True
    has_answer.short_description = "Answered"
