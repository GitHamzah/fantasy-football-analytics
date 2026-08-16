"""AI Analyst — ask anything in plain English."""

import streamlit as st

from utils.api import ask_ai
from utils.components import inject_custom_css, section_header, sidebar

st.set_page_config(page_title="AI Analyst", page_icon="🤖", layout="wide")
inject_custom_css()

sidebar(show_season=False)

st.markdown(
    '<div style="font-size:1.9rem;font-weight:800;color:#f1f5f9">🤖 AI Analyst</div>'
    '<div style="color:#94a3b8;margin-bottom:22px">'
    'Ask a question — answers are grounded in real numbers pulled from the warehouse, '
    'not guessed.</div>',
    unsafe_allow_html=True,
)

if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = []


# --- Quick prompts ------------------------------------------------------

section_header("Quick questions")

QUICK_PROMPTS = [
    "Best waiver pickups this week",
    "Draft strategy for PPR",
    "Top 5 RBs for 2026",
    "Which defense should I stream?",
]

pending = None
cols = st.columns(len(QUICK_PROMPTS))
for col, prompt in zip(cols, QUICK_PROMPTS):
    with col:
        if st.button(prompt, use_container_width=True, key=f"quick_{prompt}"):
            pending = prompt

st.write("")


# --- Chat history -------------------------------------------------------

for msg in st.session_state.ai_messages:
    with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "🧑"):
        st.markdown(msg["content"])
        if msg.get("data_context"):
            with st.expander("Data the model was given"):
                st.code(msg["data_context"], language="text")


# --- Input --------------------------------------------------------------

typed = st.chat_input("Ask about players, matchups, draft strategy...")
question = pending or typed

if question:
    st.session_state.ai_messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Pulling data and thinking..."):
            result = ask_ai(question)

        if not result:
            answer = (
                "I could not reach the AI service. Check that the API is running "
                "and that a Gemini API key is configured."
            )
            st.warning(answer)
            st.session_state.ai_messages.append(
                {"role": "assistant", "content": answer}
            )
        else:
            answer = result.get("answer", "No answer returned.")
            st.markdown(answer)
            context = result.get("data_context")
            if context:
                with st.expander("Data the model was given"):
                    st.code(context, language="text")
            st.session_state.ai_messages.append({
                "role": "assistant",
                "content": answer,
                "data_context": context,
            })

if st.session_state.ai_messages:
    st.write("")
    if st.button("Clear conversation"):
        st.session_state.ai_messages = []
        st.rerun()
