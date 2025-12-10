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
You are a deterministic helper that saves a book manuscript and its metadata.

Input JSON:
{
  "working_title": "...",
  "full_book_markdown": "...",
  "metadata": { ... }
}

You MUST do exactly the following:

1) Call the tool "save_book_to_gcs" ONCE with:
   {
     "working_title": <input.working_title>,
     "full_book_markdown": <input.full_book_markdown>,
     "metadata": <input.metadata>
   }

2) Wait for the tool result. It will return:
   {
     "manuscript_gcs_uri": "gs://...",
     "metadata_gcs_uri": "gs://..."
   }

3) Return JSON ONLY, with exactly this structure (no extra fields):

{
  "manuscript_gcs_uri": "<from tool.manuscript_gcs_uri>",
  "metadata_gcs_uri": "<from tool.metadata_gcs_uri>"
}

Rules:
- Do NOT call any other tools.
- Do NOT add commentary or Markdown.
- Output must be valid JSON only.
"""
from .tools import save_book_to_gcs

gcs_save_agent = Agent(
    model="gemini-2.5-flash",
    name="gcs_save_agent",
    instruction=GCS_SAVE_INSTRUCTION,
    tools=[save_book_to_gcs],
)

# ------------------------------------------------------------
# 4) CHAPTER WRITER AGENTS (PARALLEL DEMO)
# ------------------------------------------------------------

# For now this is a DEMO that writes up to N chapters in parallel.
# Each agent is responsible for *one* chapter number.
# They rely on:
#   - The original user JSON ("book_spec" style payload)
#   - The outline JSON produced earlier by outline_agent
# being present in the conversation history.

CHAPTER_WRITER_INSTRUCTION_TEMPLATE = """
You are Chapter Writer Agent for chapter number {chapter_number}.

Conversation context will include:
- The ORIGINAL user JSON payload describing the book
  (topic, audience, author voice, etc.).
- The outline JSON produced by outline_agent with a top-level field:
  "chapters": [{{"number": int, "working_title": str, "subtitle": str, "purpose": str, ...}}, ...]

Your job is:

1. Find the chapter in outline.chapters with "number" == {chapter_number}.
   - If NO such chapter exists, output a JSON object:
     {{
       "chapter_number": {chapter_number},
       "used": false
     }}
     and nothing else.

2. If the chapter DOES exist:
   - Let working_title = that chapter's title field (or working_title).
   - Let subheading = that chapter's subtitle (or similar field).
   - Use the overall book spec (topic, audience, author_voice_style) to shape the voice.

3. Use the google_search tool to find an inspirational quote:
   - Call google_search with a query like:
     "<book topic> <working_title> inspirational quote"
   - Inspect the snippets in the results.
   - Extract a short, plausible quote and author.
   - If you cannot find a usable quote, create a short synthetic quote that
     fits the chapter purpose and assign a plausible author type
     (e.g. "Modern technology leader", "Stoic philosopher") but do not invent
     real people.

4. Write ONLY this chapter's content in Kindle-ready Markdown:
   - Use UK English spelling.
   - Do NOT mention AI or tools.
   - Aim for a natural human voice.
   - Avoid patterns that would reveal the text is machine-generated.
   - Structure:
       # <Chapter title>
       ## <Subheading>
       *"<Quote text>" — <Quote author>*

       <Body text paragraphs, 800–1200 words, no bullet list longer than 5 items>

5. Output MUST be a SINGLE JSON object (no commentary) of the form:
   {{
     "chapter_number": {chapter_number},
     "used": true,
     "title": "<final title>",
     "subheading": "<final subheading>",
     "quote": "<quote text>",
     "quote_author": "<quote author>",
     "content_markdown": "<full chapter markdown as described above>"
   }}

Rules:
- NEVER write more than one chapter.
- NEVER modify chapter numbering.
- NEVER output Markdown fences, backticks, or extra commentary.
"""

# For the demo, we will create a small fixed pool of chapter agents.
# Later we can expand this or generate them programmatically for all chapters.
DEMO_CHAPTER_AGENT_COUNT = 3  # start small for testing

chapter_writer_agents = [
    Agent(
        model="gemini-2.5-flash",
        name=f"chapter_writer_{i}",
        instruction=CHAPTER_WRITER_INSTRUCTION_TEMPLATE.format(chapter_number=i),
        tools=[google_search],
    )
    for i in range(1, DEMO_CHAPTER_AGENT_COUNT + 1)
]

