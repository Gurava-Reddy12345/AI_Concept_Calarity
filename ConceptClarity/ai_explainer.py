import re
from groq import Groq

client = Groq()
MODEL = "llama-3.1-8b-instant"

def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def generate_explanation(term: str) -> str:
    term = _clean(term)

    if not term:
        raise ValueError("Please enter a scientific term.")
    if not re.search(r"[A-Za-z]", term):
        raise ValueError("Input must contain letters.")

    prompt = prompt = f"""
Explain the scientific term below in very simple language.

Rules:
- Write only 3 to 4 short sentences
- Do NOT start with phrases like "Let's break down" or "Imagine"
- Do NOT repeat the term unnecessarily
- Keep it clear and beginner-friendly
- End the explanation properly

Term: {term}
"""

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=120,
        )
    except Exception as e:
        print("GROQ ERROR:", e)
        raise RuntimeError("Groq API error")

    if not resp.choices:
        raise RuntimeError("Empty response from AI")

    text = _clean(resp.choices[0].message.content or "")
    if not text:
        raise RuntimeError("No explanation generated")

    return text
