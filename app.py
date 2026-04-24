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

# Ensure local packages are importable when running from repo root
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

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
  .app-title {
    font-size: 2.6rem; font-weight: 800;
    background: linear-gradient(135deg, #667eea, #764ba2);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-align: center; margin-bottom: 0.2rem;
  }
  .app-sub {
    text-align: center; color: #6c757d; font-size: 1rem; margin-bottom: 1.5rem;
  }
  .summary-box {
    background: #f8f9fe; border-left: 4px solid #667eea;
    border-radius: 0 8px 8px 0; padding: 1rem 1.5rem;
    font-size: 1.05rem; line-height: 1.7;
  }
  .badge {
    display: inline-block; padding: 2px 10px; border-radius: 20px;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em;
  }
  .badge-fast  { background:#d4edda; color:#155724; }
  .badge-best  { background:#cce5ff; color:#004085; }
  .badge-bal   { background:#fff3cd; color:#856404; }
  .badge-lite  { background:#e2e3e5; color:#383d41; }
  .badge-chat  { background:#f8d7da; color:#721c24; }
  .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; font-weight: 500; }
  .endpoint-row { font-family: monospace; margin: 4px 0; }
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
        "Large language models (LLMs) have demonstrated remarkable capabilities in natural language "
        "understanding and generation tasks. However, their deployment faces significant challenges including "
        "computational cost, latency, and memory constraints. This paper presents a knowledge distillation "
        "framework that transfers capabilities from large teacher models to compact student models while "
        "preserving 95% of performance. The approach combines layer-wise distillation with task-specific "
        "fine-tuning, producing models that are 4× smaller and 3× faster. Results on GLUE and SuperGLUE "
        "demonstrate state-of-the-art efficiency-accuracy tradeoffs. Code and models are released publicly."
    ),
    "☁️ Cloud Tech": (
        "Docker containers have revolutionized software deployment, but managing containerized applications "
        "at scale requires robust orchestration. Kubernetes has emerged as the de facto standard, providing "
        "automatic scaling, load balancing, and self-healing. However, the learning curve is steep for teams "
        "new to cloud-native development. This guide walks through pods, deployments, services, and ingress "
        "controllers with real production examples. We explore best practices for resource management, "
        "security hardening, and observability. By the end readers will design reliable, scalable Kubernetes "
        "deployments for their own applications."
    ),
}

BADGE_CSS = {
    "sshleifer/distilbart-cnn-12-6": "badge-fast",
    "facebook/bart-large-cnn": "badge-best",
    "google/pegasus-cnn_dailymail": "badge-bal",
    "t5-base": "badge-lite",
    "philschmid/bart-large-cnn-samsum": "badge-chat",
}


def model_badge(model_id: str) -> str:
    css = BADGE_CSS.get(model_id, "badge-lite")
    badge_text = MODELS[model_id]["badge"]
    return f'<span class="badge {css}">{badge_text}</span>'


# ─── Session State ────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history: list[dict] = []
if "last_summary" not in st.session_state:
    st.session_state.last_summary = ""
if "fetched_text" not in st.session_state:
    st.session_state.fetched_text = ""
if "fetched_title" not in st.session_state:
    st.session_state.fetched_title = ""

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Model & Parameters")

    model_id = st.selectbox(
        "Model",
        options=list(MODELS.keys()),
        format_func=lambda x: MODELS[x]["name"],
        index=0,
    )
    st.markdown(
        model_badge(model_id) + f" &nbsp; {MODELS[model_id]['desc']}",
        unsafe_allow_html=True,
    )
    st.caption(f"Size: {MODELS[model_id]['size']}")

    st.divider()
    max_length = st.slider("Max output tokens", 50, 512, 256, 10)
    min_length = st.slider("Min output tokens", 10, 200, 50, 10)
    num_beams = st.select_slider("Beam width", options=[1, 2, 4, 6, 8], value=4)

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
    '<div class="app-sub">Multi-model abstractive summarization · BART · PEGASUS · T5 · FastAPI · Docker</div>',
    unsafe_allow_html=True,
)

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab_summarize, tab_compare, tab_batch, tab_evaluate, tab_api = st.tabs([
    "📝 Summarize",
    "⚖️ Compare Models",
    "📁 Batch",
    "📈 Evaluate",
    "🔌 API Docs",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Summarize
# ══════════════════════════════════════════════════════════════════════════════
with tab_summarize:
    mode = st.radio("Input source", ["✍️ Text", "🌐 URL", "📄 PDF"], horizontal=True, label_visibility="collapsed")

    text_input = ""
    source_title = "Summary"

    # — Text mode —
    if mode == "✍️ Text":
        sample_key = st.selectbox("Try a sample", ["— paste your own —"] + list(SAMPLES.keys()))
        default = SAMPLES.get(sample_key, "")
        text_input = st.text_area(
            "Input text",
            value=default,
            height=240,
            placeholder="Paste any article, paper, or report here…",
            label_visibility="collapsed",
        )
        wc = len(text_input.split())
        st.caption(f"📊 {wc:,} words · ~{max(wc // 250, 1)} min read")
        source_title = sample_key if sample_key != "— paste your own —" else "Custom Text"

    # — URL mode —
    elif mode == "🌐 URL":
        url_val = st.text_input("Article URL", placeholder="https://example.com/article", label_visibility="collapsed")
        if url_val and st.button("🔍 Fetch Article"):
            with st.spinner("Fetching…"):
                try:
                    title, body = extract_from_url(url_val)
                    st.session_state.fetched_text = body
                    st.session_state.fetched_title = title
                    st.success(f"✅ **{title}** — {len(body.split())} words")
                except Exception as exc:
                    st.error(f"Fetch failed: {exc}")
        if st.session_state.fetched_text:
            text_input = st.session_state.fetched_text
            source_title = st.session_state.fetched_title
            with st.expander("Preview"):
                st.write(text_input[:600] + "…")

    # — PDF mode —
    elif mode == "📄 PDF":
        pdf_file = st.file_uploader("Upload PDF", type=["pdf"])
        if pdf_file:
            with st.spinner("Extracting text…"):
                try:
                    text_input = extract_from_pdf(pdf_file.read())
                    source_title = pdf_file.name.replace(".pdf", "")
                    st.success(f"✅ Extracted {len(text_input.split())} words from **{pdf_file.name}**")
                    with st.expander("Preview"):
                        st.write(text_input[:600] + "…")
                except Exception as exc:
                    st.error(f"PDF extraction failed: {exc}")

    st.divider()

    col_btn, col_stream = st.columns([3, 1])
    with col_btn:
        go_btn = st.button("🚀 Generate Summary", type="primary", use_container_width=True)
    with col_stream:
        streaming = st.checkbox("⚡ Stream tokens", value=False, help="Watch the summary build token by token")

    if go_btn:
        if len(text_input.split()) < 20:
            st.warning("Please provide at least 20 words.")
        else:
            try:
                engine = SummarizationEngine.get_or_create(model_id)

                if streaming:
                    st.markdown("**Summary:**")
                    placeholder = st.empty()
                    accumulated = ""
                    for tok in engine.stream(text_input, max_length=max_length, min_length=min_length):
                        accumulated += tok
                        placeholder.markdown(
                            f'<div class="summary-box">{accumulated}▌</div>',
                            unsafe_allow_html=True,
                        )
                    placeholder.markdown(
                        f'<div class="summary-box">{accumulated}</div>',
                        unsafe_allow_html=True,
                    )
                    summary = accumulated
                    in_tok = len(text_input.split())
                    out_tok = len(summary.split())
                    cr = round(in_tok / max(out_tok, 1), 2)
                    latency = 0.0
                else:
                    with st.spinner(f"Summarizing with {MODELS[model_id]['name']}…"):
                        result = engine.summarize(
                            text_input,
                            max_length=max_length,
                            min_length=min_length,
                            num_beams=num_beams,
                        )
                    summary = result.summary
                    in_tok = result.input_tokens
                    out_tok = result.output_tokens
                    cr = result.compression_ratio
                    latency = result.latency_ms
                    st.markdown("**Summary:**")
                    st.markdown(f'<div class="summary-box">{summary}</div>', unsafe_allow_html=True)

                # Metrics
                st.markdown("---")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("📥 Input tokens", f"{in_tok:,}")
                m2.metric("📤 Output tokens", f"{out_tok:,}")
                m3.metric("🗜️ Compression", f"{cr:.1f}×")
                if latency:
                    m4.metric("⏱️ Latency", f"{latency:.0f} ms")

                st.session_state.last_summary = summary
                st.session_state.history.append(
                    dict(
                        time=datetime.now().strftime("%H:%M:%S"),
                        title=source_title[:40],
                        model=MODELS[model_id]["name"],
                        input_words=in_tok,
                        output_words=out_tok,
                        compression_ratio=cr,
                        summary=summary,
                    )
                )

                # Export
                d1, d2, d3 = st.columns(3)
                with d1:
                    st.download_button("📄 TXT", summary, f"{source_title[:25]}.txt", "text/plain")
                with d2:
                    payload = {"source": source_title, "model": model_id, "summary": summary,
                               "metrics": {"input_tokens": in_tok, "output_tokens": out_tok}}
                    st.download_button("🔧 JSON", json.dumps(payload, indent=2),
                                       f"{source_title[:25]}.json", "application/json")
                with d3:
                    md = f"# {source_title}\n\n**Model:** `{model_id}`\n\n## Summary\n\n{summary}\n"
                    st.download_button("📝 Markdown", md, f"{source_title[:25]}.md", "text/markdown")

            except Exception as exc:
                st.error(f"Error: {exc}")

    # History
    if st.session_state.history:
        st.divider()
        with st.expander(f"📜 History ({len(st.session_state.history)} summaries)"):
            df = pd.DataFrame(st.session_state.history).drop(columns=["summary"], errors="ignore")
            st.dataframe(df, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Compare Models
# ══════════════════════════════════════════════════════════════════════════════
with tab_compare:
    st.markdown("### Side-by-side model comparison")

    cmp_text = st.text_area(
        "Text",
        value=SAMPLES["🤖 AI Research"],
        height=180,
        key="cmp_text",
        label_visibility="collapsed",
    )
    selected_models = st.multiselect(
        "Models to compare",
        list(MODELS.keys()),
        default=["sshleifer/distilbart-cnn-12-6", "facebook/bart-large-cnn"],
        format_func=lambda x: MODELS[x]["name"],
    )

    if st.button("⚖️ Run Comparison", type="primary") and cmp_text and selected_models:
        cmp_results: dict = {}
        prog = st.progress(0)
        for i, mid in enumerate(selected_models):
            prog.progress((i + 1) / len(selected_models), text=f"Running {MODELS[mid]['name']}…")
            try:
                eng = SummarizationEngine.get_or_create(mid)
                cmp_results[mid] = eng.summarize(cmp_text, max_length=max_length, min_length=min_length)
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
                        f'<div class="summary-box" style="min-height:140px">{r.summary}</div>',
                        unsafe_allow_html=True,
                    )
                    st.metric("Compression", f"{r.compression_ratio:.1f}×")
                    st.metric("Latency", f"{r.latency_ms:.0f} ms")

        # Chart
        ok = {mid: r for mid, r in cmp_results.items() if not isinstance(r, Exception)}
        if len(ok) > 1:
            st.divider()
            names = [MODELS[m]["name"] for m in ok]
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Latency (ms)", x=names, y=[r.latency_ms for r in ok.values()],
                                 marker_color="#667eea"))
            fig.add_trace(go.Bar(name="Output tokens", x=names, y=[r.output_tokens for r in ok.values()],
                                 marker_color="#764ba2"))
            fig.update_layout(barmode="group", height=340, title="Model Metrics Comparison",
                              legend=dict(orientation="h", y=1.02))
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Batch
# ══════════════════════════════════════════════════════════════════════════════
with tab_batch:
    st.markdown("### Batch Summarization")
    st.info("Upload a CSV with a `text` column, or paste texts separated by `---`.")

    batch_mode = st.radio("Input", ["Manual (---)", "CSV Upload"], horizontal=True, label_visibility="collapsed")
    batch_texts: list[str] = []

    if batch_mode == "Manual (---)":
        raw_batch = st.text_area(
            "Texts",
            height=260,
            placeholder="First article…\n---\nSecond article…\n---\nThird article…",
            label_visibility="collapsed",
        )
        if raw_batch:
            batch_texts = [t.strip() for t in raw_batch.split("---") if len(t.split()) >= 20]
            st.caption(f"{len(batch_texts)} valid text(s) detected (≥20 words each).")
    else:
        csv_up = st.file_uploader("CSV file", type=["csv"])
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
        rows = []
        prog = st.progress(0)
        status = st.empty()
        for i, t in enumerate(batch_texts):
            status.text(f"Processing {i + 1}/{len(batch_texts)}…")
            prog.progress((i + 1) / len(batch_texts))
            try:
                r = engine.summarize(t, max_length=max_length, min_length=min_length)
                rows.append({"preview": t[:80] + "…", "summary": r.summary,
                             "compression": r.compression_ratio, "latency_ms": r.latency_ms, "status": "✅"})
            except Exception as exc:
                rows.append({"preview": t[:80], "summary": str(exc),
                             "compression": 0, "latency_ms": 0, "status": "❌"})
        status.empty(); prog.empty()

        result_df = pd.DataFrame(rows)
        st.success(f"Processed {len(rows)} texts.")
        st.dataframe(result_df, use_container_width=True)
        st.download_button("📥 Download CSV", result_df.to_csv(index=False),
                           "batch_results.csv", "text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Evaluate
# ══════════════════════════════════════════════════════════════════════════════
with tab_evaluate:
    st.markdown("### ROUGE Evaluation Dashboard")
    st.info("Paste a reference summary and a generated summary to compute ROUGE scores and quality metrics.")

    ec1, ec2 = st.columns(2)
    with ec1:
        ref_text = st.text_area("📋 Reference (ground truth)", height=200, key="ref")
    with ec2:
        gen_text = st.text_area(
            "🤖 Generated summary",
            height=200,
            value=st.session_state.last_summary,
            key="gen",
        )

    if st.button("📊 Compute ROUGE + Metrics") and ref_text and gen_text:
        ev = evaluate_single(gen_text, ref_text)

        gauges = {"ROUGE-1": ev.rouge1, "ROUGE-2": ev.rouge2, "ROUGE-L": ev.rougeL}
        g_cols = st.columns(3)
        for col, (name, val) in zip(g_cols, gauges.items()):
            with col:
                fig = go.Figure(
                    go.Indicator(
                        mode="gauge+number",
                        value=val * 100,
                        title={"text": name, "font": {"size": 16}},
                        number={"suffix": "%", "font": {"size": 24}},
                        gauge={
                            "axis": {"range": [0, 100]},
                            "bar": {"color": "#667eea"},
                            "steps": [
                                {"range": [0, 30], "color": "#ffe0e0"},
                                {"range": [30, 60], "color": "#fff3cd"},
                                {"range": [60, 100], "color": "#d4edda"},
                            ],
                            "threshold": {"line": {"color": "#764ba2", "width": 3}, "value": val * 100},
                        },
                    )
                )
                fig.update_layout(height=230, margin=dict(t=40, b=0, l=20, r=20))
                st.plotly_chart(fig, use_container_width=True)

        m1, m2, m3 = st.columns(3)
        m1.metric("🗜️ Compression ratio", f"{ev.compression_ratio:.2f}×")
        m2.metric("📏 Avg sentence length", f"{ev.avg_sentence_length:.1f} words")
        m3.metric("📊 ROUGE-Lsum", f"{ev.rougeLsum:.3f}")

        # Radar chart
        categories = ["ROUGE-1", "ROUGE-2", "ROUGE-L", "ROUGE-Lsum"]
        vals = [ev.rouge1, ev.rouge2, ev.rougeL, ev.rougeLsum]
        fig_radar = go.Figure(
            go.Scatterpolar(r=vals + [vals[0]], theta=categories + [categories[0]],
                            fill="toself", fillcolor="rgba(102,126,234,0.2)",
                            line=dict(color="#667eea", width=2), name="Scores")
        )
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            height=350, title="ROUGE Radar",
        )
        st.plotly_chart(fig_radar, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — API Docs
# ══════════════════════════════════════════════════════════════════════════════
with tab_api:
    st.markdown("### REST API Reference")
    st.info("Start the backend with `uvicorn api.main:app --reload`. Interactive docs at `/docs`.")

    endpoints = [
        ("GET",  "/health",                 "Health check — CUDA status, loaded models"),
        ("GET",  "/api/v1/models",           "List all available models with metadata"),
        ("POST", "/api/v1/summarize",        "Summarize plain text"),
        ("POST", "/api/v1/summarize/url",    "Fetch a URL and summarize it"),
        ("POST", "/api/v1/summarize/pdf",    "Upload a PDF and summarize it"),
        ("POST", "/api/v1/summarize/batch",  "Batch-summarize up to 20 texts"),
        ("POST", "/api/v1/compare",          "Compare multiple models on the same input"),
    ]
    METHOD_COLOR = {"GET": "#28a745", "POST": "#007bff"}
    for method, path, desc in endpoints:
        color = METHOD_COLOR[method]
        st.markdown(
            f'<span class="badge" style="background:{color};color:white;border-radius:4px;padding:2px 8px">'
            f"{method}</span> &nbsp; `{path}` &mdash; {desc}",
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("**cURL example:**")
    st.code(
        'curl -X POST http://localhost:8000/api/v1/summarize \\\n'
        '  -H "Content-Type: application/json" \\\n'
        "  -d '{\"text\": \"Your article text...\", \"model_id\": \"sshleifer/distilbart-cnn-12-6\"}'",
        language="bash",
    )
    st.markdown("**Python:**")
    st.code(
        "import requests\n\n"
        "resp = requests.post(\n"
        '    "http://localhost:8000/api/v1/summarize",\n'
        '    json={"text": "...", "model_id": "sshleifer/distilbart-cnn-12-6", "num_beams": 4},\n'
        ")\n"
        'print(resp.json()["summary"])',
        language="python",
    )
    st.markdown("**Compare two models:**")
    st.code(
        "resp = requests.post(\n"
        '    "http://localhost:8000/api/v1/compare",\n'
        "    json={\n"
        '        "text": "...",\n'
        '        "model_ids": ["sshleifer/distilbart-cnn-12-6", "facebook/bart-large-cnn"],\n'
        "    },\n"
        ")\n"
        "for model_id, result in resp.json()['results'].items():\n"
        "    print(model_id, '->', result['summary'])",
        language="python",
    )
