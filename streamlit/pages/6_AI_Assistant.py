"""🤖 AI Assistant — Ask questions about fantasy football data."""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.api import ask_ai

st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")
st.title("🤖 Fantasy Football AI Assistant")

st.markdown("""
Ask any question about fantasy football and get answers backed by real data.  
The AI has access to player stats from 2021–2025 across Standard, Half-PPR, and PPR formats.
""")

# Example questions
with st.expander("💡 Example questions"):
    st.markdown("""
    - Who was the best running back in 2024?
    - Compare Josh Allen and Lamar Jackson in 2025
    - Which wide receivers are trending up recently?
    - Who should I target on the waiver wire?
    - What quarterbacks had the most consistent seasons in 2024?
    - How did Saquon Barkley perform in 2024?
    """)

st.markdown("---")

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("data_context"):
            with st.expander("📊 Data used for this answer"):
                st.code(msg["data_context"], language=None)

# Chat input
if prompt := st.chat_input("Ask about fantasy football..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing data..."):
            result = ask_ai(prompt)

        if result:
            answer = result["answer"]
            data_context = result.get("data_context")
            st.markdown(answer)
            if data_context:
                with st.expander("📊 Data used for this answer"):
                    st.code(data_context, language=None)
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "data_context": data_context,
            })
        else:
            st.error("Failed to get a response. Check that the API is running.")

# Clear chat button
if st.session_state.messages:
    if st.sidebar.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()
