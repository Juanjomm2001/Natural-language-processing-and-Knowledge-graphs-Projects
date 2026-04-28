"""
app_gemini.py — Text-to-Persons API (versión Gemini)

Idéntico a app.py pero usando la API de Google Gemini en vez de CampusAI.
Útil para probar mientras no tienes la clave de CampusAI.

Requiere en tu .env:
    GEMINI_API_KEY=tu_clave_de_gemini

Instalar dependencia extra:
    pip install google-genai
"""

import os
import json
from dotenv import load_dotenv

# Busca el .env en la misma carpeta que este script, sin importar desde dónde se lanza uvicorn
_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, ".env"))

from google import genai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ─── Configuración ────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash"  # Único verificado que existe (da 429 pero no 404)

# El cliente se crea dentro de la función (lazy) para evitar cuelgues al arrancar

# ─── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Text-to-Persons API (Gemini)",
    description="Extrae nombres de personas usando Google Gemini.",
    version="1.0.0",
)

# ─── Schemas Pydantic ─────────────────────────────────────────────────────────
class ExtractRequest(BaseModel):
    text: str

class ExtractResponse(BaseModel):
    persons: list[str]

# ─── Lógica principal ─────────────────────────────────────────────────────────
def campusai_extract_persons(text: str) -> list[str]:
    """
    Misma función que en app.py pero usando Gemini.
    El nombre se mantiene igual para que test_app.py funcione sin cambios.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY no está definida en el entorno.")

    # Cliente creado aquí (lazy) para no bloquear el arranque del servidor
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""You are a Named Entity Recognition (NER) system.
Your ONLY job is to extract person names from text.
Respond ONLY with valid JSON in this exact format: {{"persons": ["Name1", "Name2"]}}
If there are no persons, respond with: {{"persons": []}}
No explanations. No markdown. Only JSON.

Examples:
Input: "Ms Mette Frederiksen is in New York today."
Output: {{"persons": ["Mette Frederiksen"]}}

Input: "The Eiffel Tower was built in 1889."
Output: {{"persons": []}}

Input: "Einstein and von Neumann meet each other."
Output: {{"persons": ["Einstein", "von Neumann"]}}

Now process this:
Input: "{text}"
Output:"""

    import time
    from google.genai import errors as genai_errors

    for attempt in range(2):  # intenta un máximo de 2 veces
        try:
            response = client.models.generate_content(model=MODEL, contents=prompt)
            break  # éxito → salir del bucle
        except genai_errors.ClientError as e:
            if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)) and attempt == 0:
                time.sleep(65)  # espera 65 seg y reintenta
                continue
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit de Gemini agotado incluso tras reintentar. Espera un momento.",
                )
            raise HTTPException(status_code=502, detail=f"Error de Gemini API: {e}")
    raw = response.text.strip()

    # A veces Gemini añade ```json ... ```, quitamos eso si aparece
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        parsed = json.loads(raw)
        return parsed["persons"]
    except (json.JSONDecodeError, KeyError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo parsear la respuesta del LLM: {raw!r}. Error: {e}",
        )

# ─── Endpoint ─────────────────────────────────────────────────────────────────
@app.post("/v1/extract-persons", response_model=ExtractResponse)
def extract_persons(request: ExtractRequest) -> ExtractResponse:
    persons = campusai_extract_persons(request.text)
    return ExtractResponse(persons=persons)

@app.get("/health")
def health_check():
    return {"status": "ok"}
