import math

import streamlit as st

from ai_pipeline import (
    MAX_RERANK_CANDIDATES,
    RRF_RANK_CONSTANT,
    TUTOR_CONTEXT_WINDOW,
    TUTOR_LONG_EFFECTIVE_MAX_NEW_TOKENS,
    TUTOR_LONG_MAX_NEW_TOKENS,
    TUTOR_MAX_NEW_TOKENS,
)
from extraction_metrics import load_recent_extraction_records
from performance_metrics import load_recent_performance
from ui import inject_css, page_header, sidebar


st.set_page_config(page_title="EduAI | Speed & Efficiency", page_icon="⚡", layout="wide")
inject_css()
if not st.session_state.get("authenticated"):
    st.switch_page("pages/1_Login.py")
    st.stop()
if st.session_state.get("role") != "Admin":
    st.switch_page("app.py")
    st.stop()

sidebar()
page_header(
    "Speed & efficiency",
    "Local measurements for tutor response and document extraction throughput.",
)

if st.button("Refresh results", icon=":material/refresh:"):
    st.rerun()

records = load_recent_performance(500)
extraction_records = load_recent_extraction_records(500)
st.caption(
    f"RRF rank constant: {RRF_RANK_CONSTANT} · "
    f"Reranker candidate limit: {MAX_RERANK_CANDIDATES} · "
    f"Context window: {TUTOR_CONTEXT_WINDOW:,} tokens · "
    f"Output limits: detailed/concise {TUTOR_MAX_NEW_TOKENS:,}, "
    f"long-form {TUTOR_LONG_EFFECTIVE_MAX_NEW_TOKENS:,} of "
    f"{TUTOR_LONG_MAX_NEW_TOKENS:,} tokens configured · "
    "Only timings, answer-length counts, and mode flags are saved; question and answer text are not recorded."
)

if not records:
    st.info("No timing records yet. Ask a question in AI Tutor, then refresh this page.")


def values_for(field):
    return [
        float(record[field])
        for record in records
        if isinstance(record.get(field), (int, float))
    ]


def percentile(values, percent):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percent / 100 * len(ordered)) - 1))
    return ordered[index]


retrieval_times = values_for("retrieval_ms")
reranker_times = values_for("reranker_ms")
generation_times = values_for("generation_ms")
first_output_times = values_for("first_output_ms")
response_words = values_for("response_words")
total_times = values_for("total_ms")

summary = st.columns(5)
summary[0].metric("Measured requests", len(records))
summary[1].metric(
    "Mean retrieval",
    f"{sum(retrieval_times) / len(retrieval_times):.0f} ms" if retrieval_times else "—",
)
summary[2].metric(
    "Mean first output",
    f"{sum(first_output_times) / len(first_output_times) / 1000:.2f} s"
    if first_output_times else "—",
)
summary[3].metric(
    "Mean generation",
    f"{sum(generation_times) / len(generation_times) / 1000:.2f} s" if generation_times else "—",
)
summary[4].metric(
    "P95 total answer time",
    f"{percentile(total_times, 95) / 1000:.2f} s" if total_times else "—",
)

details = st.columns(4)
details[0].metric(
    "P95 retrieval",
    f"{percentile(retrieval_times, 95):.0f} ms" if retrieval_times else "—",
)
details[1].metric(
    "Mean vector search",
    f"{sum(values_for('vector_search_ms')) / len(values_for('vector_search_ms')):.0f} ms"
    if values_for("vector_search_ms") else "—",
)
details[2].metric(
    "Mean reranker",
    f"{sum(reranker_times) / len(reranker_times):.0f} ms" if reranker_times else "—",
)
details[3].metric(
    "Mean answer length",
    f"{sum(response_words) / len(response_words):.0f} words" if response_words else "—",
)

chart_rows = []
for index, record in enumerate(reversed(records), start=1):
    chart_rows.append({
        "Request": index,
        "Retrieval (ms)": float(record.get("retrieval_ms", 0) or 0),
        "Reranker (ms)": float(record.get("reranker_ms", 0) or 0),
        "First output (ms)": float(record.get("first_output_ms", 0) or 0),
        "Generation (ms)": float(record.get("generation_ms", 0) or 0),
        "Total (ms)": float(record.get("total_ms", 0) or 0),
    })

st.markdown("#### Recent latency trend")
if chart_rows:
    st.line_chart(chart_rows, x="Request", y=[
        "Retrieval (ms)", "Reranker (ms)", "First output (ms)", "Generation (ms)", "Total (ms)",
    ])

st.markdown("#### Recent requests")
table_rows = []
for record in records:
    table_rows.append({
        "Time (UTC)": record.get("timestamp_utc", ""),
        "Status": record.get("status", ""),
        "Retrieval (ms)": record.get("retrieval_ms", 0),
        "Vector search (ms)": record.get("vector_search_ms", 0),
        "BM25 + RRF (ms)": record.get("fusion_ms", 0),
        "Reranker (ms)": record.get("reranker_ms", 0),
        "First output (ms)": record.get("first_output_ms", 0),
        "Generation (ms)": record.get("generation_ms", 0),
        "Answer words": record.get("response_words", 0),
        "Output cap (tokens)": record.get("max_output_tokens", 0),
        "Characters / second": record.get("characters_per_second", 0),
        "Total (ms)": record.get("total_ms", 0),
        "Answer style": record.get("answer_style", ""),
        "Knowledge mode": record.get("knowledge_mode", ""),
        "History provided": record.get("conversation_context_used", False),
        "Contextual search query": record.get("contextual_retrieval_used", False),
        "Chunks returned": record.get("retrieved_chunks", 0),
        "Reranker used": record.get("reranker_used", False),
    })
st.dataframe(table_rows, hide_index=True, use_container_width=True)
st.caption(
    "The first output time measures how long until the first streamed text appears. The first request can include model-load time. Compare several requests after the models are warm. "
    "Reranker timing includes model initialization when it is first loaded."
)
with st.expander("How to use these measurements"):
    st.markdown(
        "- High **retrieval** time points to vector search, SQL access validation, or reranking. "
        "Compare vector search and reranker columns before changing top-k or the reranker limit.\n"
        "- High **first output** time with low retrieval time points to model startup, CPU/GPU inference, or waiting for the local inference lock.\n"
        "- Detailed answers generate more text and naturally take longer. Compare requests with the same answer style and knowledge mode.\n"
        "- The reranker candidate limit is now 12 by default. If reranking dominates, try 8 or disable the reranker; MiniLM, BM25, and RRF remain active.\n"
        "- Increase the reranker limit only if quality evaluation shows relevant passages are being missed. If generation dominates, supported GPU offload or a smaller local model can help; reducing output length also reduces time."
    )

st.divider()
st.markdown("### Document extraction throughput")
st.caption(
    "Measures the review extraction step, including OCR and diagram analysis. "
    "The local log stores file type, byte count, timings, and character/page counts; it does not store filenames, extracted text, or account IDs."
)

if not extraction_records:
    st.info("No extraction measurements yet. Extract a document for review, then refresh this page.")
else:
    extraction_durations = [
        float(record.get("duration_ms", 0) or 0)
        for record in extraction_records
        if isinstance(record.get("duration_ms"), (int, float))
    ]
    extraction_pages_per_second = [
        float(record.get("pages_per_second", 0) or 0)
        for record in extraction_records
        if isinstance(record.get("pages_per_second"), (int, float))
        and float(record.get("page_count", 0) or 0) > 0
    ]
    extraction_mb_per_second = [
        float(record.get("megabytes_per_second", 0) or 0)
        for record in extraction_records
        if isinstance(record.get("megabytes_per_second"), (int, float))
    ]
    extraction_summary = st.columns(4)
    extraction_summary[0].metric("Measured documents", len(extraction_records))
    extraction_summary[1].metric(
        "Mean extraction time",
        f"{sum(extraction_durations) / len(extraction_durations) / 1000:.2f} s"
        if extraction_durations else "—",
    )
    extraction_summary[2].metric(
        "Mean page throughput",
        f"{sum(extraction_pages_per_second) / len(extraction_pages_per_second):.2f} pages/s"
        if extraction_pages_per_second else "—",
    )
    extraction_summary[3].metric(
        "Mean file throughput",
        f"{sum(extraction_mb_per_second) / len(extraction_mb_per_second):.3f} MB/s"
        if extraction_mb_per_second else "—",
    )

    extraction_chart = []
    for index, record in enumerate(reversed(extraction_records), start=1):
        extraction_chart.append({
            "Document": index,
            "Duration (s)": float(record.get("duration_ms", 0) or 0) / 1000,
            "Pages per second": float(record.get("pages_per_second", 0) or 0),
            "MB per second": float(record.get("megabytes_per_second", 0) or 0),
        })
    st.markdown("#### Recent extraction throughput")
    st.line_chart(extraction_chart, x="Document", y=[
        "Duration (s)", "Pages per second", "MB per second",
    ])

    extraction_table = []
    for record in extraction_records:
        stages = record.get("stage_durations_ms") or {}
        extraction_table.append({
            "Time (UTC)": record.get("timestamp_utc", ""),
            "Status": record.get("status", ""),
            "File type": record.get("file_type", ""),
            "Size (MB)": round(float(record.get("file_size_bytes", 0) or 0) / (1024 * 1024), 2),
            "Elapsed (s)": round(float(record.get("duration_ms", 0) or 0) / 1000, 2),
            "Pages/items": record.get("page_count", 0),
            "Characters": record.get("character_count", 0),
            "Pages/s": record.get("pages_per_second", 0),
            "MB/s": record.get("megabytes_per_second", 0),
            "Stage times (ms)": ", ".join(
                f"{name}: {duration:.0f}"
                for name, duration in stages.items()
                if isinstance(duration, (int, float))
            ),
        })
    st.dataframe(extraction_table, hide_index=True, use_container_width=True)
