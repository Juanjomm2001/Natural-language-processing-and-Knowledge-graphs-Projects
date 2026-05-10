import pytest
from fastapi.testclient import TestClient
from main import app, init_logs_db
import sqlite3
import os

client = TestClient(app)

def test_init_logs_db():
    """Test that the database initialization creates the file and table correctly."""
    # Run the init function
    init_logs_db()
    
    # Verify the database file exists
    assert os.path.exists("data/chat_logs.db")
    
    # Verify the table exists and has the correct columns
    conn = sqlite3.connect("data/chat_logs.db")
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_sessions'")
    table_exists = c.fetchone()
    
    c.execute("PRAGMA table_info(chat_sessions)")
    columns = [info[1] for info in c.fetchall()]
    conn.close()
    
    assert table_exists is not None
    assert "session_id" in columns
    assert "tool_used" in columns

def test_get_inventory():
    """Test the admin inventory endpoint."""
    response = client.get("/api/v1/admin/inventory")
    assert response.status_code == 200
    data = response.json()
    
    # It should return a list (empty or with products)
    assert isinstance(data, list)
    if len(data) > 0:
        # If there are products, check the expected structure
        assert "product_name" in data[0]
        assert "stock_kg" in data[0]

def test_get_files():
    """Test the admin files endpoint."""
    response = client.get("/api/v1/admin/files")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_logs():
    """Test the admin logs endpoint."""
    response = client.get("/api/v1/admin/logs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "session_id" in data[0]
        assert "user_query" in data[0]

def test_chat_endpoint_mocked(mocker):
    """
    Test the chat endpoint by mocking the RAG agent's ask method.
    This ensures we don't consume real LLM API credits during unit testing.
    """
    # 1. Define a fake response that the agent would theoretically return
    fake_response = {
        "answer": "This is a mocked answer for testing.",
        "citations": ["Mocked citation"],
        "sources": ["Mocked source"],
        "tool_used": "rag"
    }
    
    # 2. Patch the 'rag.ask' method in the main module to return our fake response
    mocker.patch("main.rag.ask", return_value=fake_response)
    
    # 3. Simulate an incoming HTTP request
    payload = {
        "query": "Test query?",
        "session_id": "test_unit_123",
        "history": []
    }
    
    response = client.post("/api/v1/chat", json=payload)
    
    # 4. Assert the API behaves correctly
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "This is a mocked answer for testing."
    assert data["tool_used"] == "rag"
    
    # 5. Assert that the conversation was successfully logged in the DB
    conn = sqlite3.connect("data/chat_logs.db")
    c = conn.cursor()
    c.execute("SELECT user_query, bot_response FROM chat_sessions WHERE session_id = ?", ("test_unit_123",))
    row = c.fetchone()
    conn.close()
    
    assert row is not None
    assert row[0] == "Test query?"
    assert row[1] == "This is a mocked answer for testing."
