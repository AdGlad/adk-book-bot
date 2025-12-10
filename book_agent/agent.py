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

User provides ONE JSON object describing the book.

You MUST run the following pipeline:

STEP 1 — call outline_agent
   Pass the user input JSON as-is.

STEP 2 — call manuscript_agent
   Call with:
   {
     "outline": <result from outline_agent>,
     "book_spec": <original user input>
   }

STEP 3 — call gcs_save_agent
   Call with:
   {
     "working_title": manuscript.working_title,
     "full_book_markdown": manuscript.full_book_markdown,
     "metadata": {
        "working_title": manuscript.working_title,
        "subtitle": manuscript.subtitle,
        "chapter_count": len(manuscript.chapters),
        "blurb": manuscript.blurb,
        "target_audience": user.target_audience
     }
   }

STEP 4 — produce final JSON ONLY:
{
  "working_title": "...",
  "subtitle": "...",
  "blurb": "...",
  "front_matter_markdown": {...},
  "chapters": [...3 chapters...],
  "full_book_markdown": "...",
  "cover_prompts": {
     "front": "string",
     "back": "string"
  },
  "storage_uris": {
     "manuscript_gcs_uri": "...",
     "additional_notes": "Metadata stored at: ..."
  }
}

Rules:
- Use UK English.
- Never mention tools, ADK, or Google Cloud.
- Output must be valid JSON ONLY.
"""

root_agent = Agent(
    model="gemini-2.5-flash",
    name="book_root_agent",
    description="Multi-step book pipeline orchestrator.",
    instruction=ROOT_INSTRUCTION,
    tools=[
        AgentTool(agent=outline_agent),
        AgentTool(agent=manuscript_agent),
        AgentTool(agent=gcs_save_agent),
    ],
)
