"""Streamlit app — Wingman-branded drag-drop validation UI.

Brand:
  - Background: Core Black (#000000)
  - Surface: Deep Green (#1E2B2E), Slate Green (#081A1E)
  - Accents: Wingman gradient (Boost Green -> Clarity Blue)
  - Fonts: Roboto Mono (headers, all caps); Outfit (body)
  - No emoji; status communicated via type and color
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import streamlit as st

from race_validator import (
    CONTRACT_VERSION,
    LIBRARY_VERSION,
    validate_file,
)
from race_validator.report import Severity, ValidationReport


# ---------- assets ----------

ASSETS_DIR = Path(__file__).parent / "assets"
LOGO_PATH = ASSETS_DIR / "wingman_logo.png"


# ---------- page setup ----------

st.set_page_config(
    page_title="Wingman • Race Data Validator",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None,
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ---------- styles ----------

st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500;700&family=Outfit:wght@300;400;500;600&display=swap" rel="stylesheet">

    <style>
    :root {
        --core-black: #000000;
        --deep-green: #1E2B2E;
        --slate-green: #081A1E;
        --clear-white: #FFFFFF;
        --cool-grey: #9EA2A2;
        --boost-green: #5FFF67;
        --clarity-blue: #46FFFF;
        --wingman-gradient: linear-gradient(90deg, #5FFF67 0%, #46FFFF 100%);
        --error-red: #FF6B6B;
        --warning-amber: #FFB347;

        --font-mono: 'Roboto Mono', ui-monospace, monospace;
        --font-body: 'Outfit', system-ui, sans-serif;
    }

    /* ---- global ---- */
    html, body, [class*="css"], .stApp {
        background-color: var(--core-black) !important;
        color: var(--clear-white) !important;
        font-family: var(--font-body) !important;
    }
    .stApp { background: var(--core-black) !important; }
    [data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stToolbar"] { display: none; }
    section.main > div { padding-top: 1rem; }
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }

    /* ---- typography ---- */
    h1, h2, h3, h4, h5, h6 {
        font-family: var(--font-mono) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
        color: var(--clear-white) !important;
        font-weight: 700 !important;
    }
    p, div, span, label, li, td, th {
        font-family: var(--font-body) !important;
    }
    code, pre, .code-text {
        font-family: var(--font-mono) !important;
    }

    /* ---- header band ---- */
    .wm-header {
        padding: 24px 8px 8px 8px;
        border-bottom: 1px solid var(--deep-green);
        margin-bottom: 32px;
    }
    .wm-header-meta,
    .wm-header-meta span,
    .wm-header-meta .accent {
        font-family: var(--font-mono) !important;
        font-size: 11px;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--cool-grey);
    }
    .wm-header-meta { margin-top: 12px; }
    .wm-header-meta .accent {
        background: var(--wingman-gradient);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        font-weight: 700;
    }
    .wm-page-title {
        font-family: var(--font-mono) !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-size: 13px;
        color: var(--cool-grey);
        margin-top: 16px;
    }

    /* ---- file uploader ---- */
    [data-testid="stFileUploader"] {
        background: var(--deep-green) !important;
        border: 1px dashed #2A3B3F !important;
        border-radius: 4px !important;
        padding: 16px !important;
    }
    [data-testid="stFileUploader"] label,
    [data-testid="stFileUploader"] section {
        background: transparent !important;
        color: var(--clear-white) !important;
    }
    [data-testid="stFileUploader"] section small {
        color: var(--cool-grey) !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        background: var(--slate-green) !important;
        border: 1px dashed #2A3B3F !important;
    }

    /* Upload-button label override.
       Streamlit ships its own button label ("Browse files" / "Upload" /
       localized variants). To avoid double-rendering and to brand the CTA,
       we hide all native children and inject our own text via ::before. */
    [data-testid="stFileUploaderDropzone"] button {
        background: var(--core-black) !important;
        border: 1px solid var(--clear-white) !important;
        border-radius: 2px !important;
        padding: 8px 22px !important;
        position: relative !important;
        min-width: 140px !important;
        height: 36px !important;
        color: transparent !important;
        overflow: hidden !important;
    }
    [data-testid="stFileUploaderDropzone"] button > * {
        visibility: hidden !important;
    }
    [data-testid="stFileUploaderDropzone"] button::before {
        content: "SELECT FILE";
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono) !important;
        font-size: 11px;
        letter-spacing: 0.14em;
        color: var(--clear-white);
        text-transform: uppercase;
        font-weight: 500;
    }
    [data-testid="stFileUploaderDropzone"] button:hover {
        background: var(--clear-white) !important;
    }
    [data-testid="stFileUploaderDropzone"] button:hover::before {
        color: var(--core-black);
    }

    /* ---- result cards ---- */
    .wm-result-card {
        background: var(--deep-green);
        border-left: 3px solid var(--cool-grey);
        padding: 14px 18px;
        margin-bottom: 12px;
        border-radius: 2px;
    }
    .wm-result-card.error   { border-left-color: var(--error-red); }
    .wm-result-card.warning { border-left-color: var(--warning-amber); }
    .wm-result-card.info    { border-left-color: var(--clarity-blue); }

    .wm-result-header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        font-family: var(--font-mono) !important;
        font-size: 11px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .wm-severity-error   { color: var(--error-red); font-weight: 700; }
    .wm-severity-warning { color: var(--warning-amber); font-weight: 700; }
    .wm-severity-info    { color: var(--clarity-blue); font-weight: 700; }

    .wm-rule-id {
        font-family: var(--font-mono) !important;
        font-size: 11px;
        letter-spacing: 0.06em;
        color: var(--cool-grey);
    }
    .wm-result-message {
        font-family: var(--font-body);
        font-size: 15px;
        font-weight: 500;
        color: var(--clear-white);
        line-height: 1.5;
        margin: 4px 0 8px 0;
    }
    .wm-result-location {
        font-family: var(--font-mono) !important;
        font-size: 12px;
        color: var(--cool-grey);
        margin: 4px 0;
    }
    .wm-result-hint {
        font-family: var(--font-body);
        font-size: 13px;
        color: var(--cool-grey);
        line-height: 1.5;
        margin-top: 6px;
        padding-top: 6px;
        border-top: 1px solid var(--slate-green);
    }
    .wm-result-hint strong {
        color: var(--clear-white);
        font-family: var(--font-mono) !important;
        text-transform: uppercase;
        font-size: 10px;
        letter-spacing: 0.1em;
        display: block;
        margin-bottom: 4px;
    }

    /* ---- summary banner ---- */
    .wm-summary {
        padding: 20px 24px;
        border-radius: 4px;
        margin: 24px 0;
        font-family: var(--font-mono) !important;
    }
    .wm-summary-pass {
        background: var(--slate-green);
        border-left: 4px solid var(--boost-green);
    }
    .wm-summary-fail {
        background: var(--slate-green);
        border-left: 4px solid var(--error-red);
    }
    .wm-summary-status {
        font-size: 20px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        margin-bottom: 8px;
    }
    .wm-summary-pass .wm-summary-status {
        background: var(--wingman-gradient);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
    }
    .wm-summary-fail .wm-summary-status { color: var(--error-red); }
    .wm-summary-counts {
        font-size: 11px;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--cool-grey);
    }
    .wm-summary-counts strong {
        color: var(--clear-white);
        font-weight: 700;
    }

    /* ---- section headers in results ---- */
    .wm-section-label {
        font-family: var(--font-mono) !important;
        font-size: 11px;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--cool-grey);
        margin: 28px 0 12px 0;
        padding-bottom: 6px;
        border-bottom: 1px solid var(--deep-green);
    }
    .wm-filename {
        font-family: var(--font-mono) !important;
        color: var(--clear-white);
        font-size: 13px;
        word-break: break-all;
    }

    /* ---- buttons ---- */
    .stDownloadButton button, .stButton button {
        background: var(--core-black) !important;
        border: 1px solid var(--clear-white) !important;
        color: var(--clear-white) !important;
        font-family: var(--font-mono) !important;
        text-transform: uppercase !important;
        font-size: 11px !important;
        letter-spacing: 0.14em !important;
        border-radius: 2px !important;
        padding: 10px 20px !important;
    }
    .stDownloadButton button:hover, .stButton button:hover {
        background: var(--clear-white) !important;
        color: var(--core-black) !important;
    }

    /* ---- spinner ---- */
    .stSpinner > div { color: var(--boost-green) !important; }

    /* ---- placeholder when no file uploaded ---- */
    .wm-empty-state {
        text-align: center;
        padding: 48px 24px;
        color: var(--cool-grey);
        font-family: var(--font-mono) !important;
        font-size: 11px;
        letter-spacing: 0.18em;
        text-transform: uppercase;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- header band ----------

if LOGO_PATH.exists():
    st.markdown('<div class="wm-header">', unsafe_allow_html=True)
    st.image(str(LOGO_PATH), width=240)
    st.markdown(
        f"""
        <div class="wm-header-meta">
            <span class="accent">Race Data Validator</span>
            &nbsp;·&nbsp; Library v{LIBRARY_VERSION}
            &nbsp;·&nbsp; Contract v{CONTRACT_VERSION}
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f"""
        <div class="wm-header">
            <h1>WINGMAN</h1>
            <div class="wm-header-meta">
                Race Data Validator
                &nbsp;·&nbsp; Library v{LIBRARY_VERSION}
                &nbsp;·&nbsp; Contract v{CONTRACT_VERSION}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    '<div class="wm-page-title">Drop a CSV to validate against the data contract</div>',
    unsafe_allow_html=True,
)


# ---------- upload ----------

uploaded = st.file_uploader(
    "",
    type=["csv"],
    accept_multiple_files=False,
    label_visibility="collapsed",
)


# ---------- render helpers ----------

SEVERITY_LABEL = {
    Severity.ERROR: "ERROR",
    Severity.WARNING: "WARNING",
    Severity.INFO: "INFO",
}


def _render_result(result) -> None:
    css_class = result.severity.value
    sev_label = SEVERITY_LABEL[result.severity]
    sev_class = f"wm-severity-{css_class}"

    location_html = (
        f'<div class="wm-result-location">{result.location}</div>'
        if result.location else ""
    )
    hint_html = (
        f'<div class="wm-result-hint"><strong>Fix</strong>{result.fix_hint}</div>'
        if result.fix_hint else ""
    )

    st.markdown(
        f"""
        <div class="wm-result-card {css_class}">
            <div class="wm-result-header">
                <span class="{sev_class}">{sev_label}</span>
                <span class="wm-rule-id">{result.rule_id} &nbsp;·&nbsp; {result.contract_section}</span>
            </div>
            <div class="wm-result-message">{result.message}</div>
            {location_html}
            {hint_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_summary(report: ValidationReport) -> None:
    if report.passed:
        status = "PASS"
        counts = (
            f"<strong>{report.checks_run}</strong> checks &nbsp;·&nbsp; "
            f"<strong>{report.checks_passed}</strong> passed &nbsp;·&nbsp; "
            f"<strong>{report.warning_count}</strong> warnings"
        )
        css = "wm-summary-pass"
    else:
        status = "FILE REJECTED"
        counts = (
            f"<strong>{report.checks_run}</strong> checks &nbsp;·&nbsp; "
            f"<strong>{report.error_count}</strong> errors &nbsp;·&nbsp; "
            f"<strong>{report.warning_count}</strong> warnings"
        )
        css = "wm-summary-fail"

    st.markdown(
        f"""
        <div class="wm-summary {css}">
            <div class="wm-summary-status">{status}</div>
            <div class="wm-summary-counts">{counts}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_report(report: ValidationReport) -> None:
    st.markdown(
        f'<div class="wm-section-label">Results for &nbsp;<span class="wm-filename">{report.filename}</span></div>',
        unsafe_allow_html=True,
    )
    _render_summary(report)

    if not report.results:
        st.markdown(
            '<div class="wm-empty-state">All checks passed cleanly</div>',
            unsafe_allow_html=True,
        )
        return

    for sev, label in [
        (Severity.ERROR, "Errors"),
        (Severity.WARNING, "Warnings"),
        (Severity.INFO, "Information"),
    ]:
        bucket = [r for r in report.results if r.severity == sev]
        if not bucket:
            continue
        st.markdown(
            f'<div class="wm-section-label">{label} &nbsp;·&nbsp; {len(bucket)}</div>',
            unsafe_allow_html=True,
        )
        for r in bucket:
            _render_result(r)


# ---------- main flow ----------

if uploaded is not None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / uploaded.name
        tmp_path.write_bytes(uploaded.getbuffer())

        with st.spinner("Validating…"):
            report = validate_file(tmp_path)

    _render_report(report)

    st.markdown(
        '<div class="wm-section-label">Export</div>',
        unsafe_allow_html=True,
    )
    st.download_button(
        label="Download Report (JSON)",
        data=json.dumps(report.to_dict(), indent=2),
        file_name=f"{uploaded.name}.report.json",
        mime="application/json",
    )

else:
    st.markdown(
        '<div class="wm-empty-state">Waiting for file</div>',
        unsafe_allow_html=True,
    )
