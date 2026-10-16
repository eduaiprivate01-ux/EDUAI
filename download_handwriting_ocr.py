"""Download TrOCR handwriting weights for local, offline EduAI OCR."""

import os
from pathlib import Path

from huggingface_hub import snapshot_download


ROOT = Path(__file__).absolute().parent
MODEL_ID = "microsoft/trocr-base-handwritten"
MODEL_PATH = Path(
    os.getenv("EDUAI_OCR_MODEL_PATH", str(ROOT / "models" / "trocr-base-handwritten"))
)


def main():
    """Fetch the model repository into the local path used by ai_pipeline.py."""
    MODEL_PATH.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {MODEL_ID} into {MODEL_PATH}")
    snapshot_download(repo_id=MODEL_ID, local_dir=str(MODEL_PATH))
    print("Handwriting OCR model is ready for local use.")


if __name__ == "__main__":
    main()
