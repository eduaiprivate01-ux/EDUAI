# EduAI

EduAI is a Streamlit learning application with a local LangChain RAG pipeline.

## Local setup

The existing Python environment and embedding model are in the sibling `model` folder.
Open PowerShell in `EduAI7` and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install_ai_requirements.ps1
.\download_qwen_gguf.ps1
.\download_handwriting_ocr.ps1
.\download_diagram_model.ps1  # optional; downloads a local vision model once
.\download_reranker.ps1  # optional; downloads once for local reranking
```

The Qwen download is about 4.68 GB. The script resumes a partial download when run again.
Then configure MySQL in `.streamlit/secrets.toml` and start EduAI:

```powershell
.\run_eduai7.ps1
```

The launcher uses `..\model\.venv`, so the embedding and chat dependencies are shared
with the locally downloaded models. `requirements.txt` lists the complete AI/RAG and
database stack for repeatable installation.

## MySQL setup

The application reads `[mysql]` settings from `.streamlit/secrets.toml` or from
`MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DATABASE`.
The configured MySQL 26.7 instance is `127.0.0.1:3308`, database `eduai`. Keep the
Windows Firewall option disabled for this local-only connection. The MySQL service
must be running and the configured account needs privileges on that database. On first
connection, EduAI creates tables for the curriculum, document metadata, chat messages
and feedback, practice sets and scored attempts, and admin events.

After completing MySQL Configurator and starting its Windows service, provision the
EduAI database and application account once from this folder:

```powershell
..\model\.venv\Scripts\python.exe .\setup_mysql_3308.py
```

The script asks for the MySQL root password without displaying it. It creates the
`eduai` database if needed, configures `eduai_app` for both `localhost` and `127.0.0.1`
from the local `[mysql]` settings, and creates the application tables. It does not
erase any existing database.
The former project-managed MySQL instance on port 3307 is left untouched. Its users
and rows are not copied to the new instance; create an Admin account there with
`setup_admin.py` after provisioning.

If there is no Admin account yet, run this from `EduAI7` with the same MySQL settings,
then sign in and add the course structure:

```powershell
..\model\.venv\Scripts\python.exe .\setup_admin.py
```

## Pipeline

1. PDF, DOCX, TXT, and common image uploads are saved under `data/documents`.
2. PyPDF or python-docx extracts selectable text. Scanned PDF pages, standalone
   images, images embedded in PDFs, and images embedded in DOCX are rendered or
   decoded and passed through local TrOCR OCR. PDF figure OCR also runs when the
   surrounding page has selectable text. Recognized labels join the page text before
   chunking and can be reviewed before indexing. When local Ollama and Qwen2.5-VL are
   available, EduAI first checks raster images for diagram-like line geometry and
   counts PDF vector drawing operations while extracting text. It sends only detected
   candidate pages/images to Qwen for descriptions of diagram types, labels, arrows,
   and relationships; other PDF pages are not rendered for vision analysis.
   Those descriptions join page text, so the existing RAG tutor can retrieve and cite
   them. They appear in the editable review before indexing. The `all` value for
   `EDUAI_VISION_PDF_MODE` is retained for older `.env` files but now uses the same
   detected-page filter; it never runs vision over every page. Vision work is capped
   at `EDUAI_VISION_MAX_PAGES` detected pages (20 by default). The lightweight image
   check favors diagrams with clear horizontal and vertical strokes, so unusual
   freehand sketches may not be selected. If Ollama or its model is unavailable,
   selectable text and OCR still work.
   TrOCR processes segmented line images in small batches to limit inference overhead.
   PDF figure line crops are collected across the document and sent in batches
   (8 by default). Set `EDUAI_OCR_BATCH_SIZE=4` in the app's `.env` if memory is
   constrained; larger batches up to 16 may improve throughput when RAM allows.
3. MiniLM's tokenizer sizes overlapping chunks to stay within its input limit.
4. `sentence-transformers/all-MiniLM-L6-v2` embeds each chunk. Chroma stores the
   vectors persistently under `data/chroma` and records the SQL document ID and source
   metadata with every chunk.
5. EduAI stores document ownership, course filters, filenames, and indexing status in
   MySQL. Teacher/admin uploads are shared; student uploads are private to that account.
6. Before indexing, users can inspect and edit extracted page text. Extraction runs in
   background workers and reports percentage, current page/image, elapsed time, and an
   estimated remaining time. DOCX image decoding and line segmentation use bounded
   two-thread preprocessing; model inference remains serialized to limit RAM use.
   Chroma indexing uses one background worker to avoid concurrent SQLite writes. The
   small in-process queue is cleared if Streamlit restarts. Extraction timings and
   throughput are shown on the admin Speed & efficiency page; only counts and timings
   are saved locally, not filenames or extracted content. Set `EDUAI_PREVIEW_WORKERS=1`
   in `.env` on a low-memory machine, or use up to 3 workers when processing independent
   documents concurrently.
7. The tutor retrieves matching shared or user-owned chunks with MiniLM vector search
   and BM25 lexical search, combines their rankings with Reciprocal Rank Fusion (RRF),
   validates access against MySQL, and can apply an optional local Cross-Encoder to a
   bounded candidate pool (12 by default). Download it once with
   `download_reranker.ps1`, then restart Streamlit so the new local model is loaded.
   If reranking is slow, reduce `EDUAI_RERANK_CANDIDATES` or disable the Cross-Encoder;
   MiniLM vector search, BM25, and RRF still run.
   Follow-up retrieval uses the prior topic and answer when a question refers to them;
   recent chat turns are also included in the tutor prompt. Students can choose a detailed
   answer (about 300–450 words), a concise answer, or an on-demand long-form answer (about
   1,150–2,000 words for substantive explanations). Long-form generation can take several
   minutes on a CPU. Students can also choose course-material-only or general tutor mode
   (general tutor is the default). General mode can use Qwen's local
   knowledge to fill gaps and identifies content that is not supported by uploaded excerpts.
   The tutor streams answers and saves source citations in MySQL chat history. Users can
   rate answers helpful or not helpful; admins see aggregate counts. Practice questions
   use the same retrieval path.
8. Students can record their practice score. EduAI schedules the next subject review
   after 1, 2–7, or 7–30 days according to performance and the previous interval, and
   the Practice and Progress pages show due subjects.

To measure retrieval on your course materials, copy
`evaluation/rag_questions.example.jsonl` to `evaluation/rag_questions.jsonl`, replace
the sample IDs with labeled examples, and run:

```powershell
..\model\.venv\Scripts\python.exe .\evaluate_rag.py .\evaluation\rag_questions.jsonl --k 6
```

This reports Recall@k, Precision@k, and MRR. It measures retrieval against your labels;
it does not automatically score answer correctness. Find document IDs for the labels
with `SELECT document_id, title FROM eduai_documents WHERE status = 'ready';` in the EduAI
database, and use the signed-in user's EduAI ID in each example.

To review follow-up handling, answer length, and response timings, run the local tutor
quality cases with a valid EduAI user ID while MySQL is running:

```powershell
..\model\.venv\Scripts\python.exe .\evaluate_tutor.py .\evaluation\tutor_quality.example.jsonl --owner-id EDU-YOUR-ID
```

The evaluator prints each answer, word count, retrieval/generation/first-output times,
and simple required-term checks. Review factual correctness, relevance, and citations
manually; the sample cases use general tutor mode and do not require a specific course
document. Evaluation timings are not added to the normal Speed & efficiency dashboard.

The first handwriting upload requires the local `microsoft/trocr-base-handwritten`
checkpoint downloaded by `download_handwriting_ocr.ps1`. The model targets English
handwriting; recognition quality varies with cursive style, skew, blur, and page
contrast. OCR weights are released after extraction so they do not stay loaded alongside
the Qwen model.

Diagram understanding uses Ollama 0.7.0 or newer as a local image endpoint and the Qwen2.5-VL 3B
vision-language model. Install Ollama once from [ollama.com/download](https://ollama.com/download),
then run `download_diagram_model.ps1` once to pull `qwen2.5vl:3b` (about 3.2 GB).
Ollama must be running on `127.0.0.1:11434` while extracting diagrams. The model is
unloaded after each batch of up to four images, and EduAI serializes vision inference with Qwen and OCR to
reduce peak RAM use. CPU-only diagram analysis can take time. Configure the local
endpoint, model, and detected-page limit in `.env` using the entries in `.env.example`;
set `EDUAI_ENABLE_DIAGRAM_VISION=false` to turn it off. Existing indexed documents need
to be uploaded and indexed again to add their new visual descriptions to Chroma.

The SQL metadata and Chroma vectors are separate stores linked by `document_id`.
Uploaded files, vectors, generated Qwen weights, and secrets are excluded from Git.

## Models and hardware

- Embeddings: `..\model\models\all-MiniLM-L6-v2`
- Chat model: `models\Qwen2.5-7B-Instruct-GGUF\Qwen2.5-7B-Instruct-Q4_K_M.gguf`
- Handwriting OCR: `models\trocr-base-handwritten` (download with `download_handwriting_ocr.ps1`)
- Source model: `Qwen/Qwen2.5-7B-Instruct`, quantized to Q4_K_M for this machine's
  7.7 GiB RAM and CPU-only setup.

The full-precision Qwen folder under `..\model\models` is incomplete and too large for
this machine to load. EduAI uses the 4-bit GGUF build of the same Qwen2.5 7B Instruct
model. Local CPU answers can take time, and long-form answers take substantially longer.
The default 8192-token context supports the optional 3500-token long-form output allowance
while leaving space for source excerpts and chat history. The normal detailed/concise output
limit remains 700 tokens. The long-form limit is automatically reduced when the configured
context is smaller. On a memory-constrained PC, set `EDUAI_CONTEXT_WINDOW=2048` in `.env`;
this keeps normal responses available but makes long-form answers very short. The local Chroma
store is rebuilt only by uploading/indexing documents;
keep `data/chroma` and `data/documents` together.

Optional runtime settings can be copied from `.env.example` to the ignored `.env` file.
EduAI reads that file at startup for both database and AI runtime settings.
`EDUAI_N_GPU_LAYERS=0` keeps Qwen on CPU. Set it to `-1` only after installing a
`llama-cpp-python` build with a GPU backend supported by your hardware; this project
setting does not install GPU drivers or rebuild llama.cpp. The Cross-Encoder defaults
to CPU for compatibility and falls back to hybrid ranking if the optional model is absent.

## Standalone tutor accuracy check

Double-click `Open_Tutor_Accuracy_Check.bat` in Windows Explorer. It opens a separate
EduAI review page at `http://localhost:8502`, without navigating through the regular
dashboard. Sign in with an EduAI account; the page uses that account's existing document
access and the same local model, MySQL database, and Chroma index. MySQL must be running,
and the Qwen GGUF must be downloaded. Keep the PowerShell window open while reviewing;
press Ctrl+C there to stop the page.

The page shows retrieved excerpts, answer citations, latency, expected-phrase checks, and
phrases marked as known errors. These automated checks are screening aids, not proof of
factual accuracy; use the human review controls and compare the answer with its excerpts.
The page does not save review text to the database. Use its download button to save a JSON
report when you want to keep a review.

## Run the app

```powershell
.\run_eduai7.ps1
```

The older `install_mysql.ps1`, `start_mysql.ps1`, `stop_mysql.ps1`, and
`reset_mysql_database.ps1` scripts manage a separate project-local MySQL instance on
port 3307. They are not used by the MySQL Configurator instance on port 3308; do not
run them for this setup. The previous 3307 data remains available for recovery.

Database credentials are stored in ignored local files (`.streamlit/secrets.toml` and `.mysql-*.cnf`). Do not share those files. The MySQL data directory is under `data/`, which is also ignored by Git.
