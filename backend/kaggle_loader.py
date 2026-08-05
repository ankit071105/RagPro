import os
import glob
import logging
from ingestor import ingest_file
from database import add_document, doc_exists

logger = logging.getLogger(__name__)
KAGGLE_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "kaggle")


def load_kaggle_dataset():
    """Pre-load Kaggle dataset files into ChromaDB on startup."""
    if not os.path.exists(KAGGLE_DATA_PATH):
        logger.info("No Kaggle data folder found, skipping pre-load.")
        return 0

    supported = ["*.pdf", "*.txt", "*.csv"]
    files = []
    for pattern in supported:
        files.extend(glob.glob(os.path.join(KAGGLE_DATA_PATH, "**", pattern), recursive=True))
        files.extend(glob.glob(os.path.join(KAGGLE_DATA_PATH, pattern)))

    files = list(set(files))
    if not files:
        logger.info("No files found in Kaggle data folder.")
        return 0

    loaded = 0
    for file_path in files:
        try:
            original_name = os.path.basename(file_path)
            result = ingest_file(file_path, original_name, source="kaggle")

            if not doc_exists(result["doc_id"]):
                add_document(
                    doc_id=result["doc_id"],
                    name=result["name"],
                    doc_type=result["type"],
                    size_kb=result["size_kb"],
                    chunk_count=result["chunk_count"],
                    page_count=result["page_count"],
                    source="kaggle"
                )
                logger.info(f"Loaded: {original_name} ({result['chunk_count']} chunks)")
                loaded += 1
            else:
                logger.info(f"Already indexed: {original_name}")
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")

    logger.info(f"Kaggle pre-load complete: {loaded} new files indexed.")
    return loaded
