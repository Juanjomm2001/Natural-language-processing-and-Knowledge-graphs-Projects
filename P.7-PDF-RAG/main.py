import logging
import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from rag_engine import rag_system

# Setup logging to see what's happening in the console
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Ask PDF - RAG Service")

class AskRequest(BaseModel):
    question: str

@app.post("/api/v1/upload-pdf")
def upload_pdf(file: UploadFile = File(...)):
    """
    Receives a PDF, saves it temporarily, and indexes its content.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a valid PDF file.")
        
    temp_path = f"temp_{file.filename}"
    
    try:
        # Save file to disk
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"File {file.filename} received and saved successfully.")
        
        # Process and index the PDF
        rag_system.process_pdf(temp_path)
        
        return {"message": f"Successfully indexed {file.filename}. Ready for questions!"}
        
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
            logger.info("Temporary PDF file removed.")

@app.post("/api/v1/ask")
def ask(req: AskRequest):
    """
    Retrieves context for the question and asks the LLM for an answer.
    """
    logger.info(f"Received question: {req.question}")
    
    # 1. Retrieve the best matching chunks
    relevant_chunks = rag_system.search(req.question, top_k=3)
    
    if not relevant_chunks:
        # Provide a friendly error if no PDF was uploaded yet
        raise HTTPException(status_code=400, detail="No documents indexed. Please use /api/v1/upload-pdf first.")
        
    logger.info(f"Found {len(relevant_chunks)} relevant chunks to feed the LLM.")
    
    # 2. Generate the answer using CampusAI
    result = rag_system.ask(req.question, relevant_chunks)
    
    return {
        "answer": result.get("answer", "No answer found"),
        "followup_questions": result.get("followup_questions", [])
    }
