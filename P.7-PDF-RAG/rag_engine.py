import os
import re
import numpy as np
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import dspy
from dotenv import load_dotenv
import logging
import json

# Setup logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.expanduser("~/.env"))
load_dotenv(".env", override=True)

class RAGEngine:
    """
    Core engine handling PDF reading, chunking, dense retrieval,
    and generating answers via LLMs (CampusAI).
    """
    def __init__(self):
        self.chunks = []
        
        logger.info("Loading embedding model (all-MiniLM-L6-v2)...")
        # We use a dense model to map text chunks into semantic vector space
        self.dense_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.embeddings = None
        
        # Setup the generative model connection
        self._setup_llm()


        
# ////////////////////@app.post("/api/v1/upload-pdf")

    def _setup_llm(self):
        """
        Connect to CampusAI using DSPy
        """
        api_key = os.getenv("CAMPUSAI_API_KEY")
        model_name = os.getenv("CAMPUSAI_MODEL", "Qwen3.6-35B-MoE")
        api_url = os.getenv("CAMPUSAI_API_URL")
        
        if not api_key or not api_url:
            logger.warning("CAMPUSAI_API_KEY or CAMPUSAI_API_URL missing. LLM won't work.")
            self.llm_configured = False
            return

        model_identifier = f"openai/{model_name}"
        
        try:
            lm = dspy.LM(api_key=api_key, api_base=api_url, model=model_identifier)
            dspy.configure(lm=lm)
            self.llm_configured = True
            logger.info(f"Successfully configured LLM: {model_name}")
        except Exception as e:
            logger.error(f"Failed to set up DSPy LLM connection: {e}")
            self.llm_configured = False

    def process_pdf(self, pdf_path: str):
        """
        Reads a PDF, extracts text, chunks it, and builds the dense index.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Cannot find PDF: {pdf_path}")
            
        logger.info(f"Extracting text from {pdf_path}...")
        
        # 1. Extract text
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n\n"
            
        # 2. Chunk text smartly (sentence-based with overlap)
        self.chunks = self._chunk_text(text, chunk_size=5, overlap=2)
        
        # 3. Build embeddings
        logger.info("Computing embeddings for chunks. This may take a moment...")
        self.embeddings = self.dense_model.encode(self.chunks, convert_to_tensor=True).cpu().numpy()
        logger.info("PDF fully indexed and ready for queries!")
        
    def _chunk_text(self, text: str, chunk_size: int = 5, overlap: int = 2) -> list:
        """
        Splits text by sentences to avoid cutting phrases in half, 
        and groups them with overlap to preserve context.
        """
        logger.info("Chunking text (sentence-based approach)...")
        # Split by punctuation roughly
        sentences = re.split(r'(?<=[.!?]) +', text.replace('\n', ' '))
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        chunks = []
        i = 0
        while i < len(sentences):
            # Take a slice of sentences
            chunk_sentences = sentences[i : i + chunk_size]
            chunks.append(" ".join(chunk_sentences))
            
            # Move forward but keep some overlap
            i += (chunk_size - overlap)
            
            # Failsafe
            if chunk_size <= overlap:
                break
                
        logger.info(f"Created {len(chunks)} chunks.")
        return chunks




# //////////////////// @app.post("/api/v1/ask")  

    def search(self, query: str, top_k: int = 3) -> list:
        """
        Retrieves the top-k most semantically similar chunks for a query.
        """
        if not self.chunks or self.embeddings is None:
            logger.warning("Tried to search, but no PDF is indexed.")
            return []
            
        # Embed the query
        query_vec = self.dense_model.encode([query], convert_to_tensor=True).cpu().numpy()
        
        # Calculate cosine similarity between query and all chunks
        scores = cosine_similarity(query_vec, self.embeddings).flatten()
        
        # Get highest scoring indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        return [self.chunks[idx] for idx in top_indices]

    def ask(self, query: str, context_chunks: list) -> dict:
        """
        Asks the LLM to answer the query using the context, and generate follow-up questions.
        """
        if not getattr(self, 'llm_configured', False):
            return {"answer": "LLM not configured.", "followup_questions": []}
            
        if not context_chunks:
            return {"answer": "No context found to answer the question.", "followup_questions": []}
            
        context_text = "\n\n---\n\n".join(context_chunks)
        
        prompt = (
            "You are a helpful assistant reading a PDF document.\n"
            "Use the context below to answer the user's question.\n"
            "You MUST reply strictly with a JSON object containing exactly two keys: \n"
            "1. 'answer': Your answer to the question.\n"
            "2. 'followup_questions': A list of 3 suggested follow-up questions.\n\n"
            f"Context:\n{context_text}\n\n"
            f"Question: {query}\n\n"
            "JSON Response:"
        )
        
        try:
            lm = dspy.settings.lm
            response = lm(prompt)
            raw_output = response[0] if isinstance(response, list) else response
            
            # Si es un diccionario (que suele pasar con LiteLLM/DSPy modernos), el texto real suele estar dentro
            if isinstance(raw_output, dict):
                # Extraemos el texto que contiene el JSON del LLM
                raw_output = raw_output.get("text", raw_output.get("content", str(raw_output)))
            
            # Si es string, limpiamos el markdown
            raw_output = str(raw_output)
            clean_output = raw_output.replace("```json", "").replace("```", "").strip()
            
            result = json.loads(clean_output)
            return result
        except json.JSONDecodeError:
            logger.error(f"LLM did not return valid JSON. Raw output: {raw_output}")
            return {"answer": raw_output, "followup_questions": []}
        except Exception as e:
            logger.error(f"Error during LLM generation: {e}")
            return {"answer": "Sorry, there was an issue generating the answer.", "followup_questions": []}

# Global instance
rag_system = RAGEngine()
