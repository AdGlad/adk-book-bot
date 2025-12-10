# book_agent/test_workflow.py
import asyncio
import json

from .workflow import generate_book_payload_async


async def _run() -> None:
    # Your Stoic leadership spec
    book_spec = {
        "book_topic": "Stoic leadership for modern technology managers",
        "author_name": "Aimee Clarke",
        "author_bio": (
            "Aimee Clarke is a technology leader with experience guiding "
            "teams through cloud transformation."
        ),
        "author_voice_style": (
            "Warm, reflective and practical, written in clear UK English."
        ),
        "target_audience": "Mid-career technology managers and team leaders.",
        "book_purpose": (
            "Help leaders remain calm and principled amidst constant "
            "digital disruption."
        ),
        "min_chapters": 8,
    }

    payload = await generate_book_payload_async(book_spec)

    # Pretty-print to inspect
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
