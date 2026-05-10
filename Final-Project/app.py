import streamlit as st
import requests
import pandas as pd
import uuid

# Configuration
st.set_page_config(page_title="Cosechados AI", layout="wide", initial_sidebar_state="expanded")

# --- Session Initialization ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Custom CSS for visual polish ---
st.markdown("""
<style>
    /* Increase global font size */
    html, body, [class*="st-"] {
        font-size: 1.15rem !important;
    }
    
    /* Make metrics massive */
    [data-testid="stMetricValue"] > div, [data-testid="stMetricValue"] {
        font-size: 4.5rem !important;
        color: #2b6cb0 !important;
        line-height: 1.1 !important;
    }
    [data-testid="stMetricLabel"] > div, [data-testid="stMetricLabel"] {
        font-size: 1.4rem !important;
        font-weight: bold !important;
    }
    
    .hero-text {
        font-size: 1.3rem;
        color: #4a5568;
        margin-bottom: 2rem;
        line-height: 1.6;
    }
    .highlight {
        color: #2b6cb0;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar Navigation ---
# Add actual company logo
st.sidebar.image("images/cosechados logo.png", use_container_width=True)

st.sidebar.markdown("""
**Cosechados is born from the need to eliminate abusive and unnecessary intermediaries and bring Spanish products closer to those who value the local and authentic.**

We bet on quality food, harvested by real farmers and delivered with transparency, without intermediate steps that make it more expensive or hide its origin. Only a direct and fair connection between who grows and who consumes.

🌐 **Discover more:** [cosechados.es](https://cosechados.es/)
---
""")

st.sidebar.markdown("## 🧭 Navigation")
page = st.sidebar.radio("Pages", ["Customer Assistant", "Admin Dashboard"], label_visibility="collapsed")

# ==========================================
# PAGE 1: CUSTOMER ASSISTANT
# ==========================================
if page == "Customer Assistant":
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🛠️ Actions")
        if st.button("Start New Conversation", use_container_width=True, type="primary"):
            st.session_state.messages = []
            st.session_state.session_id = str(uuid.uuid4())[:8]
            st.rerun()
            
        st.markdown("---")
        st.info("**About the Agent:**\n\nThis hybrid AI automatically routes your question to:\n- **RAG Engine:** Reads corporate PDFs.\n- **SQL Engine:** Reads real-time inventory.")

    # Main Header
    st.title("🚜 Cosechados Assistant")
    
    with st.expander("🤖 How does this AI Agent work?"):
        st.markdown("""
        This intelligent assistant is powered by a **Hybrid RAG (Retrieval-Augmented Generation) System**:
        - 📚 **Company Knowledge:** It reads through our corporate documents, farmer biographies, and policies using semantic search.
        - 📊 **Live Inventory:** It connects directly to our SQL database to give you real-time pricing and stock information.
        
        **Try asking questions in English, Spanish, or Danish!**
        - 🇪🇸 *¿Qué precio tienen los melones y de dónde vienen?*
        - 🇬🇧 *Tell me about the founders of the company.*
        - 🇩🇰 *Hvor meget koster tomat?*
        """)
        
    st.markdown("---")

    # Chat UI
    for msg in st.session_state.messages:
        avatar_type = "assistant" if msg["role"] == "assistant" else "user"
        with st.chat_message(msg["role"], avatar=avatar_type):
            st.markdown(msg["content"])
            if "citations" in msg and msg["citations"]:
                with st.expander("🔍 View Sources & SQL Queries"):
                    for idx, c in enumerate(msg["citations"]):
                        st.success(f"**Source {idx + 1}:**\n\n{c}")

    prompt = st.chat_input("E.g. What is our return policy? / ¿Qué precio tiene el melón?")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="user"):
            st.markdown(prompt)
            
        try:
            history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-5:-1]]
            payload = {
                "query": prompt, 
                "session_id": st.session_state.session_id, 
                "history": history
            }
            
            with st.spinner("🧠 Analyzing intent and querying databases..."):
                response = requests.post("http://127.0.0.1:8000/api/v1/chat", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "No answer")
                citations = data.get("citations", [])
                
                with st.chat_message("assistant", avatar="assistant"):
                    st.markdown(answer)
                    if citations:
                        with st.expander("🔍 View Sources & SQL Queries"):
                            for idx, c in enumerate(citations):
                                st.success(f"**Source {idx + 1}:**\n\n{c}")
                                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": answer,
                    "citations": citations
                })
            else:
                st.error("❌ Error from backend API.")
        except Exception as e:
            st.error(f"❌ Failed to connect to backend: {e}")

# ==========================================
# PAGE 2: ADMIN DASHBOARD
# ==========================================
elif page == "Admin Dashboard":
    st.title("⚙️ Operations Control Panel")
    st.markdown('<p class="hero-text">Monitor active customer interactions, track API usage, and manage the underlying <span class="highlight">Knowledge Graphs</span> and <span class="highlight">Vector Databases</span>.</p>', unsafe_allow_html=True)
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["💬 Conversation Analytics", "🗄️ Knowledge Base Viewer"])
    
    # --- TAB 1: Chat Logs ---
    with tab1:
        st.markdown("### Live Chat Monitor")
        st.caption("Select a conversation from the left to view the detailed interaction trace.")
        
        try:
            res_logs = requests.get("http://127.0.0.1:8000/api/v1/admin/logs")
            if res_logs.status_code == 200 and res_logs.json():
                logs = res_logs.json()
                
                # Metrics header with visual style
                unique_sessions = len(set([log["session_id"] for log in logs]))
                total_messages = len(logs)
                
                m1, m2, m3 = st.columns(3)
                m1.metric("👥 Active User Sessions", unique_sessions, delta="Live")
                m2.metric("Total AI Inferences", total_messages)
                m3.metric("Avg. Msgs per Session", round(total_messages/unique_sessions, 1) if unique_sessions > 0 else 0)
                st.markdown("---")
                
                # Engine Usage Stats
                tool_counts = {"rag": 0, "inventory": 0, "both": 0, "unknown": 0}
                for log in logs:
                    t = log.get("tool_used", "unknown")
                    if t in tool_counts:
                        tool_counts[t] += 1
                    else:
                        tool_counts["unknown"] += 1
                        
                st.markdown("#### 🧠 Engine Usage Statistics")
                e1, e2, e3 = st.columns(3)
                e1.metric("📚 RAG (Documents)", tool_counts["rag"])
                e2.metric("🗄️ SQL (Inventory)", tool_counts["inventory"])
                e3.metric("🔗 Hybrid (Both)", tool_counts["both"])
                st.markdown("---")
                
                # Group logs by session_id
                from collections import defaultdict
                sessions = defaultdict(list)
                for log in logs:
                    sessions[log["session_id"]].append(log)
                    
                # Order sessions by newest first
                session_summaries = []
                for s_id, msgs in sessions.items():
                    start_time = msgs[0]["timestamp"]
                    session_summaries.append((s_id, start_time))
                
                session_summaries.sort(key=lambda x: x[1], reverse=True)
                radio_options = [f"📅 {s[1][:16]} | ID: {s[0]}" for s in session_summaries]
                session_mapping = {opt: s[0] for opt, s in zip(radio_options, session_summaries)}
                
                # 2-Column layout: Telegram style
                col1, col2 = st.columns([1, 2.5])
                
                with col1:
                    st.markdown("**Select Session Trace:**")
                    selected_radio = st.radio("Active Sessions", radio_options, label_visibility="collapsed")
                    selected_session = session_mapping.get(selected_radio)
                    
                    st.write("")
                    if st.button("🔄 Refresh Data", use_container_width=True):
                        st.rerun()
                        
                with col2:
                    if selected_session:
                        st.info(f"**Session Identifier:** `{selected_session}`\n\nTracing conversation execution path...")
                        # Create a scrollable container for the chat
                        with st.container(height=500, border=True):
                            for msg in sessions[selected_session]:
                                with st.chat_message("user", avatar="user"):
                                    st.markdown(f"**User:** {msg['user_query']}")
                                with st.chat_message("assistant", avatar="assistant"):
                                    st.markdown(f"**AI Response:** {msg['bot_response']}")
                                    st.caption(f"🕒 *{msg['timestamp']}*")
            else:
                st.warning("No active conversations recorded in the database yet.")
        except Exception as e:
            st.error("Backend API is currently unreachable.")
            
    # --- TAB 2: Knowledge Base ---
    with tab2:
        colA, colB = st.columns(2)
        
        with colA:
            st.markdown("### 📚 Unstructured Data (RAG)")
            st.info("**Vector Store:** ChromaDB\n\n**Embedding Model:** text-embedding-3")
            st.markdown("Documents loaded into semantic search:")
            try:
                res_files = requests.get("http://127.0.0.1:8000/api/v1/admin/files")
                if res_files.status_code == 200:
                    files = res_files.json()
                    if files:
                        for f in files:
                            st.success(f"📄 **{f}** (Active)")
                    else:
                        st.warning("No PDF files found in data/ directory.")
            except:
                st.error("Could not load files.")
                
        with colB:
            st.markdown("### 🗄️ Structured Data (SQL)")
            st.info("**Relational DB:** SQLite (`inventory.db`)\n\n**Query Engine:** LangChain Text-to-SQL")
            st.markdown("Current inventory stock availability:")
            try:
                res_inv = requests.get("http://127.0.0.1:8000/api/v1/admin/inventory")
                if res_inv.status_code == 200:
                    inv_data = res_inv.json()
                    if inv_data:
                        df_inv = pd.DataFrame(inv_data)
                        df_inv.columns = ["Product", "Origin", "Price/Kg (€)", "Stock (Kg)"]
                        st.dataframe(df_inv, use_container_width=True, hide_index=True)
                    else:
                        st.warning("Inventory is empty.")
            except:
                st.error("Could not load inventory database.")
