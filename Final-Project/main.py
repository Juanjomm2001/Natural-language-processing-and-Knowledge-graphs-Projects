from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
import sqlite3
import os
from rag_agent import CosechadosHybridAgent

app = FastAPI(title="Cosechados Hybrid API")
rag = CosechadosHybridAgent()

def init_logs_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect("data/chat_logs.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chat_sessions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  session_id TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
                  user_query TEXT, 
                  bot_response TEXT,
                  tool_used TEXT)''')
    
    # Ensure backward compatibility if table existed before without tool_used
    c.execute("PRAGMA table_info(chat_sessions)")
    columns = [info[1] for info in c.fetchall()]
    if "tool_used" not in columns:
        c.execute("ALTER TABLE chat_sessions ADD COLUMN tool_used TEXT")
        
    conn.commit()
    conn.close()

init_logs_db()

class ChatRequest(BaseModel):
    query: str
    session_id: str
    history: List[Dict[str, Any]] = []

@app.post("/api/v1/chat")
def chat_endpoint(request: ChatRequest):
    result = rag.ask(request.query, request.history)
    
    # Log the conversation with the session ID and tool used
    try:
        conn = sqlite3.connect("data/chat_logs.db")
        c = conn.cursor()
        c.execute("INSERT INTO chat_sessions (session_id, user_query, bot_response, tool_used) VALUES (?, ?, ?, ?)", 
                  (request.session_id, request.query, result["answer"], result.get("tool_used", "unknown")))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging chat: {e}")
    
    return result

@app.get("/api/v1/admin/logs")
def get_logs():
    try:
        conn = sqlite3.connect("data/chat_logs.db")
        c = conn.cursor()
        # Order by timestamp ASC so they appear chronologically in the chat
        c.execute("SELECT session_id, timestamp, user_query, bot_response, tool_used FROM chat_sessions ORDER BY timestamp ASC")
        rows = c.fetchall()
        conn.close()
        return [{"session_id": r[0], "timestamp": r[1], "user_query": r[2], "bot_response": r[3], "tool_used": r[4]} for r in rows]
    except Exception:
        return []

@app.get("/api/v1/admin/inventory")
def get_inventory():
    try:
        conn = sqlite3.connect("data/inventory.db")
        c = conn.cursor()
        c.execute("SELECT product_name, origin, price_per_kg, stock_kg FROM inventory")
        rows = c.fetchall()
        conn.close()
        return [{"product_name": r[0], "origin": r[1], "price_per_kg": r[2], "stock_kg": r[3]} for r in rows]
    except Exception:
        return []

@app.get("/api/v1/admin/files")
def get_files():
    data_dir = "data"
    if not os.path.exists(data_dir):
        return []
    files = [f for f in os.listdir(data_dir) if f.endswith(".pdf")]
    return files
