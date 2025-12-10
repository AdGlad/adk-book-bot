# book_agent/tools.py
"""
Function tools for saving book data to Google Cloud Storage.

Exposed tools:
- save_markdown_to_gcs_tool(book_title: str, content_markdown: str) -> dict
- save_metadata_to_gcs_tool(book_title: str, metadata: dict) -> dict
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
# Implementation functions (plain Python)
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


# ---------------------------------------------------------------------
# Tool exposure (single tool object per function)
# ---------------------------------------------------------------------
# ADK will infer the tool name from the underlying function name, e.g.
# "save_markdown_to_gcs" and "save_metadata_to_gcs".

save_markdown_to_gcs_tool = FunctionTool(save_markdown_to_gcs)
save_metadata_to_gcs_tool = FunctionTool(save_metadata_to_gcs)


def save_book_to_gcs(working_title: str, full_book_markdown: str, metadata: dict) -> dict:
    """
    Composite helper that:
      1) Saves the manuscript markdown
      2) Saves the metadata JSON
      3) Returns both GCS URIs in a simple JSON object
    """

    # 1) Save manuscript (call the plain Python function directly)
    manuscript_result = save_markdown_to_gcs(
        book_title=working_title,
        content_markdown=full_book_markdown,
    )
    manuscript_uri = manuscript_result["gcs_uri"]

    # 2) Save metadata (call the plain Python function directly)
    metadata_result = save_metadata_to_gcs(
        book_title=working_title,
        metadata=metadata,
    )
    metadata_uri = metadata_result["gcs_uri"]

    # 3) Final payload
    return {
        "manuscript_gcs_uri": manuscript_uri,
        "metadata_gcs_uri": metadata_uri,
    }


# Expose as a tool the LLM can call
save_book_to_gcs = FunctionTool(save_book_to_gcs)