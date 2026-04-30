from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import List
from rag_engine import rag_system

# Initialize the FastAPI application
app = FastAPI(
    title="DTU Course Assistant (RAG System)",
    description="A Retrieval-Augmented Generation system for querying DTU courses.",
    version="1.0.0"
)

# ---------------------------------------------------------
# Pydantic Models for Response formatting
# ---------------------------------------------------------

class SearchResultItem(BaseModel):
    course_code: str
    title: str
    score: float

class SearchResponse(BaseModel):
    query: str
    mode: str
    results: List[SearchResultItem]

class AskResponse(BaseModel):
    query: str
    answer: str
    retrieved_courses: List[dict]

# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------

@app.get("/v1/search", response_model=SearchResponse)
def search_courses(
    query: str = Query(..., description="The search term to look for"),
    top_k: int = Query(5, ge=1, le=20, description="How many results to return"),
    mode: str = Query("sparse", pattern="^(sparse|dense|hybrid)$", description="The retrieval strategy")
):
    """
    Standard search endpoint. Returns the most relevant courses based on the query,
    without trying to generate an answer with the LLM.
    """
    try:
        raw_results = rag_system.search(query, top_k, mode)
        
        # We drop the 'document' field here so we don't send massive text blocks in the JSON response
        clean_results = [
            {
                "course_code": item["course_code"],
                "title": item["title"],
                "score": item["score"]
            } 
            for item in raw_results
        ]
        
        return {
            "query": query,
            "mode": mode,
            "results": clean_results
        }
    except ValueError as ve:
        # E.g., if an invalid mode was somehow passed
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error during search.")


@app.get("/v1/ask", response_model=AskResponse)
def ask_question(
    query: str = Query(..., description="The natural language question about a course"),
    top_k: int = Query(5, ge=1, le=10, description="Number of context documents to fetch"),
    mode: str = Query("sparse", pattern="^(sparse|dense|hybrid)$", description="The retrieval strategy to use for context")
):
    """
    RAG endpoint. Retrieves context courses first, then feeds them to the LLM
    to answer the user's question.
    """
    try:
        # Step 1: Get the relevant courses (the 'Retrieval' part of RAG)
        context_courses = rag_system.search(query, top_k, mode)
        
        # Step 2: Formulate the answer (the 'Augmented Generation' part)
        final_answer = rag_system.generate_answer(query, context_courses)
        
        # Format the references for the output
        references = [
            {"course_code": c["course_code"], "title": c["title"]} 
            for c in context_courses
        ]
        
        return {
            "query": query,
            "answer": final_answer,
            "retrieved_courses": references
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process the question: {str(e)}")

# You can run this locally with:
# uvicorn main:app --reload
