````markdown
# DocQA Backend (Django Admin + Retrieval + LLM Q&A)

A Django backend that lets you manage **Documents**, **Tags**, and **Questions** in the **Django Admin panel**, retrieve relevant documents for a question (TF-IDF), and generate an answer using an LLM (LangChain + Ollama).

## Features

- **Django Admin panel** for:
  - Documents (title, text, date, tags) with searchable/filterable list + preview
  - Tags
  - Questions (store question + generated answer + linked documents)
- **Retrieval (Day 2)**: TF-IDF ranking over document content
- **LLM Answering (Day 3)**: question → retrieve context → LangChain → Ollama model → save answer
- **API endpoints**:
  - `POST /api/retrieve/` → returns top relevant docs + snippets (and creates a Question linked to sources)
  - `POST /api/ask/` → returns answer + sources (and saves answer in DB)

> Optional: PDF upload/extraction can be added if enabled in your version, but the core project uses document text stored in the database.

---

## Requirements

- Docker Desktop installed and running
- Docker Compose available (`docker compose version` should work)

---

## Quick Start (Run the project)

From the repository root (where `docker-compose.yml` is):

1) **Build and start**
```bash
docker compose up -d --build
````

2. **Run migrations**

```bash
docker compose run --rm web python manage.py migrate
```

3. **Create an admin user**

```bash
docker compose run --rm web python manage.py createsuperuser
```

4. Open:

* Admin panel: **[http://localhost:8000/admin/](http://localhost:8000/admin/)**

---

## Stopping and restarting later

* Stop (keeps containers):

```bash
docker compose stop
```

* Start again:

```bash
docker compose up -d
```

* Stop + remove containers (safe if DB/media are persisted via volumes):

```bash
docker compose down
```

---

## Working with the Admin Panel

### 1) Add Tags

Admin → **Tags** → Add:

* Example: `policy`, `finance`

### 2) Add Documents

Admin → **Documents** → Add:

* `title`: Document name
* `text`: Document content (used for retrieval/answers)
* `date`: optional
* `tags`: optional

The Documents list supports:

* searching by title/text
* filtering by date/tags
* preview snippet in list view

### 3) Ask questions and generate answers in Admin

Admin → **Questions** → Add:

* `question_text`: your question

Depending on your configuration, you may have one of these flows:

**A) Generate in Admin (recommended)**

* Check **Generate answer now** (if present)
* Save
* The answer is generated and stored in `answer_text`
* Related source documents are linked automatically

**B) Generate via API and view in Admin**

* Use `/api/ask/` (see below)
* Then check the new Question record in admin

---

## API Usage

### 1) Retrieve documents (no LLM answer)

Creates a Question record and links relevant documents.

```bash
curl -X POST http://localhost:8000/api/retrieve/ \
  -H "Content-Type: application/json" \
  -d '{"question":"What does the policy say about compliance?", "top_k": 5}'
```

Response includes:

* `question_id`
* ranked document results with similarity scores
* snippet text per document

### 2) Ask and generate an answer (retrieval + LLM)

Creates a Question, retrieves top docs, generates an answer, and saves it.

```bash
curl -X POST http://localhost:8000/api/ask/ \
  -H "Content-Type: application/json" \
  -d '{"question":"What does the policy say about compliance?", "top_k": 5, "model":"phi3:mini"}'
```

Response includes:

* `question_id`
* `answer`
* `sources` (linked documents)

---

## Ollama (LLM) Setup

This project uses **Ollama** as a local “free/open” model runner.

### 1) Ensure Ollama service is running

```bash
docker compose ps
```

You should see both `web` and `ollama` services running (if included in your compose file).

### 2) Pull a model (example: phi3:mini)

```bash
docker compose exec ollama ollama pull phi3:mini
docker compose exec ollama ollama list
```

If you use a different model name, pass it in the `/api/ask/` request as `"model"`.

---

## Sample Data (Optional)

If a fixture exists in `fixtures/sample.json`, you can load it:

```bash
docker compose run --rm web python manage.py loaddata fixtures/sample.json
```

> Note: fixtures may require timestamps for `created_at` / `updated_at` fields depending on how they were created.

---

## Troubleshooting

### Admin doesn’t load

Check container logs:

```bash
docker compose logs -f web
```

A common cause is an Admin configuration error (e.g., `list_display` references a missing method).

### 403 CSRF when calling API

If you call endpoints using `curl`, CSRF can block POST requests unless the endpoint is CSRF-exempt.
This project’s API endpoints are typically decorated with `@csrf_exempt` for local dev/testing.

### Ollama errors / model not found

* Confirm Ollama is running:

```bash
docker compose ps
```

* Confirm model exists:

```bash
docker compose exec ollama ollama list
```

* Pull the model:

```bash
docker compose exec ollama ollama pull phi3:mini
```

---

## Project Structure (high level)

```
config/                 Django project settings + URLs
docqa/                  Main app (models/admin/services/views)
docqa/services/
  retrieval.py          TF-IDF retrieval + snippet selection
  answering.py          LangChain + Ollama answering pipeline
fixtures/               Optional sample data
docker-compose.yml      Dev runtime
Dockerfile              App container build
```
