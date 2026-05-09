from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
from rag_agent import CosechadosHybridAgent

app = FastAPI(title="Cosechados Hybrid API")
rag = CosechadosHybridAgent()

class ChatRequest(BaseModel):
    query: str
    history: List[Dict[str, Any]] = []

@app.post("/api/v1/chat")
def chat_endpoint(request: ChatRequest):
    return rag.ask(request.query, request.history)
