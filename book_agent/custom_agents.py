from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import google_search


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

HARD RULES ABOUT CHAPTERS
=========================
- Let N = min_chapters from the input.
- The length of the "chapters" array MUST be AT LEAST N.
- You MUST NOT return fewer than N chapters under any circumstances.
- You MAY add a few extra chapters if it genuinely improves the structure,
  but NEVER exceed 25 chapters in total.
- Chapter numbers MUST be sequential integers starting at 1 (1, 2, 3, ...).
- Each chapter MUST have a distinct, commercially appealing, short title.


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
You write a non-fiction manuscript from an outline.

You ALSO have access to the tool `google_search`.

For EACH CHAPTER:
 - Before choosing the quote, call google_search like:
   {
     "query": "<book_spec.book_topic> <chapter title> inspirational quote",
     "num_results": 5
   }
 - Inspect the `snippet` fields in the returned results.
 - Extract a plausible short quote + author from a snippet.
 - If snippets contain no usable quote, create a short fallback quote that fits
   the chapter theme.

Input JSON:
{
  "outline": { ...outline_agent output... },
  "book_spec": { ...original user JSON... }
}

The outline has this shape:
{
  "working_title": "string",
  "subtitle": "string",
  "chapters": [
    {
      "number": 1,
      "title": "string",
      "subheading": "string",
      "approx_word_count": 2000
    },
    ...
  ],
  "notes_for_writer": "string"
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
  "chapters": [ ... ONE entry per outline chapter ... ],
  "full_book_markdown": "string"
}

CHAPTER RULES
=============
- Pull working_title and subtitle from outline.
- For EVERY chapter in outline.chapters, create a corresponding chapter object
  in the output "chapters" list (same number, same intent for title/subheading).

STRICT CHAPTER MAPPING
======================
- Let N = len(outline.chapters).
- You MUST create EXACTLY N chapter objects in the output "chapters" list.
- For EVERY chapter in outline.chapters, you MUST create a corresponding
  chapter object with:
  - the same "number"
  - a title that preserves the same intent
  - a subheading that preserves the same intent
- You MUST NOT merge, drop, or re-number chapters.
- The number of chapters in the manuscript output MUST match the number of
  chapters in the outline 1:1.

CHAPTER OBJECT SHAPE
====================
- Each chapter object must have:

  {
    "number": <int>,
    "title": "string",
    "subheading": "string",
    "quote": {
      "text": "string",
      "author": "string"
    },
    "summary": "short 1–2 sentence summary of the chapter",
    "content_markdown": "full chapter content in Markdown"
  }

CONTENT MARKDOWN LAYOUT
=======================

- The content_markdown for each chapter MUST follow this layout:

## Chapter N – Title
_Subheading_
> "Quote text"
> — Author

Body paragraphs...

### Reflection questions
1. ...
2. ...
(2–4 questions total)

FULL BOOK MARKDOWN
==================
- full_book_markdown must be ONE Markdown string containing:
  1. Title page (title + subtitle + author_name from book_spec)
  2. Dedication
  3. Introduction
  4. ALL chapters in order of chapter.number, using the exact
     content_markdown you generated for each chapter.

STYLE RULES
===========
- Use UK English spelling.
- Aim tone and level at book_spec.target_audience.
- Respect book_spec.author_voice_style as the general voice.
- Do NOT mention tools, google_search, ADK, or Google Cloud.
- Do NOT output Markdown fences or commentary; ONLY the JSON object.
"""


manuscript_agent = Agent(
    model="gemini-2.5-flash",
    name="manuscript_agent",
    instruction=MANUSCRIPT_INSTRUCTION,
        tools=[google_search],   # << 🔥 important

)



# ------------------------------------------------------------
# 3) GCS SAVE AGENT
# ------------------------------------------------------------

GCS_SAVE_INSTRUCTION = """
You save book data to cloud storage using tools.

Input JSON:
{
  "working_title": "string",
  "full_book_markdown": "string",
  "metadata": { ...object... }
}

You MUST perform EXACTLY these steps in this order.

STEP 1 – Call save_markdown_to_gcs
----------------------------------
Call the tool named "save_markdown_to_gcs" with a JSON object:

{
  "book_title": <working_title>,
  "content_markdown": <full_book_markdown>
}

STEP 2 – After STEP 1 returns, call save_metadata_to_gcs
--------------------------------------------------------
Let manuscript_result be the JSON result from STEP 1.
Call the tool named "save_metadata_to_gcs" with a JSON object:

{
  "book_title": <working_title>,
  "metadata": <metadata>
}

STEP 3 – Final output
---------------------
After BOTH tool calls succeed, output JSON ONLY:

{
  "manuscript_gcs_uri": "<the gcs_uri returned by save_markdown_to_gcs>",
  "metadata_gcs_uri": "<the gcs_uri returned by save_metadata_to_gcs>"
}
"""

from .tools import save_markdown_to_gcs_tool, save_metadata_to_gcs_tool

gcs_save_agent = Agent(
    model="gemini-2.5-flash",
    name="gcs_save_agent",
    instruction=GCS_SAVE_INSTRUCTION,
    tools=[
        save_markdown_to_gcs_tool,
        save_metadata_to_gcs_tool,
    ],
)
