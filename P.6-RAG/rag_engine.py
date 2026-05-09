import json
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import dspy
from dotenv import load_dotenv

# We load variables from .env to keep our API keys secure during local testing.
# In a Docker environment, these might be injected directly.
load_dotenv(os.path.expanduser("~/.env"))

class RAGEngine:
    """
    Core engine handling data ingestion, retrieval (sparse/dense),
    and answer generation via Large Language Models.
    """
    def __init__(self, data_path="dtu_courses.jsonl"):
        self.courses = []
        self.documents = []
        
        # 1. Load the course dataset into memory
        self._load_data(data_path)
        
        # 2. Setup Retrievers only if we successfully loaded data
        if self.courses:
            print("Setting up Sparse Retriever (TF-IDF)...")
            # Lowercasing and removing accents helps match queries more robustly
            self.sparse_vectorizer = TfidfVectorizer(lowercase=True, strip_accents="unicode")
            self.sparse_matrix = self.sparse_vectorizer.fit_transform(self.documents)
            
            print("Setting up Dense Retriever (Sentence-Transformers)...")
            # Using a small, efficient model suitable for local embedding computation
            self.dense_model = SentenceTransformer("all-MiniLM-L6-v2")
            self.dense_matrix = self.dense_model.encode(self.documents, convert_to_tensor=True)
            self.dense_matrix_np = self.dense_matrix.cpu().numpy()
        else:
            print("No courses loaded. Retrievers are inactive.")

        # 3. Setup the generative model connection (DSPy -> CampusAI API)
        self._setup_llm()

    def _load_data(self, data_path):
        """
        Reads the JSONL dataset. For each course, it builds a single text document
        combining title, teachers, ECTS, objectives, and content. This concatenated
        string is what we will actually search against.
        """
        if not os.path.exists(data_path):
            print(f"Warning: Could not find the dataset at {data_path}. Make sure the file is there.")
            return
            
        with open(data_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                    
                course = json.loads(line)
                self.courses.append(course)
                
                # Extract relevant fields safely
                title = course.get("title", "")
                content = course.get("content", "")
                objectives = course.get("learning_objectives", [])
                obj_text = " ".join(objectives) if isinstance(objectives, list) else str(objectives)
                
                fields = course.get("fields", {})
                teacher = fields.get("Responsible", "Unknown")
                ects = fields.get("Point( ECTS )", "Unknown")
                
                # This combined block gives the retriever maximum context
                combined_text = (
                    f"Title: {title}\n"
                    f"Responsible: {teacher}\n"
                    f"ECTS: {ects}\n"
                    f"Objectives: {obj_text}\n"
                    f"Content: {content}"
                )
                self.documents.append(combined_text)
                
    def _setup_llm(self):
        """
        Initializes the connection to the CampusAI API using the DSPy library.
        Expects CAMPUSAI_API_KEY, CAMPUSAI_MODEL, and CAMPUSAI_API_URL in the environment.
        """
        api_key = os.getenv("CAMPUSAI_API_KEY")
        # Defaulting to Qwen if not specified, as per CampusAI model list
        model_name = os.getenv("CAMPUSAI_MODEL", "Qwen3.6-35B-MoE")
        api_url = os.getenv("CAMPUSAI_API_URL")
        
        if not api_key:
            print("Notice: CAMPUSAI_API_KEY is missing. You won't be able to generate answers.")
            self.llm_configured = False
            return

        # DSPy requires the "openai/" prefix when using OpenAI-compatible endpoints
        model_identifier = f"openai/{model_name}"
        
        try:
            lm = dspy.LM(api_key=api_key, api_base=api_url, model=model_identifier)
            dspy.configure(lm=lm)
            self.llm_configured = True
            print(f"Successfully configured LLM: {model_name}")
        except Exception as e:
            print(f"Failed to set up DSPy LLM connection: {e}")
            self.llm_configured = False

    def search(self, query: str, top_k: int = 5, mode: str = "sparse"):
        """
        Returns the most relevant courses for the given query.
        Supports 'sparse' (TF-IDF), 'dense' (Embeddings), and 'hybrid' (combined scores).
        """
        if not self.courses:
            return []
            
        if mode == "sparse":
            query_vec = self.sparse_vectorizer.transform([query])
            scores = cosine_similarity(query_vec, self.sparse_matrix).flatten()
            
        elif mode == "dense":
            query_vec = self.dense_model.encode([query], convert_to_tensor=True).cpu().numpy()
            scores = cosine_similarity(query_vec, self.dense_matrix_np).flatten()
            
        elif mode == "hybrid":
            # Hybrid approach: compute both and average their scores
            q_sparse = self.sparse_vectorizer.transform([query])
            score_sparse = cosine_similarity(q_sparse, self.sparse_matrix).flatten()
            
            q_dense = self.dense_model.encode([query], convert_to_tensor=True).cpu().numpy()
            score_dense = cosine_similarity(q_dense, self.dense_matrix_np).flatten()
            
            # Giving equal weight to exact word matches (sparse) and semantic meaning (dense)
            scores = 0.5 * score_dense + 0.5 * score_sparse
            
        else:
            raise ValueError(f"Invalid mode '{mode}'. Choose 'sparse', 'dense', or 'hybrid'.")

        # Get indices of the top scores, sorted descending
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            course_data = self.courses[idx]
            results.append({
                "course_code": course_data.get("course_code", ""),
                "title": course_data.get("title", ""),
                "score": float(scores[idx]),
                "document": self.documents[idx] # Kept internally so we can feed it to the LLM later
            })
            
        return results

    def generate_answer(self, query: str, retrieved_courses: list):
        """
        Takes the user's question and the raw retrieved course data, builds a prompt,
        and asks the LLM to provide a final synthesized answer.
        """
        if not getattr(self, 'llm_configured', False):
            return "Error: The LLM is not configured properly. Did you set CAMPUSAI_API_KEY?"
            
        if not retrieved_courses:
            return "I couldn't find any relevant courses to answer your question."
            
        # Stitch all retrieved documents together to form the context
        context_blocks = [course["document"] for course in retrieved_courses]
        context_text = "\n\n---\n\n".join(context_blocks)
        
        prompt = (
            "You are a helpful assistant for DTU courses.\n"
            "Use the context below to answer the user's question.\n"
            "If the answer is not present in the context, clearly state that you don't know.\n\n"
            f"Context:\n{context_text}\n\n"
            f"Question: {query}\n\n"
            "Answer:"
        )
        
        try:
            # We fetch the configured language model and prompt it directly
            lm = dspy.settings.lm
            response = lm(prompt)
            # Depending on the DSPy version/backend, it might return a list or a string
            answer = response[0] if isinstance(response, list) else response
            return str(answer).strip()
        except Exception as e:
            print(f"Error during LLM generation: {e}")
            return "Sorry, there was an issue generating the answer."

# We initialize a global instance of the engine here. 
# This ensures data is loaded and models are embedded only once when the server starts.
rag_system = RAGEngine(data_path="dtu_courses.jsonl")
