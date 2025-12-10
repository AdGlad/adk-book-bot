# book_agent/agent.py
"""
Deterministic book workflow using SequentialAgent.

Pipeline (fixed order):
1) outline_agent      – builds the chapter outline from the user JSON
2) manuscript_agent   – writes the full manuscript (with quotes per chapter)
3) gcs_save_agent     – saves manuscript + metadata to GCS

Input to the workflow:
- ONE JSON object:
  {
    "book_topic": "...",
    "author_name": "...",
    "author_bio": "...",
    "author_voice_style": "...",
    "target_audience": "...",
    "book_purpose": "...",
    "min_chapters": 10
  }

Behaviour:
- The SequentialAgent always runs the three sub-agents in the same order
  for each invocation.
- There is no LLM decision about which tool/agent to call next.
- The symbol `root_agent` is exported for compatibility with ADK Web.
"""

from google.adk.agents import SequentialAgent

from .custom_agents import outline_agent, manuscript_agent, gcs_save_agent


# ---------------------------------------------------------------------------
# Deterministic pipeline agent
# ---------------------------------------------------------------------------

book_workflow_agent = SequentialAgent(
    name="book_workflow_agent",
    description=(
        "Deterministic non-fiction Kindle book workflow: "
        "outline → manuscript → GCS save."
    ),
    # These sub-agents run strictly in this order on every invocation.
    sub_agents=[
        outline_agent,      # Step 1: build outline from user JSON
        manuscript_agent,   # Step 2: write full manuscript (quotes per chapter)
        gcs_save_agent,     # Step 3: save to GCS and return URIs
    ],
)

# Export the workflow as root_agent so existing imports keep working:
root_agent = book_workflow_agent
