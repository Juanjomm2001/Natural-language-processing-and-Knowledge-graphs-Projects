# DTU Course RAG System

This project implements a Retrieval-Augmented Generation (RAG) system for querying technical courses at DTU. It exposes a set of REST endpoints via **FastAPI** to either perform standard document retrieval (sparse/dense/hybrid) or ask natural language questions answered by a local LLM.

## Project Structure

- `rag_engine.py`: Contains the core logic. Loads the JSONL data, sets up `TfidfVectorizer` (sparse) and `SentenceTransformer` (dense) retrievers, and configures the LLM integration using DSPy.
- `main.py`: The FastAPI application defining the `/v1/search` and `/v1/ask` routing.
- `Dockerfile`: Configuration to containerize the API.
- `dtu_courses.jsonl`: The dataset (ignored in Git).

## Setup & Requirements

1. **Dataset**: Place the `dtu_courses.jsonl` file in the root directory of this folder.
2. **Environment Variables**: Rename `.env.example` to `.env` and insert your API credentials for CampusAI. The `.env` file should include `CAMPUSAI_API_KEY`.

## Running Locally (Without Docker)

If you just want to test it locally without building the Docker image:

```bash
# Install dependencies
pip install -r requirements.txt

# Start the development server (Note: use python -m on Windows if uvicorn is not in PATH)
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Once running, access the interactive documentation at `http://127.0.0.1:8000/docs`

## Running with Docker (Recommended)

To build and run the containerized version:

```bash
# Build the Docker image
docker build -t dtu-rag-api .

# Run the container (Make sure you pass your .env file)
docker run -p 8000:8000 --env-file .env dtu-rag-api
```

## Endpoints Usage

### 1. Simple Search
Retrieve relevant courses without LLM generation. You can test different modes (`sparse`, `dense`, or `hybrid`).

```bash
curl -s "http://localhost:8000/v1/search?query=MRI&mode=sparse" | jq
```

### 2. RAG Question Answering
Ask a specific question and the system will pull context and formulate an answer.

```bash
curl -s "http://localhost:8000/v1/ask?query=Which%20course%20is%20Hiba%20Nassar%20involved%20in?&mode=hybrid" | jq
```

## How It Works Under the Hood

1. **Ingestion**: When the server boots, it reads `dtu_courses.jsonl` and merges relevant fields (title, content, teachers, ECTS) into single "documents".
2. **Vectorization**: It calculates sparse (TF-IDF) and dense (`all-MiniLM-L6-v2`) embeddings immediately, keeping them in memory for fast retrieval.
3. **Prompting**: When a user hits `/v1/ask`, the system grabs the top matches using Cosine Similarity, wraps them into a prompt alongside the original question, and requests a synthesized answer from the LLM via the CampusAI API.
