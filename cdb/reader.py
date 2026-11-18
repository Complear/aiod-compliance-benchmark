"""The reader: a language model behind an OpenAI-compatible chat endpoint extracts facts.

Default target is a local llama.cpp `llama-server` running Ministral-3-3B-Instruct-2512 (GGUF).
Any other model can be scored by pointing READER_URL / READER_MODEL elsewhere; credentials come
from READER_API_KEY and are never stored in this repository.
"""

import json
import os
import urllib.request
from pathlib import Path

from cdb.engine import FACTS, validate

PROMPT = (Path(__file__).parent / "prompt.md").read_text()

DEFAULT_FACTS = {k: (False if t is bool else "none") for k, t in FACTS.items()}

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": list(FACTS),
    "properties": {
        k: ({"type": "boolean"} if t is bool else {"type": "string", "enum": list(t)})
        for k, t in FACTS.items()
    },
}


def _chat(text, temperature=0, max_tokens=300, system=PROMPT, schema=SCHEMA, name="facts"):
    """One chat completion. The defaults are the baseline's settings; a harness that takes them
    from its own test configuration passes them with functools.partial(_chat, ...). Track B passes
    its own system prompt and JSON schema."""
    base = os.environ.get("READER_URL", "http://127.0.0.1:8080/v1").rstrip("/")
    body = {
        "model": os.environ.get("READER_MODEL", "ministral-3-3b"),
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Text: {text}\nAnswer:"},
        ],
        "response_format": {"type": "json_schema", "json_schema": {"name": name, "schema": schema}},
    }
    headers = {"Content-Type": "application/json"}
    if os.environ.get("READER_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['READER_API_KEY']}"
    req = urllib.request.Request(f"{base}/chat/completions", json.dumps(body).encode(), headers)
    with urllib.request.urlopen(req, timeout=int(os.environ.get("READER_TIMEOUT", "300"))) as resp:
        return json.load(resp)["choices"][0]["message"]["content"]


def parse(raw):
    """Facts from a model reply, or None when it is not a valid facts object."""
    try:
        start, end = raw.index("{"), raw.rindex("}") + 1
        facts = json.loads(raw[start:end])
    except (ValueError, TypeError):
        return None
    return facts if isinstance(facts, dict) and not validate(facts) else None


def read(text, chat=_chat):
    """Returns (facts, ok). Malformed output is retried once, then scored as all defaults."""
    for _ in range(2):
        facts = parse(chat(text))
        if facts is not None:
            return facts, True
    return dict(DEFAULT_FACTS), False
