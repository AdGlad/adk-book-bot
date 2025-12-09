# book_agent/tools.py

import json
import re
import uuid
from datetime import datetime
from typing import Dict, Any

from google.cloud import storage

BUCKET_NAME = "adk-book-bot"


def _slugify_title(book_title: str) -> str:
    """Create a safe folder name from the book title."""
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", book_title).strip("-").lower()
    return safe or "book"


def _gcs_client_and_prefix(book_title: str):
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    folder = _slugify_title(book_title)
    return client, bucket, folder


def save_markdown_to_gcs(book_title: str, content_markdown: str) -> Dict[str, str]:
    """
    Save a complete book manuscript (Markdown) into Google Cloud Storage.

    Args:
        book_title: The working title of the book. Used to build a folder path.
        content_markdown: The full book manuscript in Markdown format.

    Returns:
        A dict with:
          - gcs_uri: The gs:// URI of the uploaded object.
          - bucket: The bucket name used.
          - object_name: The object path within the bucket.
    """
    client, bucket, folder = _gcs_client_and_prefix(book_title)

    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    object_name = f"{folder}/manuscript-{timestamp}-{short_uuid}.md"

    blob = bucket.blob(object_name)
    blob.upload_from_string(
        content_markdown,
        content_type="text/markdown; charset=utf-8",
    )

    gcs_uri = f"gs://{BUCKET_NAME}/{object_name}"

    return {
        "gcs_uri": gcs_uri,
        "bucket": BUCKET_NAME,
        "object_name": object_name,
    }


def save_metadata_to_gcs(book_title: str, metadata: Dict[str, Any]) -> Dict[str, str]:
    """
    Save a compact metadata JSON file for the book into Google Cloud Storage.

    Args:
        book_title: The working title of the book. Used to build a folder path.
        metadata: A JSON-serialisable dict with key book information
                  (e.g. title, subtitle, chapter_count, blurb).

    Returns:
        A dict with:
          - gcs_uri: The gs:// URI of the uploaded JSON.
          - bucket: The bucket name used.
          - object_name: The object path within the bucket.
    """
    client, bucket, folder = _gcs_client_and_prefix(book_title)

    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    object_name = f"{folder}/metadata-{timestamp}-{short_uuid}.json"

    blob = bucket.blob(object_name)
    blob.upload_from_string(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        content_type="application/json; charset=utf-8",
    )

    gcs_uri = f"gs://{BUCKET_NAME}/{object_name}"

    return {
        "gcs_uri": gcs_uri,
        "bucket": BUCKET_NAME,
        "object_name": object_name,
    }
