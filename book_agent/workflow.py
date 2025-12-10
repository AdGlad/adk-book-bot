# book_agent/workflow.py
"""
Deterministic end-to-end book generator using ADK InMemoryRunner.

Pipeline:
  1) outline_agent  -> outline JSON
  2) manuscript_agent -> manuscript JSON
  3) gcs_save_agent -> GCS URIs
  4) Assemble final book payload JSON
"""

import json
from typing import Any, Dict

from google.adk.runners import InMemoryRunner
from google.genai import types

from .custom_agents import outline_agent, manuscript_agent, gcs_save_agent

APP_NAME = "adk-book-bot-local"


async def _run_json_agent_async(
    agent,
    input_obj: Dict[str, Any],
    user_id: str,
    session_id: str,
) -> Dict[str, Any]:
    """
    Run a single agent turn with JSON-in / JSON-out via InMemoryRunner.

    - Serialises input_obj to JSON text.
    - Sends it as one user message.
    - Waits for final response, parses JSON, returns dict.
    """

    # InMemoryRunner builds its own InMemorySessionService internally
    runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
    session_service = runner.session_service

    # Create a fresh session for this agent run
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    user_content = types.Content(
        role="user",
        parts=[types.Part(text=json.dumps(input_obj))],
    )

    final_text: str | None = None

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text

    if not final_text:
        raise RuntimeError(f"No final response from agent {agent.name}")

    # --- Clean up any markdown fences / extra text before parsing JSON ---
    text = final_text.strip()

    # Strip ```json ... ``` or ``` ... ``` fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) > 1:
            # drop first line (``` or ```json)
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            # drop last line (```)
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Use JSONDecoder.raw_decode to parse the FIRST JSON object only
    try:
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(text.lstrip())
        return obj
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Agent {agent.name} returned non-JSON even after cleaning:\n{text}"
        ) from e




async def generate_book_payload_async(book_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    End-to-end workflow (async):

      1) outline_agent -> outline JSON
      2) manuscript_agent -> manuscript JSON
      3) gcs_save_agent -> GCS URIs
      4) Assemble final book payload JSON
    """

    # --- STEP 1: Outline ---
    outline = await _run_json_agent_async(
        outline_agent,
        input_obj=book_spec,
        user_id="outline-user",
        session_id="outline-session",
    )

    # --- STEP 2: Manuscript ---
    manuscript_input = {
        "outline": outline,
        "book_spec": book_spec,
    }

    manuscript = await _run_json_agent_async(
        manuscript_agent,
        input_obj=manuscript_input,
        user_id="manuscript-user",
        session_id="manuscript-session",
    )

    chapters = manuscript.get("chapters") or []
    if not isinstance(chapters, list) or not chapters:
        raise RuntimeError(
            f"manuscript_agent returned no chapters. Keys: {list(manuscript.keys())}"
        )

    # --- STEP 3: Save to GCS ---
    gcs_input = {
        "working_title": manuscript["working_title"],
        "full_book_markdown": manuscript["full_book_markdown"],
        "metadata": {
            "working_title": manuscript["working_title"],
            "subtitle": manuscript.get("subtitle", ""),
            "chapter_count": len(chapters),
            "blurb": manuscript.get("blurb", ""),
            "target_audience": book_spec.get("target_audience", ""),
        },
    }

    gcs_result = await _run_json_agent_async(
        gcs_save_agent,
        input_obj=gcs_input,
        user_id="gcs-user",
        session_id="gcs-session",
    )

    manuscript_gcs_uri = gcs_result["manuscript_gcs_uri"]
    metadata_gcs_uri = gcs_result["metadata_gcs_uri"]

    # --- STEP 4: Final combined payload ---
    final_payload: Dict[str, Any] = {
        "working_title": manuscript["working_title"],
        "subtitle": manuscript.get("subtitle", ""),
        "blurb": manuscript.get("blurb", ""),
        "front_matter_markdown": manuscript.get("front_matter_markdown", {}),
        "chapters": chapters,
        "full_book_markdown": manuscript["full_book_markdown"],
        "cover_prompts": {
            "front": (
                f"Minimalist, modern non-fiction cover for a book titled "
                f"“{manuscript['working_title']}”. Calm, confident mood, "
                "cool blues with warm gold accents, clean typography."
            ),
            "back": (
                "Simple back cover with a soft gradient background and subtle "
                "geometric motif, leaving generous space for blurb text."
            ),
        },
        "storage_uris": {
            "manuscript_gcs_uri": manuscript_gcs_uri,
            "additional_notes": f"Metadata stored at: {metadata_gcs_uri}",
        },
    }

    return final_payload
