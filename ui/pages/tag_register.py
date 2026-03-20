"""
ui/pages/tag_register.py — Master Tag Register.

Auto-loads on open. 18 columns with full FK resolution.
Features: text filter (all columns), Group By, XLSX export, row selection,
Property Values panel, Connected Documents panel, tag_status colour coding.
"""
from __future__ import annotations
import io
import re
from datetime import datetime

import pandas as pd
import streamlit as st
from ui.common import db_read, section

# ─── Ex-class classification ──────────────────────────────────────────────────
_NON_EX = re.compile(
    r"^(n/?a|n\.?a\.?|n-a|not[\s-]?applicable|non-?ex|none|—|-)$",
    re.IGNORECASE,
)


def _is_ex_class(value: str | None) -> bool:
    """Return True if value represents a real ATEX/IECEx ex-class designation."""
    if not value or not str(value).strip():
        return False
    v = str(value).strip()
    if _NON_EX.match(v):
        return False
    return v.lower().startswith("ex")


# ─── Status colour mapping ─────────────────────────────────────────────────────
_STATUS_COLORS: dict[str, str] = {
    "VOID":   "background-color: #3D1A1A; color: #F85149",
    "ACTIVE": "background-color: #1A2A3D; color: #58A6FF",
    "FUTURE": "background-color: #1C2128; color: #8B949E",
}
_DEFAULT_STATUS_COLOR = "background-color: #1B3A2A; color: #3FB950"


def _highlight_status(row: pd.Series) -> list[str]:
    style = _STATUS_COLORS.get(str(row.get("Tag Status", "")).upper(), _DEFAULT_STATUS_COLOR)
    return [style if col == "Tag Status" else "" for col in row.index]


# ─── Cached data loaders ───────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Loading tag register…")
def _load_tags() -> pd.DataFrame:
    """Load main tag register with resolved FKs."""
    df = db_read("""
        SELECT
            t.id                                             AS _tag_id,
            t.tag_name                                       AS "Tag Name",
            t.description                                    AS "Description",
            design_co.name                                   AS "Owner",
            t.tag_status                                     AS "Tag Status",
            po.name                                          AS "PO Number",
            pkg.code                                         AS "Package",
            c.name                                           AS "Class Name",
            t.mc_package_code                                AS "MC Package",
            a.code                                           AS "Area",
            u.code                                           AS "Process Unit",
            pt.tag_name                                      AS "Parent Tag",
            d.code                                           AS "Discipline Code",
            t.ex_class                                       AS "_ex_class_raw",
            t.serial_no                                      AS "Serial Number",
            COALESCE(td_cnt.cnt, 0)                          AS "Tag-Doc Count",
            t.sync_status                                    AS "Sync Status",
            TO_CHAR(t.sync_timestamp, 'YYYY-MM-DD HH24:MI') AS "Sync Timestamp"
        FROM project_core.tag t
        LEFT JOIN ontology_core.class              c         ON c.id = t.class_id
        LEFT JOIN reference_core.area              a         ON a.id = t.area_id
        LEFT JOIN reference_core.process_unit      u         ON u.id = t.process_unit_id
        LEFT JOIN reference_core.discipline        d         ON d.id = t.discipline_id
        LEFT JOIN project_core.tag                 pt        ON pt.id = t.parent_tag_id
        LEFT JOIN reference_core.company           design_co ON design_co.id = t.design_company_id
        LEFT JOIN reference_core.purchase_order    po        ON po.id = t.po_id
        LEFT JOIN reference_core.po_package        pkg       ON pkg.id = po.package_id
        LEFT JOIN (
            SELECT m.tag_id, COUNT(*) AS cnt
            FROM mapping.tag_document m
            JOIN project_core.document doc ON doc.id = m.document_id
            WHERE m.mapping_status = 'Active'
              AND doc.mdr_flag = TRUE
              AND doc.status != 'CAN'
              AND doc.object_status = 'Active'
            GROUP BY m.tag_id
        ) td_cnt ON td_cnt.tag_id = t.id
        WHERE t.object_status = 'Active'
        ORDER BY t.tag_name
    """)
    if df.empty:
        return df
    # Compute Is Ex Class from raw field
    df["Is Ex Class"] = df["_ex_class_raw"].apply(_is_ex_class)
    df = df.drop(columns=["_ex_class_raw"])
    return df


@st.cache_data(ttl=60, show_spinner=False)
def _load_properties(tag_id: str) -> pd.DataFrame:
    """Load property values for a selected tag, grouped by mapping_concept."""
    return db_read("""
        SELECT
            p.property_name         AS "Property",
            pv.value                AS "Value",
            pv.uom                  AS "UoM",
            p.mapping_concept_raw   AS _concept
        FROM project_core.property_value pv
        JOIN ontology_core.property p ON p.id = pv.property_id
        WHERE pv.tag_id = :tid
          AND p.mapping_concept_raw != 'Common'
        ORDER BY
            CASE p.mapping_concept_raw
                WHEN 'Functional Physical' THEN 1
                WHEN 'Functional' THEN 2
                WHEN 'Physical' THEN 3
                ELSE 4
            END, p.property_name
    """, {"tid": str(tag_id)})


@st.cache_data(ttl=60, show_spinner=False)
def _load_documents(tag_id: str) -> pd.DataFrame:
    """Load connected documents for a selected tag."""
    return db_read("""
        SELECT
            doc.doc_number                      AS "Doc Number",
            doc.title                           AS "Title",
            doc.rev                             AS "Rev",
            doc.status                          AS "Status",
            co.name                             AS "Company",
            doc.doc_type_code                   AS "Type",
            doc.rev_author                      AS "Author",
            TO_CHAR(doc.rev_date, 'YYYY-MM-DD') AS "Rev Date"
        FROM mapping.tag_document m
        JOIN project_core.document doc ON doc.id = m.document_id
        LEFT JOIN reference_core.company co ON co.id = doc.company_id
        WHERE m.tag_id = :tid
          AND doc.mdr_flag = TRUE
          AND doc.status != 'CAN'
          AND doc.object_status = 'Active'
        ORDER BY doc.doc_number
    """, {"tid": str(tag_id)})


# ─── Page render ──────────────────────────────────────────────────────────────
def render() -> None:
    st.markdown("### 🗂 Master Tag Register")
    st.caption("Active tags · `project_core.tag` · auto-refreshes every 5 min")

    df = _load_tags()

    if df.empty:
        st.warning("No active tags found in project_core.tag.")
        return

    # ── Filters ────────────────────────────────────────────────────────────────
    section("Filters & Grouping")
    filter_col, clear_col, groupby_col = st.columns([4, 1, 3])

    with filter_col:
        filter_text = st.text_input(
            "Filter (any field)",
            key="tr_filter",
            placeholder="Type to filter — applies to all columns",
        )
    with clear_col:
        st.write("")
        if st.button("✕ Clear", key="tr_clear"):
            st.session_state["tr_filter"] = ""
            st.rerun()

    with groupby_col:
        groupby = st.selectbox(
            "Group by",
            ["— None —"] + [c for c in df.columns if c not in ("_tag_id",)],
            key="tr_groupby",
        )

    # Apply text filter across all columns
    if filter_text:
        mask = df.astype(str).apply(
            lambda col: col.str.contains(filter_text, case=False, na=False)
        ).any(axis=1)
        df_display = df[mask].copy()
    else:
        df_display = df.copy()

    # Apply group-by sort
    if groupby != "— None —" and groupby in df_display.columns:
        df_display = df_display.sort_values(groupby)

    st.caption(f"{len(df_display):,} of {len(df):,} tags")

    # ── XLSX Export ────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df_display.drop(columns=["_tag_id"], errors="ignore").to_excel(
            w, index=False, sheet_name="Master Tag Register"
        )
    st.download_button(
        "⬇ Export to XLSX",
        data=buf.getvalue(),
        file_name=f"tag_register_{datetime.now():%Y%m%d_%H%M}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="tr_dl",
    )

    # ── Main table with row selection ─────────────────────────────────────────
    selected = st.dataframe(
        df_display.drop(columns=["_tag_id"], errors="ignore").style.apply(
            _highlight_status, axis=1
        ),
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="tr_table",
    )

    selected_idx = selected.selection.rows[0] if selected.selection.rows else None
    selected_tag_id = (
        df_display.iloc[selected_idx]["_tag_id"] if selected_idx is not None else None
    )
    selected_tag_name = (
        df_display.iloc[selected_idx]["Tag Name"] if selected_idx is not None else "—"
    )

    # ── Property Values panel ─────────────────────────────────────────────────
    with st.expander(f"📐 Property Values — {selected_tag_name}", expanded=True):
        if selected_tag_id is not None:
            df_props = _load_properties(str(selected_tag_id))
            if not df_props.empty:
                for concept in ["Functional Physical", "Functional", "Physical"]:
                    subset = df_props[df_props["_concept"] == concept].drop(columns=["_concept"])
                    if not subset.empty:
                        st.caption(f"**{concept}**")
                        st.dataframe(subset, use_container_width=True, hide_index=True)
            else:
                st.caption("No property values for this tag.")
        else:
            st.caption("Select a tag in the table above.")

    # ── Connected Documents panel ─────────────────────────────────────────────
    with st.expander(f"📄 Connected Documents — {selected_tag_name}", expanded=False):
        if selected_tag_id is not None:
            df_docs = _load_documents(str(selected_tag_id))
            if not df_docs.empty:
                st.caption(f"{len(df_docs)} document(s)")
                st.dataframe(df_docs, use_container_width=True, hide_index=True)
            else:
                st.caption("No connected documents for this tag.")
        else:
            st.caption("Select a tag in the table above.")
