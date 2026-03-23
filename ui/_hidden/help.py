"""Help & Guidelines page — renders docs/help.md as formatted Markdown."""
from pathlib import Path

import streamlit as st

from ui.common import section


def render() -> None:
    """Render the help documentation page."""
    section("Help & Guidelines")

    help_path = Path(__file__).parent.parent.parent / "docs" / "help.md"

    if not help_path.exists():
        st.warning(f"Help file not found: `{help_path}`")
        st.info("Create `docs/help.md` to add documentation here.")
        return

    content = help_path.read_text(encoding="utf-8")
    st.markdown(content)
