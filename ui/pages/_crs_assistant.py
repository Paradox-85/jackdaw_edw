"""ui/pages/crs_assistant.py — CRS Assistant. Phase 1: stub."""
from __future__ import annotations
import streamlit as st
from ui.common import wip, section


def render() -> None:
    st.markdown("### 📎 CRS Assistant")
    st.caption("Client Review Sheet parser · AI-generated replies · Export reply XLSX")
    wip("CRS Assistant — Planned for Phase 2")
    st.markdown("""
    **Planned functionality:**
    - Upload CRS files (XLSX / CSV)
    - AI agent (Ollama) parses each row and generates technical replies
    - Review and edit replies in browser
    - Export: per-file with `-reply` suffix, or combined output
    """)
