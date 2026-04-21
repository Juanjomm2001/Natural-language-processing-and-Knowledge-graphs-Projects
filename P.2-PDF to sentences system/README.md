# PDF to Sentences System

## Overview
This project provides a complete Dockerized Web Service capable of extracting individual grammatical sentences from academic PDF documents. It leverages advanced Natural Language Processing tools and Machine Learning to accurately parse double-column academic papers and segment the raw text into readable sentence arrays.

## Architecture & Technologies
The system is composed of two primary independent services orchestrated via Docker Compose:
- **FastAPI Backend (`web-api`)**: A lightweight Python-based REST API that receives HTTP uploads, orchestrates the entire processing pipeline, parses the output data, and handles sentence tokenization using `nltk`.
- **GROBID (`grobid`)**: A machine learning library deployed as a separate microservice container. It explicitly handles the complex transcription of academic PDF documents into structured XML (TEI format) ensuring robustness across diverse paper layouts.

## Deployment (How to Run)
Ensure you have Docker and Docker Compose installed on your machine. From the root of this project folder, open a terminal and execute:
```bash
docker compose up --build
```
> **Note:** The first time you run this command, it might take a few minutes as Docker needs to pull the heavy GROBID image. Subsequent runs will boot up in seconds.

## How to Test the API
Once the deployment finishes and both containers are running, the web service will be available locally at port `8000`.

### 1. Using cURL (Command Line)
You can send a test document like `2303.15133.pdf` using the following command:
```bash
curl -s -F pdf_file=@2303.15133.pdf http://localhost:8000/v1/extract-sentences | jq
```

### 2. Using the built-in Frontend App
A lightweight testing frontend (`app.py`) is also available for visual feedback:
1. Open a new terminal instance (do not stop the Docker containers).
2. Ensure you have the local dependencies: `pip install fastapi uvicorn httpx python-multipart`
3. Run the frontend on a different port: `uvicorn app:app --port 8001`
4. Visit `http://localhost:8001` in your browser, upload your PDF graphically, and inspect the sentences and system latency.

## Interesting Implementation Details
- **Asynchronous Communication**: The FastAPI component queries the GROBID service fully asynchronously utilizing `httpx`. This prevents the Python server from blocking while waiting for the CPU-intensive PDF parsing operations.
- **TEI XML Target Filtering**: The algorithm mitigates noise from headers, equations, or references by explicitly navigating the XML tree structure and extracting only text belonging to standard body paragraphs (`<tei:body>//<tei:p>`).
- **NLTK `punkt` Tokenization**: Instead of a naive rule-based split by single dots (.), the API utilizes the NLTK `sent_tokenize` statistical model. This approach handles acronyms (`U.S.A.`, `e.g.`) seamlessly without mistaking them for grammatical ends of sentences.
