"""ui/pages/llm_chat.py"""
from __future__ import annotations
import httpx
import streamlit as st
from ui.common import OLLAMA_URL, ollama_models


def _chat(model: str, messages: list, system: str) -> str:
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    try:
        r = httpx.post(f"{OLLAMA_URL}/api/chat",
                       json={"model": model, "messages": msgs, "stream": False},
                       timeout=120)
        return r.json()["message"]["content"]
    except Exception as e:
        return f"⚠ Ollama error: {e}"


def render() -> None:
    st.markdown("### 🤖 LLM Chat")
    st.caption(f"Local inference · Ollama · RTX 3090 · `{OLLAMA_URL}`")
    st.info("💡 Phase 1: general Q&A about EDW concepts. NL-to-SQL planned for Phase 3.")

    if "chat_hist" not in st.session_state:
        st.session_state["chat_hist"] = []

    models = ollama_models()
    c1, c2, c3 = st.columns([2, 3, 1])
    model = c1.selectbox("Model", models if models else ["(no models)"], key="llm_m")
    sys_p = c2.text_input(
        "System prompt",
        value="You are a data engineering assistant for Jackdaw EDW (Plant JDA, North Sea). "
              "Answer questions about tags, documents, EIS exports, and data quality. "
              "Do NOT generate SQL queries.",
        key="llm_sys",
    )
    if c3.button("🗑", use_container_width=True, key="llm_clr"):
        st.session_state["chat_hist"] = []
        st.rerun()

    for msg in st.session_state["chat_hist"]:
        role = "YOU" if msg["role"] == "user" else f"🤖 {model}"
        css = ("background:#1C2128;border-left:3px solid #58A6FF"
               if msg["role"] == "user"
               else "background:#0D1117;border-left:3px solid #3FB950")
        st.markdown(
            f'<div style="{css};padding:10px 14px;margin:6px 0;border-radius:4px;'
            f'font-size:13px;line-height:1.6">'
            f'<div style="font-size:10px;color:#8B949E;font-weight:600;margin-bottom:4px">{role}</div>'
            f'{msg["content"]}</div>',
            unsafe_allow_html=True,
        )

    prompt = st.chat_input("Ask about EDW data, tags, exports, validation…")
    if prompt and models:
        st.session_state["chat_hist"].append({"role": "user", "content": prompt})
        with st.spinner("Thinking…"):
            reply = _chat(model, st.session_state["chat_hist"], sys_p)
        st.session_state["chat_hist"].append({"role": "assistant", "content": reply})
        st.rerun()

    if not models:
        st.warning(f"Ollama unreachable at `{OLLAMA_URL}`.")
