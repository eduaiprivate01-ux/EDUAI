# EduAI data contracts for future API routes

The SQL and vector helpers now return validated dictionaries and lists that can be
passed to a JSON response layer. Pydantic schemas live in `api_schemas.py`; their
`model_dump(mode="json")` serialization converts MySQL timestamps to ISO-8601
strings and excludes non-JSON Python objects.

## SQL records

The following reads return consistent JSON-safe records:

- `catalog_records()` -> `list[CatalogRecord]`
- `list_documents(owner_eduai_id, role, **filters)` -> `list[DocumentRecord]`
- `document_record(document_id)` -> `StoredDocumentRecord | None` for internal service use
- `list_chat_sessions(owner_eduai_id)` -> `list[ChatSession]`
- `get_chat_messages(session_id, owner_eduai_id)` -> `list[ChatMessage]`
- `list_practice_sessions(owner_eduai_id)` -> `list[PracticeSession]`
- `get_admin_metrics()` -> `AdminMetrics`
- `list_admin_events(limit=100)` -> `list[AdminEvent]`

The document-list response intentionally omits local `storage_path` and `mime_type`.
`document_record()` includes those fields because deletion and file operations need
them; keep that internal record out of public API responses.

## Vector search

Use `search_vector_chunks(question, owner_eduai_id, role, context=None, limit=6)`
when an API needs retrieval results. It applies the same document visibility and
course filters as the RAG tutor and returns a JSON-safe `VectorSearchResponse`:

```json
{
  "query": "What is supervised learning?",
  "collection": "eduai_course_materials",
  "result_count": 1,
  "results": [
    {
      "id": "document-uuid:0",
      "rank": 1,
      "content": "Retrieved text chunk...",
      "distance": 0.18,
      "metadata": {"document_id": "document-uuid", "chunk_index": 0},
      "citation": {
        "document_id": "document-uuid",
        "title": "Study material",
        "original_filename": "notes.pdf",
        "page": 2
      }
    }
  ]
}
```

`distance` is Chroma's similarity-search distance; lower values indicate closer
matches. It is not a probability or a calibrated 0-to-1 relevance score. The
existing `retrieve_documents()` function continues returning LangChain `Document`
objects for internal RAG prompt construction. Existing Streamlit features can keep
using their current dictionary keys.

Vector search requests are limited to 4,000 characters and at most 50 returned
results. Search candidates are rechecked against ready SQL document records and
their owner/visibility/context filters before being returned. The SQL check only
loads candidate IDs rather than every visible document record.

## Ingestion resource limits

Uploads remain capped at 50 MB. Extraction additionally allows at most 1,000,000
characters, 500 PDF pages, 40 MiB of expanded DOCX package data, 10,000 DOCX archive
entries, 100,000 DOCX text blocks, and 5,000 chunks per document. Chunks are embedded
and written in batches of 64 to keep peak embedding memory bounded.

Handwriting OCR runs before chunking and embedding. It processes at most 50 scanned
PDF pages, 25 embedded DOCX images, 80 detected text lines per page/image, and 1,500
lines per document; each rendered page or uploaded image is capped at 20 million
pixels. OCR output shares the 1,000,000-character extraction limit. TrOCR weights are
loaded locally only while OCR is running and must first be downloaded with
`download_handwriting_ocr.ps1`.
