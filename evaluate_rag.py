"""Measure retrieval Recall@k, Precision@k, and MRR on a labeled JSONL set."""

import argparse
import json
from pathlib import Path

from ai_pipeline import retrieve_documents


def evaluate(path, limit=6):
    examples = [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not examples:
        raise ValueError("The evaluation file contains no labeled questions.")
    totals = {"recall_at_k": 0.0, "precision_at_k": 0.0, "mrr": 0.0}
    used = 0
    for row in examples:
        relevant = {str(item) for item in row.get("relevant_document_ids", [])}
        if not relevant:
            continue
        documents = retrieve_documents(
            row["question"],
            row["owner_eduai_id"],
            row.get("role", "Student"),
            context=row.get("context", {}),
            limit=limit,
        )
        ranked_ids = list(dict.fromkeys(
            str(doc.metadata.get("document_id", "")) for doc in documents
            if doc.metadata.get("document_id")
        ))
        hits = [index for index, document_id in enumerate(ranked_ids, start=1) if document_id in relevant]
        totals["recall_at_k"] += len(set(ranked_ids) & relevant) / len(relevant)
        totals["precision_at_k"] += len(set(ranked_ids) & relevant) / max(1, len(ranked_ids))
        totals["mrr"] += 1 / hits[0] if hits else 0.0
        used += 1
    if used == 0:
        raise ValueError("Add at least one relevant_document_ids label to evaluate retrieval.")
    return {"questions": used, "k": int(limit), **{key: round(value / used, 4) for key, value in totals.items()}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", help="Path to a labeled JSONL dataset")
    parser.add_argument("--k", type=int, default=6, help="Number of retrieved chunks")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.dataset, args.k), indent=2))
