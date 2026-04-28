# P.3 – Text to Persons (LLM NER)

REST API that extracts person names from a given text using the CampusAI DTU LLM.

## Endpoint

```
POST /v1/extract-persons
Content-Type: application/json
{"text": "Einstein and von Neumann meet each other."}
```

**Response:**
```json
{"persons": ["Einstein", "von Neumann"]}
```

## Development Execution (Local)

Start the server using the Gemini test model:

```bash
python -m uvicorn app_gemini:app --reload --port 8000
```

Interactive Swagger UI available at → `http://127.0.0.1:8000/docs`

## Execution with Docker (Production)

```bash
docker build -t text-to-persons:latest .
docker run --rm -p 8000:8000 --env-file ~/.env text-to-persons:latest
```

## Tests

To run the integration tests:

```bash
python -m pytest test_app.py -v
```

## Configuration

Create a local `.env` file in the folder (never commit it to Git). To run the application, you need at least your Google Gemini test key:

```env
GEMINI_API_KEY=your_gemini_key_here
CAMPUSAI_API_KEY=your_campusai_key_here
```

## Submission

```bash
git archive -o latest.zip HEAD
```
