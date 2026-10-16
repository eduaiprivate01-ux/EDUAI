"""Standalone local review page for EduAI tutor answers."""

import json
import re
from datetime import datetime, timezone

import streamlit as st

from ai_pipeline import (
    TUTOR_LONG_EFFECTIVE_MAX_NEW_TOKENS,
    _contextual_retrieval_query,
    retrieve_documents,
    stream_answer,
)
from auth import authenticate_user
from education_data import catalog_values


st.set_page_config(
    page_title="EduAI | Tutor accuracy check",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("EduAI tutor accuracy check")
st.caption(
    "Standalone Windows review page. It runs the same local tutor pipeline and shows the "
    "retrieved excerpts beside the answer."
)
st.info(
    "Automated checks find missing expected phrases, unwanted phrases, and citation problems. "
    "They do not prove factual accuracy; compare the answer with the excerpts and record a human review."
)


def _lines(value):
    return [line.strip() for line in str(value or "").splitlines() if line.strip()]


def _word_count(value):
    return len(re.findall(r"\b[\w’'-]+\b", str(value or "")))


def _check_answer(answer, citations, source_count, expected_points, forbidden_phrases, knowledge_mode):
    folded_answer = answer.casefold()
    missing_points = [point for point in expected_points if point.casefold() not in folded_answer]
    forbidden_found = [phrase for phrase in forbidden_phrases if phrase.casefold() in folded_answer]
    cited_numbers = sorted({int(number) for number in re.findall(r"\[Source\s+(\d+)\]", answer, re.IGNORECASE)})
    invalid_citations = [number for number in cited_numbers if number > len(citations)]
    issues = []

    if not answer.strip():
        issues.append("The tutor returned an empty answer.")
    if source_count == 0 and knowledge_mode == "course_material":
        issues.append("No course excerpts were retrieved, so a source-grounded answer could not be checked.")
    elif source_count == 0:
        issues.append("No course excerpts were retrieved; check this general-knowledge answer against a trusted reference.")
    if missing_points:
        issues.append("Missing expected phrases: " + ", ".join(missing_points))
    if forbidden_found:
        issues.append("Found phrases marked as incorrect: " + ", ".join(forbidden_found))
    if cited_numbers and invalid_citations:
        issues.append("Citation numbers have no matching source: " + ", ".join(map(str, invalid_citations)))
    if source_count and not cited_numbers:
        issues.append("Retrieved course material was available, but the answer has no [Source N] citation.")

    return {
        "passed_basic_checks": not issues,
        "issues": issues,
        "missing_expected_phrases": missing_points,
        "forbidden_phrases_found": forbidden_found,
        "citation_numbers": cited_numbers,
        "unmatched_citation_numbers": invalid_citations,
        "answer_words": _word_count(answer),
        "source_count": source_count,
    }


def _login_panel():
    with st.form("tutor_qa_login"):
        st.subheader("Sign in to review your accessible course material")
        identity = st.text_input("Email or EduAI ID")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary")
    if submitted:
        try:
            user = authenticate_user(identity, password)
        except Exception as error:
            st.error(f"Could not connect to EduAI/MySQL: {error}")
            return
        if user:
            st.session_state.tutor_qa_user = user
            st.session_state.tutor_qa_history = []
            st.rerun()
        st.error("Sign-in failed. Check the account, password, and account status.")


if not st.session_state.get("tutor_qa_user"):
    _login_panel()
    st.stop()

user = st.session_state.tutor_qa_user
account_columns = st.columns([5, 1])
account_columns[0].caption(f"Signed in as {user['name']} · {user['role']} · {user['id']}")
if account_columns[1].button("Sign out"):
    for key in ("tutor_qa_user", "tutor_qa_history", "tutor_qa_result"):
        st.session_state.pop(key, None)
    st.rerun()

if "tutor_qa_history" not in st.session_state:
    st.session_state.tutor_qa_history = []

if st.button("＋ New review conversation"):
    st.session_state.tutor_qa_history = []
    st.session_state.pop("tutor_qa_result", None)
    st.rerun()

try:
    courses = catalog_values("Course")
    selected_course = st.selectbox("Course", ["All courses", *courses], key="tutor_qa_course")
    course = "" if selected_course == "All courses" else selected_course
    semesters = catalog_values("Semester", course=course) if course else []
    selected_semester = st.selectbox(
        "Semester", ["All semesters", *semesters], key=f"tutor_qa_semester_{selected_course}",
    )
    semester = "" if selected_semester == "All semesters" else selected_semester
    subjects = catalog_values("Subject", course=course, semester=semester) if course and semester else []
    selected_subject = st.selectbox(
        "Subject", ["All subjects", *subjects], key=f"tutor_qa_subject_{selected_course}_{selected_semester}",
    )
    subject = "" if selected_subject == "All subjects" else selected_subject
except Exception as error:
    st.error(f"Could not load the course filters from MySQL: {error}")
    st.stop()

context = {"course": course, "semester": semester, "subject": subject}
form_columns = st.columns(2)
answer_style_label = form_columns[0].selectbox(
    "Answer length",
    ["Detailed (about 300–450 words)", "Concise", "Long-form (up to 3,500 tokens)"],
    key="tutor_qa_answer_style",
)
answer_style = (
    "long_form" if answer_style_label.startswith("Long-form")
    else "detailed" if answer_style_label.startswith("Detailed")
    else "concise"
)
if answer_style == "long_form":
    st.caption(
        f"Long-form output is capped at {TUTOR_LONG_EFFECTIVE_MAX_NEW_TOKENS:,} tokens "
        "with the current context setting and may take several minutes on CPU."
    )

knowledge_label = form_columns[1].selectbox(
    "Knowledge source",
    ["Course materials only", "General tutor (may use model knowledge)"],
    index=0,
    key="tutor_qa_knowledge_mode",
)
knowledge_mode = "course_material" if knowledge_label == "Course materials only" else "general"

with st.form("tutor_accuracy_check_form"):
    question = st.text_area("Question to test", height=100)
    expected_text = st.text_area(
        "Expected key phrases or facts (one per line, optional)", height=100,
    )
    forbidden_text = st.text_area(
        "Phrases that indicate a known error (one per line, optional)", height=80,
    )
    run_check = st.form_submit_button("Generate answer and check", type="primary")

if run_check:
    if not question.strip():
        st.error("Enter a question to check.")
    else:
        expected_points = _lines(expected_text)
        forbidden_phrases = _lines(forbidden_text)
        history = list(st.session_state.tutor_qa_history)
        retrieval_query, _used_contextual_query = _contextual_retrieval_query(question, history)
        try:
            with st.spinner("Retrieving course excerpts and generating the tutor answer..."):
                evidence_documents = retrieve_documents(
                    retrieval_query, user["id"], user["role"], context=context, limit=6,
                )
                chunks, citations, metrics = stream_answer(
                    question,
                    user["id"],
                    user["role"],
                    context=context,
                    history=history,
                    answer_style=answer_style,
                    knowledge_mode=knowledge_mode,
                )
                answer = st.write_stream(chunks)
            evidence = []
            for document in evidence_documents:
                metadata = dict(document.metadata or {})
                evidence.append({
                    "title": metadata.get("title") or metadata.get("original_filename") or "Study material",
                    "page": metadata.get("page"),
                    "text": document.page_content,
                })
            checks = _check_answer(
                answer, citations, len(evidence), expected_points, forbidden_phrases, knowledge_mode,
            )
            result = {
                "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
                "account_id": user["id"],
                "role": user["role"],
                "question": question.strip(),
                "answer": answer,
                "answer_style": answer_style,
                "knowledge_mode": knowledge_mode,
                "course_filter": context,
                "expected_points": expected_points,
                "forbidden_phrases": forbidden_phrases,
                "checks": checks,
                "citations": citations,
                "retrieved_excerpts": evidence,
                "timings": {
                    key: metrics.get(key)
                    for key in ("retrieval_ms", "first_output_ms", "generation_ms", "total_ms", "response_words")
                },
                "human_review": {"verdict": "Not reviewed", "notes": ""},
            }
            st.session_state.pop("tutor_qa_human_verdict", None)
            st.session_state.pop("tutor_qa_review_notes", None)
            st.session_state.tutor_qa_result = result
            st.session_state.tutor_qa_history = history + [
                {"role": "user", "content": question.strip()},
                {"role": "assistant", "content": answer},
            ]
        except Exception as error:
            st.error(f"Tutor generation or retrieval failed: {error}")

result = st.session_state.get("tutor_qa_result")
if result:
    st.divider()
    if result["checks"]["passed_basic_checks"]:
        st.success("Basic checks passed. Review the source excerpts before treating the answer as accurate.")
    else:
        st.warning("Potential issues found. Review the checklist and compare the answer against its sources.")

    summary_columns = st.columns(4)
    summary_columns[0].metric("Answer length", f"{result['checks']['answer_words']:,} words")
    summary_columns[1].metric("Retrieved excerpts", result["checks"]["source_count"])
    summary_columns[2].metric("Inline citations", len(result["checks"]["citation_numbers"]))
    summary_columns[3].metric(
        "Basic check", "Pass" if result["checks"]["passed_basic_checks"] else "Review",
    )

    for issue in result["checks"]["issues"]:
        st.error(issue)

    answer_column, source_column = st.columns([1.25, 1])
    with answer_column:
        st.subheader("Tutor answer")
        st.markdown(result["answer"] or "_(No answer text returned.)_")
        timings = result.get("timings", {})
        timing_labels = [
            f"{label}: {timings[key] / 1000:.1f}s"
            for key, label in (("retrieval_ms", "Retrieval"), ("first_output_ms", "First output"),
                               ("generation_ms", "Generation"), ("total_ms", "Total"))
            if isinstance(timings.get(key), (int, float))
        ]
        if timing_labels:
            st.caption(" · ".join(timing_labels))
    with source_column:
        st.subheader("Retrieved source excerpts")
        if not result["retrieved_excerpts"]:
            st.info("No indexed excerpt matched this filter and question.")
        for index, excerpt in enumerate(result["retrieved_excerpts"], start=1):
            location = f", page {excerpt['page']}" if excerpt.get("page") else ""
            with st.expander(f"[Source {index}] {excerpt['title']}{location}", expanded=index == 1):
                st.write(excerpt["text"])

    st.subheader("Human accuracy review")
    verdict = st.radio(
        "Does the answer accurately match the evidence and question?",
        ["Not reviewed", "Accurate", "Needs correction", "Incorrect"],
        horizontal=True,
        key="tutor_qa_human_verdict",
    )
    review_notes = st.text_area(
        "Describe any factual error, missing detail, or citation problem",
        key="tutor_qa_review_notes",
    )
    result["human_review"] = {"verdict": verdict, "notes": review_notes.strip()}
    st.session_state.tutor_qa_result = result
    report = json.dumps(result, ensure_ascii=False, indent=2)
    file_time = datetime.now().strftime("%Y%m%d-%H%M%S")
    st.download_button(
        "Download accuracy/error report",
        data=report,
        file_name=f"eduai-tutor-review-{file_time}.json",
        mime="application/json",
    )
