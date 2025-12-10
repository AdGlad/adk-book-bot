# book_agent/tools.py
"""
Function tools for saving book data to Google Cloud Storage.

Exposed tools:
- save_markdown_to_gcs(book_title: str, content_markdown: str) -> dict
- save_metadata_to_gcs(book_title: str, metadata: dict) -> dict
"""

import json
import re
import uuid
from datetime import datetime

from google.cloud import storage
from google.adk.tools.function_tool import FunctionTool

BUCKET_NAME = "adk-book-bot"

_storage_client = None


def _get_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client


def _safe_title(title: str) -> str:
    if not title:
        return "untitled"
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", title)
    value = value.strip("-").lower()
    return value or "untitled"


# ---------------------------------------------------------------------
# save_markdown_to_gcs
# ---------------------------------------------------------------------
def save_markdown_to_gcs(book_title: str, content_markdown: str) -> dict:
    """
    Saves the full book manuscript to Google Cloud Storage and returns URI info.
    """

    client = _get_client()
    bucket = client.bucket(BUCKET_NAME)

    folder = _safe_title(book_title)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    uniq = uuid.uuid4().hex[:8]

    object_name = f"{folder}/manuscript-{timestamp}-{uniq}.md"

    blob = bucket.blob(object_name)
    blob.upload_from_string(content_markdown, content_type="text/markdown")

    return {
        "gcs_uri": f"gs://{BUCKET_NAME}/{object_name}",
        "bucket": BUCKET_NAME,
        "object_name": object_name,
    }


# Tool exposure — **no name= or description= allowed**
save_markdown_to_gcs_tool = FunctionTool(func=save_markdown_to_gcs)


# ---------------------------------------------------------------------
# save_metadata_to_gcs
# ---------------------------------------------------------------------
def save_metadata_to_gcs(book_title: str, metadata: dict) -> dict:
    """
    Saves a metadata JSON file to Google Cloud Storage.
    """

    client = _get_client()
    bucket = client.bucket(BUCKET_NAME)

    folder = _safe_title(book_title)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    uniq = uuid.uuid4().hex[:8]

    object_name = f"{folder}/metadata-{timestamp}-{uniq}.json"

    blob = bucket.blob(object_name)
    blob.upload_from_string(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        content_type="application/json",
    )

    return {
        "gcs_uri": f"gs://{BUCKET_NAME}/{object_name}",
        "bucket": BUCKET_NAME,
        "object_name": object_name,
    }


# Tool exposure
save_markdown_to_gcs = FunctionTool(save_markdown_to_gcs)
save_metadata_to_gcs = FunctionTool(save_metadata_to_gcs)
