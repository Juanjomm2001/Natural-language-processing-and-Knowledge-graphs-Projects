# Sentiment Analysis API

This is a simple sentiment analysis API built with FastAPI in Python. It evaluates Danish and English texts (such as course evaluations) and returns a sentiment score.

## Features

- **Basic Sentiment Analysis**: Searches for basic keywords in English and Danish (e.g., *good*, *god*, *bad*, *dårlig*).
- **Fast and Lightweight**: Built with [FastAPI](https://fastapi.tiangolo.com/).
- **Containerized**: Can be run inside an efficient Docker/Podman container (using Alpine Linux) with a very small footprint (< 200 MB).

## Endpoints

### `POST /v1/sentiment`

**Input (JSON):**
```json
{
  "text": "Det var en god lærer."
}
```

**Output (JSON):**
```json
{
  "score": 3
}
```
*Scores range from -5 to 5, where `-3` is negative, `0` is neutral, and `3` is positive.*

## Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
3. Visit the **Swagger Documentation** at `http://127.0.0.1:8000/docs`.

## Testing

You can run the included tests using the following script:

```bash
python test_main.py
```

## Docker / Podman

To build and run with Podman / Docker:

```bash
# Build the image
podman build -t sentiment-api .

# Run the container
podman run -p 8000:8000 sentiment-api
```
Once running, the API and documentation will be available at `http://localhost:8000`.
