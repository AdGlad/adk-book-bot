# book_agent/agent.py
"""
Root ADK agent that orchestrates a multi-stage book workflow:

1) Calls outline_agent to plan chapters
2) Calls manuscript_agent to write content
3) Calls gcs_save_agent to persist manuscript + metadata to GCS
4) Returns a final combined JSON suitable as a book payload
"""

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from .custom_agents import outline_agent, manuscript_agent, gcs_save_agent


ROOT_INSTRUCTION = """
ROOT WORKFLOW AGENT
===================

The user provides ONE JSON object describing the book (book_topic, author_name,
author_bio, author_voice_style, target_audience, book_purpose, min_chapters).

You MUST run the following pipeline using tool calls in this exact order:

STEP 1 — call outline_agent
---------------------------
- Call the tool named "outline_agent".
- Pass the user input JSON as-is as the input.
- Wait for the tool result. Call no other tools until it returns.

STEP 2 — call manuscript_agent
------------------------------
- Call the tool named "manuscript_agent".
- The input JSON MUST be:

  {
    "outline": <outline_agent JSON result>,
    "book_spec": <original user JSON>
  }

- Wait for the tool result. The result contains:
  - working_title
  - subtitle
  - blurb
  - front_matter_markdown
  - chapters (EXACTLY 3)
  - full_book_markdown

STEP 3 — call gcs_save_agent
----------------------------
- Call the tool named "gcs_save_agent".
- Build the input JSON as:

  {
    "working_title": <manuscript.working_title>,
    "full_book_markdown": <manuscript.full_book_markdown>,
    "metadata": {
      "working_title": <manuscript.working_title>,
      "subtitle": <manuscript.subtitle>,
      "chapter_count": <len(manuscript.chapters)>,
      "blurb": <manuscript.blurb>,
      "target_audience": <user.target_audience>
    }
  }

- Wait for the tool result. The result MUST contain:
  - manuscript_gcs_uri
  - metadata_gcs_uri

You MUST NOT produce the final JSON answer before gcs_save_agent has been called
and returned its JSON. If you have not yet called gcs_save_agent, you are not done.

STEP 4 — Final output JSON
--------------------------

After all THREE tool calls have completed, you MUST output ONE final JSON object
with the following structure:

{
  "working_title": "<from manuscript>",
  "subtitle": "<from manuscript>",
  "blurb": "<from manuscript>",
  "front_matter_markdown": {
    "dedication": "...",
    "introduction": "..."
  },
  "chapters": [
    ...copy EXACTLY the 3 chapters array from manuscript...
  ],
  "full_book_markdown": "<from manuscript>",
  "cover_prompts": {
    "front": "string",
    "back": "string"
  },
  "storage_uris": {
    "manuscript_gcs_uri": "<from gcs_save_agent.manuscript_gcs_uri>",
    "additional_notes": "Metadata stored at: <gcs_save_agent.metadata_gcs_uri>"
  }
}

Cover prompts:
- front: a short textual prompt describing a suitable front cover image
  for the book, including mood and colours.
- back: a short textual description for a simpler back cover with space for text.

Rules:
- Use UK English spelling throughout.
- Do NOT mention tools, ADK, Google Cloud, Vertex, or any implementation detail.
- Output MUST be valid JSON ONLY, no commentary, no Markdown fences.
- storage_uris.manuscript_gcs_uri MUST come from gcs_save_agent.manuscript_gcs_uri.
- storage_uris.additional_notes MUST include gcs_save_agent.metadata_gcs_uri as
  "Metadata stored at: ...".
"""

root_agent = Agent(
    model="gemini-2.5-flash",
    name="book_root_agent",
    description="Multi-step book pipeline orchestrator (outline + manuscript + GCS save).",
    instruction=ROOT_INSTRUCTION,
    tools=[
        AgentTool(agent=outline_agent),
        AgentTool(agent=manuscript_agent),
        AgentTool(agent=gcs_save_agent),
    ],
)
