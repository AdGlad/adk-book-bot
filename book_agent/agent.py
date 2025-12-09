# book_agent/agent.py
"""
Simple ADK agent that generates a tiny book JSON for a given topic.

This is the INITIAL WORKING VERSION used with `adk web`.

Right now it:
- Reads one JSON object from the user's message that describes the book.
- Generates:
    - working title, subtitle, blurb
    - very short dedication and introduction
    - exactly 3 short chapters
    - full_book_markdown (title page plus front matter plus 3 chapters)
    - basic front/back cover prompts
    - storage_uris with a real GCS URI using save_markdown_to_gcs()


Later you will extend this by:
- Increasing chapter count (20 plus).
- Adding real quote lookup tools (Google Search, your own DB).
- Adding foreword and more front matter pages.
- Adding a tool for saving Markdown to Cloud Storage.
- Adding agents/tools to generate real cover images.
"""

from google.adk.agents import Agent

from .tools import save_markdown_to_gcs, save_metadata_to_gcs


SIMPLE_BOOK_INSTRUCTION = """
You are a simple non-fiction book generator.

The user will send you one JSON object describing the book, including:
- book_topic
- author_name
- author_bio
- author_voice_style
- target_audience
- book_purpose
- min_chapters

For this initial simple version:
- You MUST create exactly min_chapters chapters.
- min_chapters will be at least 3. For early testing it may be small (e.g. 3–5),
  but later it may be 20 or more for a full-length book.
- Use the other fields to shape tone and content.


You MUST reply with VALID JSON ONLY, no commentary.

JSON schema:
{
  "working_title": "string",
  "subtitle": "string",
  "blurb": "string",

  "front_matter_markdown": {
    "dedication": "string",
    "introduction": "string"
  },

  "chapters": [
    {
      "number": 1,
      "title": "string",
      "subheading": "string",
      "quote": {
        "text": "string",
        "author": "string"
      },
      "summary": "string",
      "content_markdown": "string"
    }
  ],

  "full_book_markdown": "string",

  "cover_prompts": {
    "front": "string",
    "back": "string"
  },

  "storage_uris": {
    "manuscript_gcs_uri": "string",
    "additional_notes": "string"
  }
}

Generation rules:
- Use UK English spelling.
- Natural human non-fiction tone.
- Do not mention AI, prompts, models or tools.
- Always create exactly 3 chapters.
GCS saving behaviour:
- After you have decided on the final working_title, subtitle, blurb,
  front_matter_markdown and chapters, and constructed full_book_markdown,
  you MUST call the tool save_markdown_to_gcs exactly once.
- Call it with:
    book_title = working_title
    content_markdown = full_book_markdown
- Use the returned "gcs_uri" from the tool result and set:
    storage_uris.manuscript_gcs_uri = that gcs_uri

- Then you SHOULD call save_metadata_to_gcs exactly once.
  Build a small metadata object with keys such as:
    {
      "working_title": working_title,
      "subtitle": subtitle,
      "chapter_count": length of the chapters array,
      "blurb": blurb,
      "target_audience": target_audience from the user input
    }
  Call save_metadata_to_gcs with:
    book_title = working_title
    metadata = that metadata object.
- Use the "gcs_uri" from the save_metadata_to_gcs result to set:
    storage_uris.additional_notes = "Metadata stored at: " + gcs_uri

- Do not invent or guess any gs:// URIs yourself; always rely on the tools.

"""
root_agent = Agent(
    model="gemini-2.5-flash",  # or any Vertex Gemini model you prefer
    name="simple_book_root_agent",
    description="Minimal Kindle-style book generator for ADK web debugging.",
    instruction=SIMPLE_BOOK_INSTRUCTION,
    tools=[save_markdown_to_gcs, save_metadata_to_gcs],


    # tools=[]   # later you will add tools here (quote search, GCS save, etc.)
    #ui_form={
        #"title": "Simple Book Generator",
        #"description": "Generates a minimal 3-chapter book JSON for testing.",
        #"icon": "📘"
    #}
)

