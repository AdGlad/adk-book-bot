from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

# ------------------------------------------------------------
# 1) OUTLINE AGENT
# ------------------------------------------------------------

OUTLINE_INSTRUCTION = """
You generate a structured chapter outline for a non-fiction Kindle book.

Input is ONE JSON object with fields:
- book_topic
- author_name
- author_bio
- author_voice_style
- target_audience
- book_purpose
- min_chapters

You MUST output JSON ONLY:

{
  "working_title": "string",
  "subtitle": "string",
  "chapters": [
    {
      "number": 1,
      "title": "string",
      "subheading": "string",
      "approx_word_count": 2000
    }
  ],
  "notes_for_writer": "string"
}

Rules:
- Use UK English spelling.
- Chapters >= min_chapters, max 25.
- Titles must be short and commercially appealing.
"""

outline_agent = Agent(
    model="gemini-2.5-flash",
    name="outline_agent",
    instruction=OUTLINE_INSTRUCTION,
)



# ------------------------------------------------------------
# 2) MANUSCRIPT WRITER AGENT
# ------------------------------------------------------------

MANUSCRIPT_INSTRUCTION = """
You write a short non-fiction manuscript from an outline.

Input JSON:
{
  "outline": { ...outline_agent output... },
  "book_spec": { ...original user JSON... }
}

You MUST output JSON ONLY:

{
  "working_title": "...",
  "subtitle": "...",
  "blurb": "...",
  "front_matter_markdown": {
      "dedication": "string",
      "introduction": "string"
  },
  "chapters": [ ... EXACTLY 3 chapters ... ],
  "full_book_markdown": "string"
}

Rules:
- Pull title + subtitle from outline.
- Use first 3 chapters of outline only.
- Each chapter must follow this Markdown layout:

## Chapter N – Title
_Subheading_
> "Quote text"
> — Author

Paragraphs...

### Reflection questions
1. ...
2. ...

- Use UK English spelling.
- Do NOT call tools. Only write JSON.
"""

manuscript_agent = Agent(
    model="gemini-2.5-flash",
    name="manuscript_agent",
    instruction=MANUSCRIPT_INSTRUCTION,
)



# ------------------------------------------------------------
# 3) GCS SAVE AGENT
# ------------------------------------------------------------

GCS_SAVE_INSTRUCTION = """
You save data to GCS using tools.

Input JSON:
{
  "working_title": "...",
  "full_book_markdown": "...",
  "metadata": { ... }
}

You MUST:

1) Call tool "save_markdown_to_gcs" with:
   {
     "book_title": working_title,
     "content_markdown": full_book_markdown
   }

2) After that tool returns, call "save_metadata_to_gcs" with:
   {
     "book_title": working_title,
     "metadata": metadata
   }

3) Finally, output JSON ONLY:
1) Call tool save_markdown_to_gcs(book_title, content_markdown)
2) Call tool save_metadata_to_gcs(book_title, metadata)
3) Output JSON ONLY:

{
  "manuscript_gcs_uri": "gs://...",
  "metadata_gcs_uri": "gs://..."
}
"""

from .tools import save_markdown_to_gcs, save_metadata_to_gcs

gcs_save_agent = Agent(
    model="gemini-2.5-flash",
    name="gcs_save_agent",
    instruction=GCS_SAVE_INSTRUCTION,
    tools=[
        save_markdown_to_gcs,
        save_metadata_to_gcs,
    ]
)
