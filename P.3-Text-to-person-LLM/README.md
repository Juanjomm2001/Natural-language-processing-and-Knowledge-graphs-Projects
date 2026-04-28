# P.3 – Text to Persons (LLM NER)

REST API que extrae nombres de personas de un texto usando un LLM de CampusAI DTU.

## Endpoint

```
POST /v1/extract-persons
Content-Type: application/json
{"text": "Einstein and von Neumann meet each other."}
```

**Respuesta:**
```json
{"persons": ["Einstein", "von Neumann"]}
```

## Ejecución en Desarrollo (Local)

Arranca el servidor usando el modelo de prueba de Gemini:

```bash
python -m uvicorn app_gemini:app --reload --port 8000
```

Swagger UI interactivo disponible en → `http://127.0.0.1:8000/docs`

## Ejecución con Docker (Producción)

```bash
docker build -t text-to-persons:latest .
docker run --rm -p 8000:8000 --env-file ~/.env text-to-persons:latest
```

## Tests

Para pasar los tests integrados:

```bash
python -m pytest test_app.py -v
```

Crea un archivo `.env` local en la carpeta (nunca lo subas a Git). Para funcionar, necesitas al menos tu clave de pruebas de Google Gemini:

```env
GEMINI_API_KEY=tu_clave_gemini_aqui
CAMPUSAI_API_KEY=tu_clave_campusai_aqui
```

## Entrega

```bash
git archive -o latest.zip HEAD
```
