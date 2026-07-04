from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_REVIEW_MODEL = os.getenv("GROQ_REVIEW_MODEL", "openai/gpt-oss-120b")
MAX_INPUT_CHARS = 2000

SYSTEM_PROMPT = """You name chat sessions. Given a user's first message, reply with a short, specific title (3-6 words) that summarizes its topic. Output ONLY the title: no quotes, no surrounding markdown, no trailing punctuation, no explanation."""

def clean(text: str) -> str:
    title = (text or "").strip().splitlines()[0] if text and text.strip() else "" #get the first line without spaces
    title = title.strip().strip("'\"").rstrip(" .!?,:;").strip("'\"").strip() #remove the trailing punctuation marks
    return title

async def generate_session_title(message: str) -> str | None:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key or not message or not message.strip():
        return None
    try:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=api_key)
        completion = await client.chat.completions.create(
            model=GROQ_REVIEW_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.strip()[:MAX_INPUT_CHARS]},
            ],
            temperature=0.3,
        )
        title = clean(completion.choices[0].message.content or "")
        return title or None
    except Exception:  # network / auth / model failures
        return None
