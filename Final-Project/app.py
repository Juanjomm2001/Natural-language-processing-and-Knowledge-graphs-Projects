import streamlit as st
import requests

st.set_page_config(page_title="Cosechados AI", layout="wide")

# Sidebar
with st.sidebar:
    st.title("Cosechados AI")
    st.markdown("---")
    st.markdown("""
    **DTU - NLP & Knowledge Graphs Project**
    
    Welcome to the Cosechados Hybrid AI Agent.
    
    This assistant combines two data engines:
    - **Unstructured Data (RAG)**: Extracts info from corporate PDFs, farmer bios, and policies using semantic search.
    - **Structured Data (SQL)**: Queries our real-time inventory database for stock and dynamic pricing.
    
    The system automatically routes your query to the appropriate database, or combines both to answer complex questions.
    """)
    st.markdown("---")
    st.markdown("### Examples to try:")
    st.markdown("- *¿De dónde vienen vuestras manzanas?*")
    st.markdown("- *Tell me about the founders and the price of Melon.*")
    st.markdown("- *Hvor meget koster tomat?*")
    st.markdown("---")
    if st.button("Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("Cosechados - Agricultural Assistant")
st.markdown("*Ask about our farmers, delivery policies, or request a budget for fresh products.*")
st.markdown("---")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    # Use standard default avatars (no emojis)
    avatar_type = "assistant" if msg["role"] == "assistant" else "user"
    with st.chat_message(msg["role"], avatar=avatar_type):
        st.markdown(msg["content"])
        if "citations" in msg and msg["citations"]:
            with st.expander("Verbatim Citations & SQL Queries"):
                for idx, c in enumerate(msg["citations"]):
                    st.info(f"**Source {idx + 1}:**\n\n{c}")

prompt = st.chat_input("E.g. What is the return policy? / ¿Cuánto valen las manzanas?")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="user"):
        st.markdown(prompt)
        
    try:
        # Pass the last 4 messages (excluding the current one) as history for context
        history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-5:-1]]
        
        with st.spinner("Processing query across unstructured and structured sources..."):
            response = requests.post("http://127.0.0.1:8000/api/v1/chat", json={"query": prompt, "history": history})
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer", "No answer")
            citations = data.get("citations", [])
            
            with st.chat_message("assistant", avatar="assistant"):
                st.markdown(answer)
                if citations:
                    with st.expander("Verbatim Citations & SQL Queries"):
                        for idx, c in enumerate(citations):
                            st.info(f"**Source {idx + 1}:**\n\n{c}")
                            
            st.session_state.messages.append({
                "role": "assistant", 
                "content": answer,
                "citations": citations
            })
        else:
            st.error("Error from backend API.")
    except Exception as e:
        st.error(f"Failed to connect to backend: {e}")
