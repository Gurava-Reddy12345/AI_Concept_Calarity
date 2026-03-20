import re
from groq import Groq

client = Groq()
MODEL = "llama-3.1-8b-instant"

DIFFICULTY_CONFIGS = {
    "beginner": {
        "audience": "a curious 10-year-old with no prior knowledge",
        "rules": [
            "Use everyday analogies and comparisons to familiar objects",
            "Avoid ALL technical jargon — if a term is unavoidable, define it immediately",
            "Keep sentences short (under 20 words each)",
            "Use a friendly, encouraging tone"
        ],
        "max_tokens": 200,
    },
    "intermediate": {
        "audience": "a high school or undergraduate student with basic science literacy",
        "rules": [
            "Use some technical vocabulary, but explain unfamiliar terms briefly",
            "Reference mechanisms and processes, not just outcomes",
            "Balance depth with clarity",
        ],
        "max_tokens": 240,
    },
    "expert": {
        "audience": "a graduate-level researcher or professional in a STEM field",
        "rules": [
            "Use precise technical terminology without over-explaining basics",
            "Reference underlying mechanisms, edge cases, or current research",
            "Be concise but intellectually thorough"
        ],
        "max_tokens": 300,
    }
}

DIFFICULTY_TAGS = {
    "beginner":     {"label": "Foundational", "emoji": "🌱"},
    "intermediate": {"label": "Intermediate",  "emoji": "⚗️"},
    "expert":       {"label": "Advanced",      "emoji": "🔬"}
}

LANGUAGE_INSTRUCTIONS = {
    "English": "Respond entirely in English.",
    "Hindi":   "Respond entirely in Hindi (हिन्दी). Use Devanagari script.",
    "Telugu":  "Respond entirely in Telugu (తెలుగు). Use Telugu script.",
    "French":  "Respond entirely in French (Français).",
    "German":  "Respond entirely in German (Deutsch).",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _validate_term(term: str) -> str:
    term = _clean(term)
    if not term:
        raise ValueError("Please enter a scientific term.")
    if not re.search(r"[A-Za-zÀ-ÿ\u0900-\u097F\u0C00-\u0C7F]", term):
        raise ValueError("Input must contain letters.")
    if len(term) > 200:
        raise ValueError("Term is too long. Please be more specific.")
    return term


def generate_explanation(term: str, difficulty: str = "intermediate", language: str = "English") -> dict:
    term = _validate_term(term)
    difficulty = difficulty if difficulty in DIFFICULTY_CONFIGS else "intermediate"
    language   = language   if language   in LANGUAGE_INSTRUCTIONS else "English"

    config   = DIFFICULTY_CONFIGS[difficulty]
    tag      = DIFFICULTY_TAGS[difficulty]
    lang_instr = LANGUAGE_INSTRUCTIONS[language]
    rules_block = "\n".join(f"  - {r}" for r in config["rules"])

    prompt = f"""You are a brilliant science educator explaining to {config['audience']}.

Language instruction: {lang_instr}

Explain the concept below using this EXACT structure.

Rules:
{rules_block}
  - Total response must be under 200 words
  - Do not use markdown headers or asterisks
  - Write all sections in the specified language

Concept: {term}

Respond in this exact format (keep the labels in English, content in target language):
EXPLANATION: [2-3 sentences explaining what it is]
EXAMPLE: [1 concrete real-world example]
KEY INSIGHT: [The single most important thing to understand]
"""

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.35,
            max_tokens=config["max_tokens"],
        )
    except Exception as e:
        print("GROQ ERROR:", e)
        raise RuntimeError("AI service temporarily unavailable. Please try again.")

    if not resp.choices:
        raise RuntimeError("No response received from AI.")

    raw = _clean(resp.choices[0].message.content or "")
    if not raw:
        raise RuntimeError("AI returned an empty response.")

    parsed = _parse_structured_response(raw)

    return {
        "term":        term,
        "difficulty":  difficulty,
        "language":    language,
        "tag":         tag,
        "explanation": parsed.get("explanation", raw),
        "example":     parsed.get("example", ""),
        "key_insight": parsed.get("key_insight", ""),
    }


def _parse_structured_response(text: str) -> dict:
    result = {}
    patterns = {
        "explanation": r"EXPLANATION:\s*(.+?)(?=EXAMPLE:|KEY INSIGHT:|$)",
        "example":     r"EXAMPLE:\s*(.+?)(?=KEY INSIGHT:|$)",
        "key_insight": r"KEY INSIGHT:\s*(.+?)$"
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            result[key] = _clean(match.group(1))
    return result


def generate_related_terms(term: str) -> list:
    prompt = f"""List exactly 4 scientific concepts closely related to "{term}".
Return only a comma-separated list. No explanations, no numbering.
Example format: Osmosis, Cell membrane, Diffusion, Active transport"""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=50
        )
        text = resp.choices[0].message.content.strip()
        terms = [t.strip().strip(".,;") for t in text.split(",") if t.strip()]
        return terms[:4]
    except Exception:
        return []


def generate_followup_answer(term: str, question: str, difficulty: str = "intermediate",
                              context: str = "", language: str = "English") -> str:
    term     = _validate_term(term)
    question = _clean(question)
    difficulty = difficulty if difficulty in DIFFICULTY_CONFIGS else "intermediate"
    language   = language   if language   in LANGUAGE_INSTRUCTIONS else "English"
    config     = DIFFICULTY_CONFIGS[difficulty]
    lang_instr = LANGUAGE_INSTRUCTIONS[language]
    context_block = f"\nPrevious explanation context:\n{context[:500]}" if context else ""

    prompt = f"""You are a science educator. A student just learned about "{term}" at {difficulty} level.{context_block}

Language instruction: {lang_instr}

Follow-up question: "{question}"

Rules:
  - Answer directly and concisely in the specified language
  - Match the audience: {config['audience']}
  - Be conversational, like continuing a tutoring session
  - Maximum 3 sentences
"""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=160
        )
        return _clean(resp.choices[0].message.content or "")
    except Exception as e:
        print("GROQ FOLLOWUP ERROR:", e)
        raise RuntimeError("Could not generate follow-up answer.")