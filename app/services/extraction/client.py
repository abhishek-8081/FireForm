"""The Ollama call behind one chunk.

Thin on purpose: build nothing, decide nothing, just send a prompt and hand
back parsed JSON. Ollama's JSON mode does most of the work, but small models
still wrap answers in a code fence or add a sentence, so the parser tolerates
both rather than failing a chunk over formatting.
"""

from __future__ import annotations

import json
from typing import Any

import requests

from app.core.config import OLLAMA_HOST, OLLAMA_MAX_TOKENS, OLLAMA_MODEL, OLLAMA_TIMEOUT
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMUnavailableError(RuntimeError):
    """Ollama could not be reached. Nothing is extractable, so the whole run fails."""


class ChunkCallError(RuntimeError):
    """One chunk call failed or came back unparseable. Retryable."""


class ChunkTimeoutError(ChunkCallError):
    """A chunk call ran past the timeout.

    Not worth retrying: the same prompt on the same model takes the same time,
    so a retry only doubles the wait before the section is left empty anyway.
    """


def _close_truncated(text: str) -> str | None:
    """Rebuild a JSON object that was cut off mid-answer.

    An answer that hits the token ceiling ends in the middle of a value and
    parses as nothing, losing a section that was mostly fine. This trims back
    to the last complete key and value pair and closes the brackets that are
    still open. Only whole pairs survive, so no half value is ever kept.
    """
    depth: list[str] = []
    in_string = False
    escaped = False
    last_complete = None

    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char in "{[":
            depth.append("}" if char == "{" else "]")
        elif char in "}]":
            if depth:
                depth.pop()
            last_complete = index + 1
        elif char == "," and depth:
            last_complete = index

    if last_complete is None:
        return None

    # Re-count what is still open at the cut, then close it.
    head = text[:last_complete]
    stack: list[str] = []
    in_string = False
    escaped = False
    for char in head:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char in "{[":
            stack.append("}" if char == "{" else "]")
        elif char in "}]" and stack:
            stack.pop()

    return head + "".join(reversed(stack))


def _extract_json_object(raw: str) -> dict[str, Any]:
    """Parse the model's answer, ignoring a code fence or surrounding prose."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1] if "```" in text[3:] else text[3:]
        text = text.removeprefix("json").strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as first_error:
        start = text.find("{")
        end = text.rfind("}")
        candidate = text[start : end + 1] if start != -1 and end > start else None
        try:
            parsed = json.loads(candidate) if candidate else None
        except json.JSONDecodeError:
            parsed = None

        if parsed is None:
            repaired = _close_truncated(text[start:] if start != -1 else text)
            if repaired is None:
                raise ChunkCallError(
                    f"no JSON object in the model's answer: {raw[:200]!r}"
                ) from first_error
            try:
                parsed = json.loads(repaired)
            except json.JSONDecodeError as exc:
                raise ChunkCallError(f"unparseable JSON from the model: {exc}") from exc
            logger.warning(
                "the model's answer was cut off; kept the %d complete field(s) before the cut",
                len(parsed) if isinstance(parsed, dict) else 0,
            )

    if not isinstance(parsed, dict):
        raise ChunkCallError(f"expected a JSON object, got {type(parsed).__name__}")
    return parsed


def call_chunk(prompt: str, model: str | None = None) -> dict[str, Any]:
    """Send one chunk prompt to Ollama and return the parsed JSON object."""
    payload = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            # Deterministic decoding: extraction should not vary run to run.
            "temperature": 0,
            # A section's answer is a small object. Without a cap a small model
            # will happily echo the whole skeleton back with nulls in it and
            # spend the timeout doing it.
            "num_predict": OLLAMA_MAX_TOKENS,
        },
    }
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate", json=payload, timeout=OLLAMA_TIMEOUT
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as exc:
        raise LLMUnavailableError(f"could not reach Ollama at {OLLAMA_HOST}: {exc}") from exc
    except requests.exceptions.Timeout as exc:
        raise ChunkTimeoutError(f"Ollama timed out after {OLLAMA_TIMEOUT}s") from exc
    except requests.exceptions.RequestException as exc:
        raise ChunkCallError(f"Ollama request failed: {exc}") from exc

    try:
        body = response.json()
    except ValueError as exc:
        raise ChunkCallError(f"Ollama returned a non-JSON body: {exc}") from exc

    return _extract_json_object(body.get("response", ""))
