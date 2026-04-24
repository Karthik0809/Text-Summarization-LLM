"""
Advanced Text Summarization — Streamlit UI
HuggingFace Spaces compatible entry point.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from summarizer.core import MODELS, SummarizationEngine
from summarizer.evaluation import evaluate_single
from summarizer.ingestion import clean_text, extract_from_pdf, extract_from_url

logging.basicConfig(level=logging.WARNING)

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Text Summarizer",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS (dark-mode aware) ────────────────────────────────────────────────────
st.markdown(
    """
<style>
  /* ── Header ── */
  .app-title {
    font-size: 2.4rem; font-weight: 800; text-align: center;
    background: linear-gradient(135deg, #667eea, #a78bfa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.15rem;
  }
  .app-sub {
    text-align: center; color: #9ca3af; font-size: 0.92rem;
    margin-bottom: 1.6rem; letter-spacing: 0.03em;
  }

  /* ── Summary box — transparent tinted, works in light & dark ── */
  .summary-box {
    border-left: 4px solid #667eea;
    border-radius: 0 10px 10px 0;
    padding: 1.1rem 1.5rem;
    font-size: 1.05rem;
    line-height: 1.75;
    background: rgba(102, 126, 234, 0.10);
    margin-top: 0.5rem;
  }

  /* ── Model badges ── */
  .badge {
    display: inline-block; padding: 2px 11px; border-radius: 20px;
    font-size: 0.71rem; font-weight: 700; letter-spacing: 0.05em;
    vertical-align: middle;
  }
  .badge-fast  { background: rgba(16,185,129,.18); color: #6ee7b7; }
  .badge-best  { background: rgba(59,130,246,.18);  color: #93c5fd; }
  .badge-bal   { background: rgba(245,158,11,.18);  color: #fcd34d; }
  .badge-lite  { background: rgba(156,163,175,.18); color: #d1d5db; }
  .badge-chat  { background: rgba(239,68,68,.18);   color: #fca5a5; }

  /* ── Metric cards ── */
  div[data-testid="metric-container"] {
    background: rgba(102, 126, 234, 0.07);
    border: 1px solid rgba(102, 126, 234, 0.2);
    border-radius: 10px;
    padding: 0.6rem 1rem;
  }

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0 0; font-weight: 500; font-size: 0.9rem;
  }

  /* ── Error / warning callout ── */
  .url-tip {
    background: rgba(245,158,11,.10);
    border-left: 4px solid #f59e0b;
    border-radius: 0 8px 8px 0;
    padding: 0.9rem 1.2rem;
    font-size: 0.9rem;
    line-height: 1.6;
    margin-top: 0.5rem;
  }
</style>
""",
    unsafe_allow_html=True,
)

# ─── Sample Texts ─────────────────────────────────────────────────────────────
SAMPLES = {
    "🌍 Climate Science": (
        "Scientists have discovered a potentially revolutionary method for carbon capture that could "
        "significantly accelerate efforts to combat climate change. The breakthrough involves engineered "
        "microorganisms that absorb CO2 at rates up to 20 times faster than natural processes. Researchers "
        "at MIT and Stanford collaborated on the project, publishing their findings in the journal Nature "
        "Climate Change. The organisms have been tested in controlled environments and show promise for "
        "deployment in industrial settings. If scaled successfully, the technology could capture billions "
        "of tons of carbon dioxide annually. The team is now working with environmental agencies to conduct "
        "field trials. Experts caution that while promising, the technology is still years away from "
        "widespread deployment and must be carefully evaluated for ecological impacts."
    ),
    "🤖 AI Research": (
        "Large language models have demonstrated remarkable capabilities in natural language understanding "
        "and generation tasks. However, their deployment faces significant challenges including computational "
        "cost, latency, and memory constraints. This paper presents a knowledge distillation framework that "
        "transfers capabilities from large teacher models to compact student models while preserving 95% of "
        "performance. The approach combines layer-wise distillation with task-specific fine-tuning, producing "
        "models that are 4x smaller and 3x faster. Results on GLUE and SuperGLUE benchmarks demonstrate "
        "state-of-the-art efficiency-accuracy tradeoffs. Code and pre-trained models are released publicly "
        "to facilitate further research in efficient natural language processing systems."
    ),
    "☁️ Cloud & DevOps": (
        "Docker containers have revolutionized software deployment, but managing containerized applications "
        "at scale requires robust orchestration. Kubernetes has emerged as the de facto standard, providing "
        "automatic scaling, load balancing, and self-healing capabilities. However, the learning curve is "
        "steep for teams new to cloud-native development. This guide walks through the key concepts: pods, "
        "deployments, services, and ingress controllers with real production examples. We explore best "
        "practices for resource management, security hardening, and monitoring. By the end, readers will "
        "understand how to design reliable, scalable Kubernetes deployments for their own applications, "
        "avoiding the common pitfalls that cause outages in production environments."
    ),
}

BADGE_CSS = {
    "sshleifer/distilbart-cnn-12-6":   "badge-fast",
    "facebook/bart-large-cnn":          "badge-best",
    "google/pegasus-cnn_dailymail":     "badge-bal",
    "t5-base":                          "badge-lite",
    "philschmid/bart-large-cnn-samsum": "badge-chat",
}


def model_badge(model_id: str) -> str:
    css = BADGE_CSS.get(model_id, "badge-lite")
    return f'<span class="badge {css}">{MODELS[model_id]["badge"]}</span>'


# ─── Session State ────────────────────────────────────────────────────────────
for key, default in [
    ("history", []),
    ("last_summary", ""),
    ("fetched_text", ""),
    ("fetched_title", ""),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Model")
    model_id = st.selectbox(
        "Model",
        list(MODELS.keys()),
        format_func=lambda x: MODELS[x]["name"],
        label_visibility="collapsed",
    )
    st.markdown(
        model_badge(model_id) + f"&nbsp; {MODELS[model_id]['desc']}",
        unsafe_allow_html=True,
    )
    st.caption(f"Size: {MODELS[model_id]['size']}")

    st.divider()
    st.markdown("### 🔧 Parameters")
    max_length = st.slider("Max output tokens", 50, 512, 256, 10)
    min_length = st.slider("Min output tokens", 10, 200, 50, 10)
    num_beams  = st.select_slider("Beam width", options=[1, 2, 4, 6, 8], value=4)

    st.divider()
    st.markdown("### 📊 Session")
    n = len(st.session_state.history)
    st.metric("Summaries generated", n)
    if n:
        avg_cr = sum(h["compression_ratio"] for h in st.session_state.history) / n
        st.metric("Avg compression", f"{avg_cr:.1f}×")
    if st.button("🗑️ Clear history", use_container_width=True):
        st.session_state.history.clear()
        st.rerun()

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown('<div class="app-title">🔬 Advanced Text Summarization</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-sub">BART · PEGASUS · T5 &nbsp;|&nbsp; Text · PDF · URL &nbsp;|&nbsp; FastAPI · Docker</div>',
    unsafe_allow_html=True,
)

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab_sum, tab_cmp, tab_bat, tab_eval, tab_api = st.tabs([
    "📝 Summarize",
    "⚖️ Compare Models",
    "📁 Batch",
    "📈 Evaluate",
    "🔌 API Docs",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Summarize
# ══════════════════════════════════════════════════════════════════════════════
with tab_sum:
    mode = st.radio(
        "source",
        ["✍️ Text", "🌐 URL", "📄 PDF"],
        horizontal=True,
        label_visibility="collapsed",
    )

    text_input   = ""
    source_title = "Summary"

    # ── Text ──────────────────────────────────────────────────────────────────
    if mode == "✍️ Text":
        choice = st.selectbox(
            "Sample",
            ["— paste your own —"] + list(SAMPLES.keys()),
            label_visibility="collapsed",
        )
        default = SAMPLES.get(choice, "")
        text_input = st.text_area(
            "text",
            value=default,
            height=230,
            placeholder="Paste any article, paper, or report here…",
            label_visibility="collapsed",
        )
        wc = len(text_input.split())
        st.caption(f"📊 {wc:,} words · ~{max(wc // 250, 1)} min read")
        source_title = choice if choice != "— paste your own —" else "Custom Text"

    # ── URL ───────────────────────────────────────────────────────────────────
    elif mode == "🌐 URL":
        url_val = st.text_input(
            "url",
            placeholder="https://example.com/article",
            label_visibility="collapsed",
        )
        if url_val and st.button("🔍 Fetch Article"):
            with st.spinner("Fetching article…"):
                try:
                    title, body = extract_from_url(url_val)
                    wc = len(body.split())
                    if wc < 30:
                        st.warning(f"Fetched **{title}** but extracted only {wc} words — the site may block scrapers.")
                    else:
                        st.session_state.fetched_text  = body
                        st.session_state.fetched_title = title
                        st.success(f"✅ **{title}** — {wc:,} words extracted")
                except ValueError as exc:
                    # Show the friendly tip message
                    msg = str(exc)
                    # Split on \n\n to separate error from tips
                    parts = msg.split("\n\n", 1)
                    st.error(parts[0])
                    if len(parts) > 1:
                        st.markdown(
                            f'<div class="url-tip">{parts[1].replace(chr(10), "<br>")}</div>',
                            unsafe_allow_html=True,
                        )
                except Exception as exc:
                    st.error(f"Unexpected error: {exc}")

        if st.session_state.fetched_text:
            text_input   = st.session_state.fetched_text
            source_title = st.session_state.fetched_title
            with st.expander(f"Preview — {source_title}"):
                st.write(text_input[:700] + "…")

    # ── PDF ───────────────────────────────────────────────────────────────────
    elif mode == "📄 PDF":
        st.info("Upload a text-based PDF (scanned/image PDFs are not supported).", icon="ℹ️")
        pdf_file = st.file_uploader("PDF", type=["pdf"], label_visibility="collapsed")
        if pdf_file:
            with st.spinner("Extracting text…"):
                try:
                    text_input   = extract_from_pdf(pdf_file.read())
                    source_title = pdf_file.name.replace(".pdf", "")
                    st.success(f"✅ Extracted **{len(text_input.split()):,}** words from **{pdf_file.name}**")
                    with st.expander("Preview"):
                        st.write(text_input[:700] + "…")
                except Exception as exc:
                    st.error(f"PDF extraction failed: {exc}")

    st.divider()

    col_btn, col_stream = st.columns([3, 1])
    with col_btn:
        go_btn = st.button("🚀 Generate Summary", type="primary", use_container_width=True)
    with col_stream:
        streaming = st.checkbox("⚡ Stream tokens", value=False,
                                help="Watch the summary generate token by token (uses greedy decoding)")

    if go_btn:
        words = text_input.split()
        if len(words) < 20:
            st.warning("Please provide at least 20 words of input text.")
        else:
            try:
                engine = SummarizationEngine.get_or_create(model_id)

                if streaming:
                    st.markdown("**Summary**")
                    ph = st.empty()
                    accumulated = ""
                    for tok in engine.stream(text_input, max_length=max_length, min_length=min_length):
                        accumulated += tok
                        ph.markdown(
                            f'<div class="summary-box">{accumulated}▌</div>',
                            unsafe_allow_html=True,
                        )
                    ph.markdown(
                        f'<div class="summary-box">{accumulated}</div>',
                        unsafe_allow_html=True,
                    )
                    summary   = accumulated
                    in_tok    = len(words)
                    out_tok   = len(summary.split())
                    cr        = round(in_tok / max(out_tok, 1), 2)
                    latency   = None
                else:
                    with st.spinner(f"Summarizing with {MODELS[model_id]['name']}…"):
                        result = engine.summarize(
                            text_input,
                            max_length=max_length,
                            min_length=min_length,
                            num_beams=num_beams,
                        )
                    summary = result.summary
                    in_tok  = result.input_tokens
                    out_tok = result.output_tokens
                    cr      = result.compression_ratio
                    latency = result.latency_ms

                    st.markdown("**Summary**")
                    st.markdown(
                        f'<div class="summary-box">{summary}</div>',
                        unsafe_allow_html=True,
                    )

                # Metrics
                st.markdown("")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("📥 Input tokens",  f"{in_tok:,}")
                m2.metric("📤 Output tokens", f"{out_tok:,}")
                m3.metric("🗜️ Compression",   f"{cr:.1f}×")
                if latency:
                    m4.metric("⏱️ Latency", f"{latency:.0f} ms")

                # Save history
                st.session_state.last_summary = summary
                st.session_state.history.append(dict(
                    time=datetime.now().strftime("%H:%M:%S"),
                    title=source_title[:40],
                    model=MODELS[model_id]["name"],
                    input_words=in_tok,
                    output_words=out_tok,
                    compression_ratio=cr,
                    summary=summary,
                ))

                # Export
                d1, d2, d3 = st.columns(3)
                with d1:
                    st.download_button("📄 TXT", summary,
                                       f"{source_title[:25]}.txt", "text/plain")
                with d2:
                    payload = {"source": source_title, "model": model_id, "summary": summary,
                               "metrics": {"input_tokens": in_tok, "output_tokens": out_tok}}
                    st.download_button("🔧 JSON", json.dumps(payload, indent=2),
                                       f"{source_title[:25]}.json", "application/json")
                with d3:
                    md = f"# {source_title}\n\n**Model:** `{model_id}`\n\n## Summary\n\n{summary}\n"
                    st.download_button("📝 Markdown", md,
                                       f"{source_title[:25]}.md", "text/markdown")

            except Exception as exc:
                st.error(f"Summarization error: {exc}")

    # History
    if st.session_state.history:
        st.divider()
        with st.expander(f"📜 History ({len(st.session_state.history)} summaries)"):
            df = pd.DataFrame(st.session_state.history).drop(columns=["summary"], errors="ignore")
            st.dataframe(df, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Compare Models
# ══════════════════════════════════════════════════════════════════════════════
with tab_cmp:
    st.markdown("### Side-by-side model comparison")

    cmp_text = st.text_area(
        "compare text",
        value=SAMPLES["🤖 AI Research"],
        height=170,
        key="cmp_text",
        label_visibility="collapsed",
    )
    selected_models = st.multiselect(
        "Models",
        list(MODELS.keys()),
        default=["sshleifer/distilbart-cnn-12-6", "facebook/bart-large-cnn"],
        format_func=lambda x: MODELS[x]["name"],
        label_visibility="collapsed",
    )

    if st.button("⚖️ Run Comparison", type="primary") and cmp_text and selected_models:
        cmp_results: dict = {}
        prog = st.progress(0)
        for i, mid in enumerate(selected_models):
            prog.progress((i + 1) / len(selected_models),
                          text=f"Running {MODELS[mid]['name']}…")
            try:
                eng = SummarizationEngine.get_or_create(mid)
                cmp_results[mid] = eng.summarize(
                    cmp_text, max_length=max_length, min_length=min_length
                )
            except Exception as exc:
                cmp_results[mid] = exc
        prog.empty()

        cols = st.columns(len(selected_models))
        for col, mid in zip(cols, selected_models):
            with col:
                r = cmp_results[mid]
                st.markdown(f"**{MODELS[mid]['name']}**")
                st.markdown(model_badge(mid), unsafe_allow_html=True)
                if isinstance(r, Exception):
                    st.error(str(r))
                else:
                    st.markdown(
                        f'<div class="summary-box" style="min-height:130px">{r.summary}</div>',
                        unsafe_allow_html=True,
                    )
                    st.metric("Compression", f"{r.compression_ratio:.1f}×")
                    st.metric("Latency",     f"{r.latency_ms:.0f} ms")

        # Comparison chart
        ok = {m: r for m, r in cmp_results.items() if not isinstance(r, Exception)}
        if len(ok) > 1:
            st.divider()
            names = [MODELS[m]["name"] for m in ok]
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Latency (ms)", x=names,
                                 y=[r.latency_ms for r in ok.values()],
                                 marker_color="#667eea"))
            fig.add_trace(go.Bar(name="Output tokens", x=names,
                                 y=[r.output_tokens for r in ok.values()],
                                 marker_color="#a78bfa"))
            fig.update_layout(
                barmode="group", height=320,
                title="Latency & Output Length",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", y=1.08),
                font=dict(color="#e8e8f0"),
            )
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Batch
# ══════════════════════════════════════════════════════════════════════════════
with tab_bat:
    st.markdown("### Batch Summarization")
    st.info("Upload a CSV with a `text` column, or paste multiple texts separated by `---`.")

    batch_mode  = st.radio("input", ["Manual (---)", "CSV Upload"],
                            horizontal=True, label_visibility="collapsed")
    batch_texts: list[str] = []

    if batch_mode == "Manual (---)":
        raw = st.text_area(
            "batch input",
            height=240,
            placeholder="First article…\n---\nSecond article…\n---\nThird article…",
            label_visibility="collapsed",
        )
        if raw:
            batch_texts = [t.strip() for t in raw.split("---") if len(t.split()) >= 20]
            st.caption(f"{len(batch_texts)} valid text(s) (≥ 20 words each)")
    else:
        csv_up = st.file_uploader("CSV", type=["csv"], label_visibility="collapsed")
        if csv_up:
            df_csv = pd.read_csv(csv_up)
            if "text" not in df_csv.columns:
                st.error("CSV must have a `text` column.")
            else:
                batch_texts = df_csv["text"].dropna().tolist()
                st.success(f"✅ {len(batch_texts)} rows loaded.")
                st.dataframe(df_csv.head(3), use_container_width=True)

    if batch_texts and st.button("🚀 Process Batch", type="primary"):
        engine = SummarizationEngine.get_or_create(model_id)
        rows, prog, status = [], st.progress(0), st.empty()
        for i, t in enumerate(batch_texts):
            status.text(f"Processing {i + 1}/{len(batch_texts)}…")
            prog.progress((i + 1) / len(batch_texts))
            try:
                r = engine.summarize(t, max_length=max_length, min_length=min_length)
                rows.append({"preview": t[:80] + "…", "summary": r.summary,
                             "compression": r.compression_ratio,
                             "latency_ms": r.latency_ms, "status": "✅"})
            except Exception as exc:
                rows.append({"preview": t[:80], "summary": str(exc),
                             "compression": 0, "latency_ms": 0, "status": "❌"})
        status.empty(); prog.empty()

        df_out = pd.DataFrame(rows)
        st.success(f"Processed {len(rows)} texts.")
        st.dataframe(df_out, use_container_width=True)
        st.download_button("📥 Download CSV", df_out.to_csv(index=False),
                           "batch_results.csv", "text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Evaluate
# ══════════════════════════════════════════════════════════════════════════════
with tab_eval:
    st.markdown("### ROUGE Evaluation Dashboard")
    st.info("Paste a reference summary and a generated summary to compute ROUGE scores.")

    ec1, ec2 = st.columns(2)
    with ec1:
        ref_text = st.text_area("📋 Reference (ground truth)", height=190, key="ref")
    with ec2:
        gen_text = st.text_area("🤖 Generated summary", height=190,
                                value=st.session_state.last_summary, key="gen")

    if st.button("📊 Compute ROUGE + Metrics") and ref_text and gen_text:
        ev = evaluate_single(gen_text, ref_text)

        gauges = {"ROUGE-1": ev.rouge1, "ROUGE-2": ev.rouge2, "ROUGE-L": ev.rougeL}
        g_cols = st.columns(3)
        for col, (name, val) in zip(g_cols, gauges.items()):
            with col:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=val * 100,
                    title={"text": name, "font": {"size": 15, "color": "#e8e8f0"}},
                    number={"suffix": "%", "font": {"size": 22, "color": "#e8e8f0"}},
                    gauge={
                        "axis": {"range": [0, 100],
                                 "tickcolor": "#6b7280", "tickfont": {"color": "#9ca3af"}},
                        "bar": {"color": "#667eea"},
                        "bgcolor": "rgba(0,0,0,0)",
                        "bordercolor": "rgba(0,0,0,0)",
                        "steps": [
                            {"range": [0, 30],  "color": "rgba(239,68,68,.15)"},
                            {"range": [30, 60], "color": "rgba(245,158,11,.15)"},
                            {"range": [60, 100],"color": "rgba(16,185,129,.15)"},
                        ],
                        "threshold": {
                            "line": {"color": "#a78bfa", "width": 2},
                            "value": val * 100,
                        },
                    },
                ))
                fig.update_layout(
                    height=220,
                    margin=dict(t=40, b=0, l=20, r=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True)

        m1, m2, m3 = st.columns(3)
        m1.metric("🗜️ Compression", f"{ev.compression_ratio:.2f}×")
        m2.metric("📏 Avg sentence", f"{ev.avg_sentence_length:.1f} words")
        m3.metric("📊 ROUGE-Lsum",   f"{ev.rougeLsum:.3f}")

        # Radar
        cats = ["ROUGE-1", "ROUGE-2", "ROUGE-L", "ROUGE-Lsum"]
        vals = [ev.rouge1, ev.rouge2, ev.rougeL, ev.rougeLsum]
        fig_r = go.Figure(go.Scatterpolar(
            r=vals + [vals[0]], theta=cats + [cats[0]],
            fill="toself",
            fillcolor="rgba(102,126,234,0.15)",
            line=dict(color="#667eea", width=2),
        ))
        fig_r.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0, 1],
                                tickfont={"color": "#9ca3af"},
                                gridcolor="rgba(156,163,175,.2)"),
                angularaxis=dict(tickfont={"color": "#d1d5db"},
                                 gridcolor="rgba(156,163,175,.2)"),
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            height=340,
            title=dict(text="ROUGE Radar", font=dict(color="#e8e8f0")),
        )
        st.plotly_chart(fig_r, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — API Docs
# ══════════════════════════════════════════════════════════════════════════════
with tab_api:
    st.markdown("### REST API Reference")
    st.info("Run `uvicorn api.main:app --reload` locally. Interactive Swagger UI at `/docs`.")

    endpoints = [
        ("GET",  "/api/v1/health",           "Health check — CUDA status + loaded models"),
        ("GET",  "/api/v1/models",           "List all available models with metadata"),
        ("POST", "/api/v1/summarize",        "Summarize plain text"),
        ("POST", "/api/v1/summarize/url",    "Fetch a URL and summarize it"),
        ("POST", "/api/v1/summarize/pdf",    "Upload a PDF and summarize it"),
        ("POST", "/api/v1/summarize/batch",  "Batch-summarize up to 20 texts"),
        ("POST", "/api/v1/compare",          "Compare multiple models on the same input"),
    ]
    MC = {"GET": "#10b981", "POST": "#667eea"}
    for method, path, desc in endpoints:
        c = MC[method]
        st.markdown(
            f'<span class="badge" style="background:{c}22;color:{c};border-radius:5px;'
            f'padding:2px 10px">{method}</span>&nbsp; `{path}` — {desc}',
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("**cURL**")
    st.code(
        'curl -X POST http://localhost:8000/api/v1/summarize \\\n'
        '  -H "Content-Type: application/json" \\\n'
        "  -d '{\"text\": \"Your article text...\", \"model_id\": \"sshleifer/distilbart-cnn-12-6\"}'",
        language="bash",
    )
    st.markdown("**Python**")
    st.code(
        "import requests\n\n"
        "resp = requests.post(\n"
        '    "http://localhost:8000/api/v1/summarize",\n'
        '    json={"text": "...", "model_id": "sshleifer/distilbart-cnn-12-6", "num_beams": 4},\n'
        ")\n"
        'print(resp.json()["summary"])',
        language="python",
    )
    st.markdown("**Model comparison**")
    st.code(
        "resp = requests.post(\n"
        '    "http://localhost:8000/api/v1/compare",\n'
        "    json={\n"
        '        "text": "Long article...",\n'
        '        "model_ids": ["sshleifer/distilbart-cnn-12-6", "facebook/bart-large-cnn"],\n'
        "    },\n"
        ")\n"
        "for model_id, result in resp.json()['results'].items():\n"
        "    print(model_id, '->', result['summary'][:80])",
        language="python",
    )
