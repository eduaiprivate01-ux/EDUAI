"""Run sample tutor conversations and report length and latency for manual review."""

import argparse
import json
import re
from pathlib import Path

from ai_pipeline import stream_answer


def _word_count(text):
    return len(re.findall(r"\b[\w’'-]+\b", text or ""))


def _read_cases(path):
    cases = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON on line {line_number}: {error}") from error
        if not isinstance(case, dict) or not isinstance(case.get("turns"), list) or not case["turns"]:
            raise ValueError(f"Line {line_number} must contain a JSON object with a non-empty turns list.")
        cases.append(case)
    if not cases:
        raise ValueError("The evaluation file contains no conversation cases.")
    return cases


def evaluate(path, owner_eduai_id, role="Student", show_answers=True, case_id=None):
    """Run each sample conversation; content quality remains a human review."""
    cases = _read_cases(path)
    if case_id:
        cases = [case for case in cases if str(case.get("case_id", "")) == case_id]
        if not cases:
            raise ValueError(f"No evaluation case named {case_id!r} exists in {path}.")
    results = []

    for case_number, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id", f"case-{case_number}"))
        context = case.get("context") if isinstance(case.get("context"), dict) else {}
        answer_style = case.get("answer_style", "detailed")
        knowledge_mode = case.get("knowledge_mode", "general")
        history = []
        last_answer = ""
        last_citations = []
        last_metrics = {}

        print(f"\n{'=' * 78}\n{case_id} | {knowledge_mode} | {answer_style}")
        for turn_number, raw_turn in enumerate(case["turns"], start=1):
            question = raw_turn.get("question", "") if isinstance(raw_turn, dict) else raw_turn
            question = str(question or "").strip()
            if not question:
                raise ValueError(f"Case {case_id!r} has an empty question at turn {turn_number}.")

            chunks, citations, metrics = stream_answer(
                question,
                owner_eduai_id,
                role,
                context=context,
                history=history,
                answer_style=answer_style,
                knowledge_mode=knowledge_mode,
                record_metrics=False,
            )
            answer = "".join(str(chunk) for chunk in chunks).strip()
            history.extend([
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ])
            last_answer = answer
            last_citations = citations
            last_metrics = metrics
            turn_words = _word_count(answer)
            print(
                f"Turn {turn_number}: {turn_words} words · "
                f"retrieval {float(metrics.get('retrieval_ms') or 0):.0f} ms · "
                f"first output {float(metrics.get('first_output_ms') or 0):.0f} ms · "
                f"generation {float(metrics.get('generation_ms') or 0):.0f} ms · "
                f"sources {len(citations)}"
            )
            if show_answers:
                print(f"Q: {question}\nA: {answer}")

        checks = case.get("checks") if isinstance(case.get("checks"), dict) else {}
        words = _word_count(last_answer)
        minimum_words = int(checks.get("minimum_words", 0) or 0)
        minimum_sources = int(checks.get("minimum_sources", 0) or 0)
        required_terms = checks.get("must_include", [])
        forbidden_terms = checks.get("must_not_include", [])
        if isinstance(required_terms, str):
            required_terms = [required_terms]
        if isinstance(forbidden_terms, str):
            forbidden_terms = [forbidden_terms]
        must_include = [str(term).casefold() for term in required_terms]
        must_not_include = [str(term).casefold() for term in forbidden_terms]
        answer_folded = last_answer.casefold()
        missing_terms = [term for term in must_include if term not in answer_folded]
        unwanted_terms = [term for term in must_not_include if term in answer_folded]
        passed = (
            words >= minimum_words
            and len(last_citations) >= minimum_sources
            and not missing_terms
            and not unwanted_terms
        )
        result = {
            "case_id": case_id,
            "passed_basic_checks": passed,
            "answer_words": words,
            "minimum_words": minimum_words,
            "source_count": len(last_citations),
            "minimum_sources": minimum_sources,
            "missing_terms": missing_terms,
            "unexpected_terms": unwanted_terms,
            "retrieval_ms": last_metrics.get("retrieval_ms", 0),
            "first_output_ms": last_metrics.get("first_output_ms", 0),
            "generation_ms": last_metrics.get("generation_ms", 0),
        }
        results.append(result)
        print(
            f"Checks: {'PASS' if passed else 'REVIEW'} · final answer {words} words · "
            f"citations {len(last_citations)}"
        )
        if missing_terms:
            print("Missing expected terms: " + ", ".join(missing_terms))
        if unwanted_terms:
            print("Unexpected terms: " + ", ".join(unwanted_terms))
        if len(last_citations) < minimum_sources:
            print(f"Expected at least {minimum_sources} source citations.")

    passed_count = sum(bool(result["passed_basic_checks"]) for result in results)
    print(f"\nBasic checks passed: {passed_count}/{len(results)}")
    print("Review relevance, factual correctness, follow-up continuity, and source citations manually.")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", help="Path to tutor conversation cases in JSONL format")
    parser.add_argument("--owner-id", required=True, help="EduAI ID used for document access checks")
    parser.add_argument("--role", choices=("Student", "Teacher", "Admin"), default="Student")
    parser.add_argument("--summary-only", action="store_true", help="Do not print generated answer text")
    parser.add_argument("--case-id", help="Run one matching case instead of the full evaluation set")
    args = parser.parse_args()
    evaluate(
        args.dataset,
        args.owner_id,
        role=args.role,
        show_answers=not args.summary_only,
        case_id=args.case_id,
    )
