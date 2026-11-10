"""
VendorFlow AI - UI theme layer.

Pure presentation: no business logic. Restyles Streamlit's native widgets
(forms, uploader, expanders, buttons, tables) so every page picks up the new
look automatically, and provides three components used by app.py:
    apply_theme(), render_sidebar(), render_overview(runs)
"""

from datetime import datetime
from html import escape

import altair as alt
import pandas as pd
import streamlit as st


# ------------------------------------------------------------
# DESIGN TOKENS
# ------------------------------------------------------------

STATUS_COLORS = {
    "Approved": "#2dd4bf",
    "Pending": "#f2b84b",
    "Rejected": "#ff7a6b",
    "Processing Error": "#b69cff",
    "Submitted": "#7aa2f7",
}

NAV = {
    "Overview": "◧",
    "New Vendor": "＋",
    "Live Execution": "◉",
    "Run History": "☰",
}

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=DM+Sans:wght@400;500;600&display=swap');

:root{
  --ink:#0c1519; --panel:#132128; --panel-2:#182a32; --line:#233842;
  --text:#e6f0ee; --muted:#8aa0a6; --gold:#f2b84b; --teal:#2dd4bf; --coral:#ff7a6b;
}
html, body, [class*="css"], .stApp { font-family:'DM Sans',system-ui,sans-serif; }
.stApp { background: var(--ink); color: var(--text); }
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility:hidden; }
.block-container { max-width:1400px; padding-top:2rem; padding-bottom:4rem; }

h1,h2,h3,h4 { font-family:'Bricolage Grotesque',sans-serif; letter-spacing:-.01em; color:var(--text); }
h1 { font-weight:700; font-size:2.1rem !important; }
h2,h3 { font-weight:500; }
[data-testid="stCaptionContainer"], .stCaption { color:var(--muted) !important; }
hr { border-color:var(--line) !important; }

/* sidebar */
[data-testid="stSidebar"] { background:#0a1114; border-right:1px solid var(--line); }
[data-testid="stSidebar"] [role="radiogroup"] { gap:.25rem; }
[data-testid="stSidebar"] [role="radiogroup"] label {
  padding:.6rem .85rem; border-radius:10px; width:100%; cursor:pointer; transition:background .15s;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background:var(--panel); }
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display:none; }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
  background:var(--panel-2); box-shadow: inset 3px 0 0 var(--gold);
}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p { color:var(--gold); font-weight:600; }

/* forms, inputs, uploader */
[data-testid="stForm"] {
  background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:1.5rem;
}
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, textarea {
  background:var(--ink) !important; border:1px solid var(--line) !important; border-radius:10px !important;
}
div[data-baseweb="input"]:focus-within > div { border-color:var(--gold) !important; }
label p { color:var(--muted); font-weight:500; }
[data-testid="stFileUploaderDropzone"] {
  background:var(--ink); border:1.5px dashed #34505c; border-radius:14px; padding:1.5rem;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color:var(--gold); }

/* buttons */
.stButton button, [data-testid="stFormSubmitButton"] button {
  border-radius:10px; font-weight:600; border:1px solid var(--line); background:var(--panel-2); color:var(--text);
}
button[kind^="primary"] {
  background:var(--gold) !important; color:#1a1405 !important; border:none !important;
  box-shadow:0 6px 18px rgba(242,184,75,.22); transition:transform .12s, box-shadow .12s;
}
button[kind^="primary"]:hover { transform:translateY(-1px); box-shadow:0 10px 24px rgba(242,184,75,.3); }

/* expanders, alerts, native metrics, tables */
[data-testid="stExpander"] { background:var(--panel); border:1px solid var(--line); border-radius:14px; }
[data-testid="stExpander"] summary:hover { color:var(--gold); }
[data-testid="stAlert"] { border-radius:12px; border:1px solid var(--line); }
[data-testid="stMetric"] {
  background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:16px 18px;
}
[data-testid="stMetricLabel"] { color:var(--muted); }
[data-testid="stMetricValue"] { font-family:'Bricolage Grotesque',sans-serif; color:var(--text); }
[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:14px; overflow:hidden; }

/* custom components */
.vf-brand { display:flex; align-items:center; gap:.75rem; padding:.25rem 0 1.25rem; }
.vf-mark { width:40px; height:40px; border-radius:12px; background:var(--gold); color:#1a1405;
  display:grid; place-items:center; font:700 1.25rem 'Bricolage Grotesque'; }
.vf-brand b { font:700 1.15rem 'Bricolage Grotesque'; display:block; line-height:1.1; }
.vf-brand span { color:var(--muted); font-size:.8rem; }
.vf-note { background:var(--panel); border:1px solid var(--line); border-radius:12px;
  padding:.8rem .95rem; color:var(--muted); font-size:.82rem; line-height:1.45; }

.vf-hero { display:grid; grid-template-columns:1fr auto; gap:2rem; align-items:center;
  background:var(--panel); border:1px solid var(--line); border-radius:22px; padding:1.9rem 2.1rem; margin-bottom:1.1rem; }
.vf-hero h1 { margin:0 0 .35rem; }
.vf-hero p { margin:0; color:var(--muted); max-width:56ch; line-height:1.5; }
.vf-hero .vf-date { color:var(--gold); font-weight:600; font-size:.9rem; margin-bottom:.5rem; display:block; }
.vf-ring { width:128px; height:128px; border-radius:50%; display:grid; place-items:center; }
.vf-ring > div { width:98px; height:98px; border-radius:50%; background:var(--panel);
  display:grid; place-items:center; text-align:center; }
.vf-ring strong { font:700 1.6rem 'Bricolage Grotesque'; line-height:1; display:block; }
.vf-ring small { color:var(--muted); font-size:.72rem; }

.vf-strip { display:grid; grid-template-columns:repeat(5,1fr); background:var(--panel);
  border:1px solid var(--line); border-radius:16px; margin-bottom:1.4rem; overflow:hidden; }
.vf-stat { padding:1.1rem 1.3rem; border-right:1px solid var(--line); border-top:3px solid var(--c); }
.vf-stat:last-child { border-right:none; }
.vf-stat span { color:var(--muted); font-size:.85rem; }
.vf-stat strong { display:block; font:700 2rem 'Bricolage Grotesque'; margin-top:.15rem; }

.vf-panel { background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:1.2rem 1.4rem; }
.vf-panel h3 { margin:0 0 .2rem; font-size:1.1rem; }
.vf-panel p { margin:0; color:var(--muted); font-size:.85rem; }
.vf-big { font:700 2.4rem 'Bricolage Grotesque'; }

.vf-table-wrap { overflow-x:auto; border:1px solid var(--line); border-radius:16px; background:var(--panel); }
.vf-table { width:100%; border-collapse:collapse; font-size:.88rem; }
.vf-table th { text-align:left; color:var(--muted); font-weight:500; padding:.8rem 1rem; border-bottom:1px solid var(--line); }
.vf-table td { padding:.8rem 1rem; border-bottom:1px solid #1b2e36; max-width:220px;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.vf-table tr:last-child td { border-bottom:none; }
.vf-table tbody tr:hover { background:var(--panel-2); }
.vf-badge { display:inline-block; padding:.18rem .65rem; border-radius:999px; font-size:.78rem; font-weight:600;
  color:var(--c); background:color-mix(in srgb, var(--c) 14%, transparent);
  border:1px solid color-mix(in srgb, var(--c) 35%, transparent); }

@media (max-width:900px){
  .vf-hero{grid-template-columns:1fr;} .vf-strip{grid-template-columns:repeat(2,1fr);}
}
"""


def _html(markup: str):
    """Render HTML; strips indentation/blank lines so Markdown never treats it as a code block."""
    flat = "\n".join(line.strip() for line in markup.splitlines() if line.strip())
    st.markdown(flat, unsafe_allow_html=True)


# ------------------------------------------------------------
# PUBLIC COMPONENTS
# ------------------------------------------------------------

def apply_theme():
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    """Optional: use on any page in place of st.title + st.caption."""
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def render_sidebar() -> str:
    with st.sidebar:
        _html("""
        <div class="vf-brand"><div class="vf-mark">V</div>
        <div><b>VendorFlow AI</b><span>Intelligent Vendor Operations</span></div></div>
        """)

        page = st.radio(
            "Workspace",
            list(NAV),
            format_func=lambda name: f"{NAV[name]}   {name}",
            label_visibility="collapsed",
        )

        st.divider()
        _html('<div class="vf-note">Upload PAN, GST and bank proof. '
              'AI reads every page, you confirm, the workflow decides.</div>')
    return page


def _badge(status) -> str:
    color = STATUS_COLORS.get(str(status), "#8aa0a6")
    return f'<span class="vf-badge" style="--c:{color}">{escape(str(status))}</span>'


def _activity_table(df: pd.DataFrame, limit: int = 8) -> str:
    cols = list(df.columns)[:7]
    head = "".join(f"<th>{escape(str(c).replace('_', ' ').capitalize())}</th>" for c in cols)
    rows = ""
    for _, row in df.head(limit).iterrows():
        cells = "".join(
            f"<td>{_badge(row[c]) if c == 'status' else escape(str(row[c]))}</td>" for c in cols
        )
        rows += f"<tr>{cells}</tr>"
    return (f'<div class="vf-table-wrap"><table class="vf-table"><thead><tr>{head}</tr></thead>'
            f"<tbody>{rows}</tbody></table></div>")


def render_overview(runs: list):
    total = len(runs)
    count = lambda s: sum(r["status"] == s for r in runs)
    approved, pending, rejected = count("Approved"), count("Pending"), count("Rejected")
    errors, submitted = count("Processing Error"), count("Submitted")
    rate = (approved / total * 100) if total else 0
    docs = sum(r.get("document_count", 0) for r in runs)

    # --- hero: leads with what needs attention ---
    if not total:
        headline, lede = "No vendors yet", "Add your first vendor and the AI will read their documents for you."
    elif pending:
        noun = "vendor needs" if pending == 1 else "vendors need"
        headline, lede = f"{pending} {noun} your review", "Open Run History and filter by Pending to pick up where you left off."
    else:
        headline, lede = "Nothing waiting on you", "Every submission has a final outcome. New vendors will appear here."

    today = datetime.now().strftime("%A, %d %B")
    ring = f"conic-gradient(var(--teal) {rate:.1f}%, #233842 0)"
    _html(f"""
    <div class="vf-hero"><div>
    <span class="vf-date">{today}</span>
    <h1>{escape(headline)}</h1><p>{escape(lede)}</p></div>
    <div class="vf-ring" style="background:{ring}"><div><div>
    <strong>{rate:.0f}%</strong><small>approved</small></div></div></div></div>
    """)

    # --- one connected stat strip ---
    stats = [("Total submissions", total, "#7aa2f7"), ("Approved", approved, STATUS_COLORS["Approved"]),
             ("Pending", pending, STATUS_COLORS["Pending"]), ("Rejected", rejected, STATUS_COLORS["Rejected"]),
             ("Processing errors", errors, STATUS_COLORS["Processing Error"])]
    _html('<div class="vf-strip">' + "".join(
        f'<div class="vf-stat" style="--c:{c}"><span>{l}</span><strong>{v}</strong></div>' for l, v, c in stats
    ) + "</div>")

    # --- charts + insights ---
    left, right = st.columns([3, 2], gap="large")

    with left:
        _html('<div class="vf-panel"><h3>Where vendors stand</h3><p>Share of submissions by status</p></div>')
        if total:
            data = pd.DataFrame({
                "Status": ["Approved", "Pending", "Rejected", "Processing Error", "Submitted"],
                "Count": [approved, pending, rejected, errors, submitted],
            })
            data = data[data["Count"] > 0]
            donut = (
                alt.Chart(data)
                .mark_arc(innerRadius=70, outerRadius=108, cornerRadius=5, padAngle=0.025)
                .encode(
                    theta="Count:Q",
                    color=alt.Color(
                        "Status:N",
                        scale=alt.Scale(domain=list(STATUS_COLORS), range=list(STATUS_COLORS.values())),
                        legend=alt.Legend(orient="right", title=None, labelColor="#c5d3d6", labelFontSize=13),
                    ),
                    tooltip=["Status", "Count"],
                )
                .properties(height=250)
                .configure(background="transparent")
                .configure_view(strokeWidth=0)
            )
            st.altair_chart(donut, use_container_width=True)
        else:
            st.info("Submit your first vendor to see the breakdown.")

    with right:
        _html(f"""
        <div class="vf-panel"><h3>Documents processed</h3><p>Files uploaded across all submissions</p>
        <div class="vf-big" style="color:var(--gold)">{docs}</div></div>
        """)
        st.write("")
        avg = (docs / total) if total else 0
        _html(f"""
        <div class="vf-panel"><h3>Documents per vendor</h3><p>Average, based on {total} submission{'s' if total != 1 else ''}</p>
        <div class="vf-big">{avg:.1f}</div></div>
        """)

    # --- optional trend, only if the data has a timestamp ---
    df = pd.DataFrame(runs)
    if total and "created_at" in df.columns:
        try:
            df["day"] = pd.to_datetime(df["created_at"], errors="coerce").dt.date
            daily = df.dropna(subset=["day"]).groupby("day").size().reset_index(name="Submissions")
            if len(daily) > 1:
                st.write("")
                _html('<div class="vf-panel"><h3>Submissions over time</h3><p>New vendors per day</p></div>')
                area = (
                    alt.Chart(daily)
                    .mark_area(line={"color": "#f2b84b"}, color="#f2b84b", opacity=0.18)
                    .encode(x=alt.X("day:T", title=None), y=alt.Y("Submissions:Q", title=None))
                    .properties(height=180)
                    .configure(background="transparent")
                    .configure_view(strokeWidth=0)
                    .configure_axis(labelColor="#8aa0a6", gridColor="#233842", domainColor="#233842")
                )
                st.altair_chart(area, use_container_width=True)
        except Exception:
            pass

    # --- recent activity ---
    st.write("")
    st.subheader("Recent vendor activity")
    if runs:
        _html(_activity_table(df))
        with st.expander("View all submissions"):
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No vendor submissions yet. Choose New Vendor in the sidebar to add one.")