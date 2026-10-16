"""Download the optional local Cross-Encoder used to rerank RAG candidates."""

import os
from pathlib import Path

from huggingface_hub import snapshot_download


ROOT = Path(__file__).resolve().parent
MODEL_ID = "cross-encoder/ms-marco-MiniLM-L-6-v2"
TARGET = Path(os.getenv(
    "EDUAI_RERANKER_PATH",
    str(ROOT / "models" / "cross-encoder-ms-marco-MiniLM-L-6-v2"),
))


if __name__ == "__main__":
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    path = snapshot_download(
        repo_id=MODEL_ID,
        local_dir=str(TARGET),
        allow_patterns=["*.json", "*.txt", "*.model", "*.safetensors", "*.bin", "*.pt"],
        max_workers=2,
    )
    print(f"Cross-Encoder reranker is ready at {path}")
