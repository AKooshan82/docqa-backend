from django.db import models
from django.utils.text import slugify


class Tag(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Document(models.Model):
    title = models.CharField(max_length=255)
    pdf = models.FileField(upload_to="pdfs/", blank=True, null=True)
    text = models.TextField(blank=True, default="")  # optional manual notes
    extracted_text = models.TextField(blank=True, default="")
    date = models.DateField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="documents")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.title
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # If a PDF exists and we don't have extracted text yet, extract it once.
        if self.pdf and (is_new or not self.extracted_text.strip()):
            from docqa.services.pdf_extract import extract_pdf_text

            try:
                text = extract_pdf_text(self.pdf.path)
            except Exception:
                text = ""

            # Avoid recursion by updating via queryset
            Document.objects.filter(pk=self.pk).update(extracted_text=text)


class Question(models.Model):
    question_text = models.TextField()
    answer_text = models.TextField(blank=True, null=True)
    related_documents = models.ManyToManyField(Document, blank=True, related_name="questions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.question_text[:60]
