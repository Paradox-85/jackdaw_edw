"""
ui/pages/feedback.py — Feedback & Enhancement Request form.

All authenticated users can submit feedback.
Admin users additionally see the full submissions table with status filter.
Submissions are stored in app_core.ui_feedback (admin engine — viewer has no INSERT rights).
"""
from __future__ import annotations

import streamlit as st

from ui.common import db_read, db_write, get_current_user, is_admin, section


def render() -> None:
    """Render the feedback submission form and admin submissions view."""
    section("Feedback & Enhancement Requests")
    st.caption("Submit bug reports, feature requests, or questions to the development team.")

    user = get_current_user()
    user_id = user["id"] if user and "id" in user else None
    username = user["username"] if user else "anonymous"

    # ── Submission form ───────────────────────────────────────────────────────
    with st.form("feedback_form", clear_on_submit=True):
        ftype = st.selectbox(
            "Type",
            ["Bug", "Enhancement", "Question"],
            help="Bug = something is broken · Enhancement = new feature idea · Question = general query",
        )
        title = st.text_input("Title", max_chars=200, placeholder="Brief summary of your feedback")
        body  = st.text_area(
            "Description",
            height=150,
            placeholder="Describe the issue or request in detail. "
                        "For bugs: include steps to reproduce. "
                        "For enhancements: describe the expected behaviour.",
        )
        submitted = st.form_submit_button("Submit", type="primary", use_container_width=True)

    if submitted:
        if not title.strip():
            st.error("Please provide a title.")
        elif not body.strip():
            st.error("Please provide a description.")
        else:
            # Resolve user_id from DB if not in session (session stores username only)
            resolved_id = user_id
            if resolved_id is None:
                id_df = db_read(
                    "SELECT id FROM app_core.ui_user WHERE username = :u",
                    {"u": username},
                    admin=True,
                )
                resolved_id = str(id_df.iloc[0]["id"]) if not id_df.empty else None

            ok = db_write(
                """
                INSERT INTO app_core.ui_feedback
                    (user_id, username, feedback_type, title, body)
                VALUES (:uid, :uname, :ftype, :title, :body)
                """,
                {
                    "uid":   resolved_id,
                    "uname": username,
                    "ftype": ftype,
                    "title": title.strip(),
                    "body":  body.strip(),
                },
            )
            if ok:
                st.success("✅ Feedback submitted. Thank you!")

    # ── Admin: all submissions ────────────────────────────────────────────────
    if is_admin():
        st.markdown("---")
        section("All Submissions (Admin)")

        status_filter = st.selectbox(
            "Filter by status",
            ["All", "Open", "In Progress", "Done", "Rejected"],
            key="fb_status_filter",
        )

        _BASE_SELECT = """
            SELECT
                TO_CHAR(f.created_at, 'YYYY-MM-DD HH24:MI') AS "Submitted",
                f.username          AS "User",
                f.feedback_type     AS "Type",
                f.title             AS "Title",
                f.body              AS "Description",
                f.status            AS "Status"
            FROM app_core.ui_feedback f
        """
        if status_filter == "All":
            df = db_read(_BASE_SELECT + " ORDER BY f.created_at DESC", {}, admin=True)
        else:
            df = db_read(
                _BASE_SELECT + " WHERE f.status = :status ORDER BY f.created_at DESC",
                {"status": status_filter},
                admin=True,
            )

        if df.empty:
            st.info("No submissions found.")
        else:
            st.caption(f"{len(df):,} submission(s)")
            st.dataframe(df, use_container_width=True, hide_index=True)
