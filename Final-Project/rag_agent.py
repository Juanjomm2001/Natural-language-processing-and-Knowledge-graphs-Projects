import os
import re
import json
import fitz
import sqlite3
import shutil
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

load_dotenv(override=True)

ROUTER_PROMPT = """You are the lead orchestrator for Cosechados. Your job is to route user queries to the correct data engine and extract entities for processing.

Tools:
1. "rag": For company history, farmer bios, quality policies (Double Criba), delivery protocols (Km Real), and legal/GDPR info.
2. "inventory": For real-time data on prices, stock levels, product origins, or calculating a budget based on availability.
3. "both": Use this for hybrid queries that require linking a policy/story with a specific product or origin.

Rules:
- If specific products are mentioned, list ALL of them separately in "products" (always as a JSON array).
- Product names MUST be extracted as their generic English base word to match the database. Ignore varieties or adjectives (e.g., "melon piel de sapo" -> "Melon", "red apples" -> "Apple", "økologisk honning" -> "Honey").
- Translate from Spanish or Danish to English base words (e.g., ES: miel->Honey, manzana->Apple, sandia->Watermelon. DK: æble->Apple, honning->Honey, tomat->Tomato, appelsin->Orange, vandmelon->Watermelon).
- Do NOT extract generic categories like 'fruit', 'frutas', 'vegetables', 'productos', or 'products'.
- If NO specific products are mentioned (or only generic terms are used) but the user asks about the inventory (e.g. "what do you have from Tomelloso?", "all fruits under 3 euros"), set "products" to an empty array [].
- For "both", include a "rag_query" with just the general info part.

Examples:
User: "que me costaria un pedido de 30 kilos de miel y 20 de manzanas?" -> {{"tool": "inventory", "products": ["Honey", "Apple"]}}
User: "hvor meget koster melon piel de sapo og æble?" -> {{"tool": "inventory", "products": ["Melon", "Apple"]}}
User: "What is the return policy?" -> {{"tool": "rag"}}
User: "Tell me about David and honey stock" -> {{"tool": "both", "products": ["Honey"], "rag_query": "Who is David?"}}
User: "The company was born in a garage in a specific town. What products do we currently have from that place of origin?" -> {{"tool": "both", "products": [], "rag_query": "In which town was the company born?"}}

Respond ONLY with a JSON object.

Chat History (Context):
{history}

User query: {query}"""


class CosechadosHybridAgent:

    def __init__(self):
        self.api_key = os.getenv("CAMPUSAI_API_KEY")
        self.api_url = os.getenv("CAMPUSAI_API_URL")
        self.model_name = os.getenv("CAMPUSAI_MODEL")
        self.embed_model_name = os.getenv("CAMPUSAI_EMBED_MODEL")

        self.embeddings = OpenAIEmbeddings(
            api_key=self.api_key,
            base_url=self.api_url,
            model=self.embed_model_name
        )

        self.llm = ChatOpenAI(
            api_key=self.api_key,
            base_url=self.api_url,
            model=self.model_name,
            temperature=0
        )

        self.vectorstore = None
        self.retriever = None
        self._init_vector_db()

    def _init_vector_db(self):
        data_dir = "data"
        pdf_files = [f for f in os.listdir(data_dir) if f.endswith(".pdf")]

        if os.path.exists("./chroma_db"):
            try:
                self.vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=self.embeddings)
                count = self.vectorstore._collection.count()
                if count > 0:
                    self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
                    return
            except Exception:
                pass

        if not pdf_files:
            return

        if os.path.exists("./chroma_db"):
            shutil.rmtree("./chroma_db")

        all_splits = []
        for pdf_file in pdf_files:
            pdf_path = os.path.join(data_dir, pdf_file)
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text("text") + "\n\n"

            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
            chunks = text_splitter.split_text(text)
            for chunk_text in chunks:
                all_splits.append(Document(page_content=chunk_text, metadata={"source": pdf_file}))

        if all_splits:
            self.vectorstore = Chroma.from_documents(
                documents=all_splits,
                embedding=self.embeddings,
                persist_directory="./chroma_db"
            )
            self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})

    def _route_query(self, query: str, history: list) -> dict:
        history_str = "\n".join([f"{m['role']}: {m['content']}" for m in history]) if history else "No previous context."
        prompt = ROUTER_PROMPT.format(query=query, history=history_str)
        response = self.llm.invoke(prompt)
        raw = response.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        try:
            result = json.loads(raw)
            if "product" in result and "products" not in result:
                result["products"] = [result["product"]]
            return result
        except json.JSONDecodeError:
            return {"tool": "rag"}

    def _search_rag(self, query: str, history: list) -> dict:
        if not self.retriever:
            return {"answer": "No documents loaded.", "citations": [], "sources": []}

        docs = self.retriever.invoke(query)
        context = "\n\n".join(doc.page_content for doc in docs)
        citations = [doc.page_content for doc in docs]
        sources = list(set(doc.metadata.get("source", "unknown") for doc in docs))
        
        history_str = "\n".join([f"{m['role']}: {m['content']}" for m in history]) if history else "None"

        answer_prompt = (
            f"You are an assistant for Cosechados. Your tone must be 'campechano' (rural, extremely warm, friendly, and close, as if you are a nice farmer from a Spanish village talking to a neighbor). "
            f"Keep your response concise and direct to the point. "
            f"Answer ONLY from the context below. Reply in the same language the user used.\n\n"
            f"Chat History:\n{history_str}\n\n"
            f"Context:\n{context}\n\nQuestion: {query}"
        )
        response = self.llm.invoke(answer_prompt)

        return {"answer": response.content, "citations": citations, "sources": sources}

    def _search_inventory(self, products: list, original_query: str, history: list) -> dict:
        conn = sqlite3.connect("data/inventory.db")
        cursor = conn.cursor()

        all_results = []
        all_citations = []

        if not products:
            cursor.execute("SELECT product_name, origin, price_per_kg, stock_kg FROM inventory")
            results = cursor.fetchall()
            lines = []
            for row in results:
                line = f"Product: {row[0]}, Origin: {row[1]}, Price: {row[2]} EUR/kg, Stock: {row[3]}kg"
                lines.append(line)
                all_results.append(line)
            all_citations.append(f"SQL: SELECT * FROM inventory\n" + "\n".join(lines))
        else:
            for product_name in products:
                cursor.execute(
                    "SELECT product_name, origin, price_per_kg, stock_kg FROM inventory WHERE product_name LIKE ?",
                    (f"%{product_name}%",)
                )
                results = cursor.fetchall()

                if not results:
                    all_citations.append(f"SQL: SELECT * FROM inventory WHERE product_name LIKE '%{product_name}%' -> 0 results")
                else:
                    lines = []
                    for row in results:
                        line = f"Product: {row[0]}, Origin: {row[1]}, Price: {row[2]} EUR/kg, Stock: {row[3]}kg"
                        lines.append(line)
                        all_results.append(line)
                    all_citations.append(f"SQL: SELECT * FROM inventory WHERE product_name LIKE '%{product_name}%'\n" + "\n".join(lines))

        conn.close()

        if not all_results:
            return {
                "answer": f"We don't currently have those products in our inventory.",
                "citations": all_citations,
                "sources": ["inventory.db"]
            }
            
        history_str = "\n".join([f"{m['role']}: {m['content']}" for m in history]) if history else "None"

        answer_prompt = (
            f"You are an assistant for Cosechados. Your tone must be 'campechano' (rural, warm, friendly, and close, as if you are a nice farmer from a Spanish village talking to a neighbor).\n"
            f"Keep your response concise and direct to the point.\n"
            f"Use the following database results to answer the user's question.\n"
            f"If the user asks for a budget or calculation, do the math explicitly step by step.\n\n"
            f"Chat History:\n{history_str}\n\n"
            f"Database Results:\n"
            f"{chr(10).join(all_results)}\n\n"
            f"User Question: {original_query}\n\n"
            f"Reply in the same language the user used."
        )
        response = self.llm.invoke(answer_prompt)

        return {"answer": response.content, "citations": all_citations, "sources": ["inventory.db"]}

    def ask(self, query: str, history: list = None) -> dict:
        if history is None:
            history = []
            
        route = self._route_query(query, history)
        tool = route.get("tool", "rag")

        if tool == "inventory":
            products = route.get("products", [])
            return self._search_inventory(products, query, history)

        elif tool == "both":
            products = route.get("products", [])
            rag_query = route.get("rag_query", query)

            rag_result = self._search_rag(rag_query, history)
            inv_result = self._search_inventory(products, query, history)
            
            history_str = "\n".join([f"{m['role']}: {m['content']}" for m in history]) if history else "None"

            combined_prompt = (
                f"You are an assistant for Cosechados. Your tone must be 'campechano' (rural, extremely warm, friendly, and close, as if you are a nice farmer from a Spanish village talking to a neighbor).\n"
                f"Keep your response concise and direct to the point.\n"
                f"Combine these two pieces of information into ONE coherent answer. "
                f"If there is any math required, do it explicitly.\n"
                f"Reply in the same language the user used.\n\n"
                f"Chat History:\n{history_str}\n\n"
                f"From documents:\n{rag_result['answer']}\n\n"
                f"From inventory:\n{inv_result['answer']}\n\n"
                f"Original question: {query}"
            )
            response = self.llm.invoke(combined_prompt)

            return {
                "answer": response.content,
                "citations": rag_result["citations"] + inv_result["citations"],
                "sources": rag_result["sources"] + inv_result["sources"]
            }

        else:
            return self._search_rag(query, history)
