"""
app.py — Text-to-Persons API

This module:
1. Connects to the CampusAI LLM API (OpenAI-compatible) to extract person names from text.
2. Exposes a FastAPI endpoint POST /v1/extract-persons that accepts a JSON body
   with a "text" field and returns a JSON with a "persons" list.

Architecture:
  [Client] --POST /v1/extract-persons--> [FastAPI router]
                                               |
                                    campusai_extract_persons(text)
                                               |
                                    [CampusAI LLM API at DTU]
                                               |
                                    parse JSON response
                                               |
                                    return {"persons": [...]}
"""

import os
import json
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ─── Configuration ────────────────────────────────────────────────────────────
# The API key is injected via the environment variable CAMPUSAI_API_KEY.
# It is NEVER hardcoded. It comes from the ~/.env file passed via --env-file.
CAMPUSAI_API_KEY = os.environ.get("CAMPUSAI_API_KEY")
CAMPUSAI_BASE_URL = "https://api.campusai.compute.dtu.dk/v1"
MODEL = "Qwen3.6 35B MoE"  # The primary model available on CampusAI

# ─── FastAPI App ───────────────────────────────────────────────────────────────
# FastAPI automatically generates an interactive Swagger UI at /docs
# and an OpenAPI schema at /openapi.json
app = FastAPI(
    title="Text-to-Persons API",
    description="Extracts person names from text using the CampusAI LLM.",
    version="1.0.0",
)


# ─── Request / Response Schemas (Pydantic) ────────────────────────────────────
# Pydantic models define and VALIDATE the shape of JSON coming in and going out.
# FastAPI uses these automatically — if the client sends wrong data, it returns
# a 422 error with a helpful message without you writing any extra code.

class ExtractRequest(BaseModel):
    """Request body: the text from which to extract person names."""
    text: str


class ExtractResponse(BaseModel):
    """Response body: a list of person name strings found in the text."""
    persons: list[str]


# ─── Core Logic: LLM Integration ──────────────────────────────────────────────

def campusai_extract_persons(text: str) -> list[str]:
    """
    Sends `text` to the CampusAI LLM API with a carefully crafted prompt
    and returns a list of person names found in the text.

    Prompt strategy (few-shot):
    - We use a 'system' message to set the LLM's role and output format.
    - We use examples (few-shot) to guide the model to return ONLY valid JSON.
    - We instruct the model NOT to think aloud (no chain-of-thought in output).

    This keeps the output clean and easy to parse.
    """
    if not CAMPUSAI_API_KEY:
        raise RuntimeError("CAMPUSAI_API_KEY environment variable is not set.")

    # ── Build the prompt ──────────────────────────────────────────────────────
    system_prompt = (
        "You are a Named Entity Recognition (NER) system. "
        "Your ONLY job is to extract person names from input text. "
        "You MUST respond with a valid JSON object in this exact format: "
        '{"persons": ["Name One", "Name Two"]}. '
        "If there are no persons, respond with: {\"persons\": []}. "
        "Do NOT include any explanation, markdown, or extra text. Only JSON."
    )

    # Few-shot examples teach the model the exact expected behaviour
    few_shot_messages = [
        {"role": "user", "content": "Ms Mette Frederiksen is in New York today."},
        {"role": "assistant", "content": '{"persons": ["Mette Frederiksen"]}'},
        {"role": "user", "content": "The Eiffel Tower was built in 1889."},
        {"role": "assistant", "content": '{"persons": []}'},
        {"role": "user", "content": "Einstein and von Neumann meet each other."},
        {"role": "assistant", "content": '{"persons": ["Einstein", "von Neumann"]}'},
    ]

    # Final user message with the actual input
    messages = (
        [{"role": "system", "content": system_prompt}]
        + few_shot_messages
        + [{"role": "user", "content": text}]
    )

    # ── Call the CampusAI API ─────────────────────────────────────────────────
    response = requests.post(
        f"{CAMPUSAI_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {CAMPUSAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": MODEL, "messages": messages},
        timeout=30,
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"CampusAI API error {response.status_code}: {response.text}",
        )

    # ── Parse the LLM response ────────────────────────────────────────────────
    # The LLM returns a JSON string inside the 'content' field of the message.
    raw_content = response.json()["choices"][0]["message"]["content"]

    try:
        parsed = json.loads(raw_content)
        return parsed["persons"]
    except (json.JSONDecodeError, KeyError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse LLM response as JSON: {raw_content!r}. Error: {e}",
        )


# ─── API Endpoint ─────────────────────────────────────────────────────────────

@app.post("/v1/extract-persons", response_model=ExtractResponse)
def extract_persons(request: ExtractRequest) -> ExtractResponse:
    """
    POST /v1/extract-persons

    Accepts a JSON body: {"text": "some text here"}
    Returns:            {"persons": ["Name1", "Name2", ...]}

    Flow:
      1. FastAPI validates the request body against ExtractRequest (Pydantic).
      2. We call campusai_extract_persons() with the text.
      3. FastAPI validates the return value against ExtractResponse.
      4. The JSON response is sent back to the client.
    """
    persons = campusai_extract_persons(request.text)
    return ExtractResponse(persons=persons)


# ─── Health check ───────────────────────────────────────

@app.get("/health")
def health_check():
    """Simple health check endpoint. Returns 200 if the server is running."""
    return {"status": "ok"}
