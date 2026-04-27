/* ═══════════════════════════════════════════════════════
   App interactivity — tabs, generate, compare, batch,
   evaluate, agent, history, copy, export, toasts
   ═══════════════════════════════════════════════════════ */

/* ── Sample texts ─────────────────────────────────────── */
const SAMPLES = {
  climate: `Climate change represents one of the most pressing challenges facing humanity in the 21st century. Rising global temperatures, driven primarily by the accumulation of greenhouse gases in the atmosphere, are causing widespread disruptions to natural ecosystems and human societies alike. Scientists have documented significant increases in extreme weather events, including more intense hurricanes, prolonged droughts, and devastating wildfires. The Intergovernmental Panel on Climate Change (IPCC) has warned that limiting global warming to 1.5°C above pre-industrial levels requires immediate and unprecedented reductions in carbon emissions across all sectors of the economy. Renewable energy sources such as solar and wind power have seen dramatic cost reductions over the past decade, making the transition to a clean energy economy increasingly feasible. However, systemic changes in agriculture, transportation, urban planning, and industrial processes are also necessary to achieve the deep decarbonization required to avoid the worst impacts of climate change.`,
  ai: `Large language models (LLMs) have revolutionized natural language processing over the past few years, demonstrating remarkable capabilities across a wide range of tasks including text generation, translation, summarization, question answering, and code completion. These models, trained on vast corpora of text data using transformer architectures and self-supervised learning objectives, have shown emergent abilities that were not explicitly programmed or anticipated. GPT-4, Claude, Gemini, and other frontier models now perform at or above human level on many standardized benchmarks. Researchers are actively investigating the mechanisms underlying these capabilities through interpretability studies, probing experiments, and theoretical analyses. Key challenges remain, including reducing hallucinations, improving factual accuracy, ensuring alignment with human values, and making these systems more computationally efficient. The rapid pace of development has also sparked important debates around AI safety, bias, misuse, and the long-term societal implications of deploying increasingly capable AI systems at scale.`,
  cloud: `Cloud computing has fundamentally transformed how organizations build, deploy, and operate software systems. The major cloud providers — Amazon Web Services, Microsoft Azure, and Google Cloud Platform — offer hundreds of managed services that abstract away the complexity of infrastructure management, enabling engineering teams to focus on delivering business value. Containerization technologies like Docker and orchestration platforms such as Kubernetes have become standard tools for packaging and deploying applications in cloud environments. The adoption of infrastructure-as-code practices, using tools like Terraform and Pulumi, allows teams to version-control their infrastructure and deploy repeatable, auditable environments. Microservices architectures have enabled organizations to scale individual components independently and deploy changes more frequently with reduced risk. However, the shift to cloud-native development has also introduced new challenges around cost optimization, security, observability, and the complexity of distributed systems. Site Reliability Engineering (SRE) practices and platform engineering teams have emerged to address these operational challenges at scale.`,
};

/* ── State ────────────────────────────────────────────── */
let MODELS = [];
let selectedModel = 'sshleifer/distilbart-cnn-12-6';
let currentMode = 'text';
let lastSummary = '';
let history = JSON.parse(localStorage.getItem('sums_history') || '[]');
let pdfFile = null;
let urlFetched = null; // { title, text }

/* ═══════════════════ TOAST ═══════════════════ */
function toast(msg, type = 'info', dur = 3000) {
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icons[type] || '📢'}</span><span>${msg}</span>`;
  document.getElementById('toastContainer').appendChild(el);
  setTimeout(() => {
    el.classList.add('removing');
    setTimeout(() => el.remove(), 260);
  }, dur);
}

/* ═══════════════════ TAB SWITCHING ═══════════════════ */
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`tab-${tab}`).classList.add('active');
  });
});

/* ═══════════════════ HEALTH CHECK ═══════════════════ */
async function checkHealth() {
  const pill = document.getElementById('statusPill');
  const txt  = document.getElementById('statusText');
  try {
    const h = await API.health();
    pill.className = 'status-pill online';
    txt.textContent = `Online · ${h.loaded_models.length} model(s) loaded`;
  } catch {
    pill.className = 'status-pill offline';
    txt.textContent = 'Offline';
  }
}

/* ═══════════════════ MODELS ═══════════════════ */
async function loadModels() {
  try {
    MODELS = await API.models();
    renderModelGrid();
    renderCompareModelGrid();
    renderBatchModelSelect();
  } catch {
    toast('Failed to load model list', 'error');
  }
}

function renderModelGrid() {
  const grid = document.getElementById('modelGrid');
  grid.innerHTML = '';
  MODELS.forEach(m => {
    const card = document.createElement('div');
    card.className = 'model-card' + (m.model_id === selectedModel ? ' selected' : '');
    card.dataset.id = m.model_id;
    card.innerHTML = `
      <span class="model-card-badge">${m.badge}</span>
      <span class="model-card-name">${m.name}</span>
      <span class="model-card-desc">${m.desc}</span>
      <span class="model-card-size">${m.size}</span>
    `;
    card.addEventListener('click', () => {
      selectedModel = m.model_id;
      document.querySelectorAll('#modelGrid .model-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
    });
    grid.appendChild(card);
  });
}

function renderCompareModelGrid() {
  const grid = document.getElementById('cmpModelGrid');
  grid.innerHTML = '';
  MODELS.forEach((m, i) => {
    const label = document.createElement('label');
    label.className = 'model-checkbox-item';
    label.innerHTML = `<input type="checkbox" value="${m.model_id}" ${i < 2 ? 'checked' : ''}/>${m.name}`;
    grid.appendChild(label);
  });
}

function renderBatchModelSelect() {
  const sel = document.getElementById('batchModelSelect');
  sel.innerHTML = '';
  MODELS.forEach(m => {
    const o = document.createElement('option');
    o.value = m.model_id;
    o.textContent = m.name;
    sel.appendChild(o);
  });
}

/* ═══════════════════ MODE TABS (Summarize) ═══════════════════ */
document.querySelectorAll('.mode-btn[data-mode]').forEach(btn => {
  btn.addEventListener('click', () => {
    currentMode = btn.dataset.mode;
    document.querySelectorAll('.mode-btn[data-mode]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    ['text', 'url', 'pdf'].forEach(m => {
      document.getElementById(`mode-${m}`).classList.toggle('hidden', m !== currentMode);
    });
  });
});

/* ═══════════════════ WORD COUNT ═══════════════════ */
document.getElementById('inputText').addEventListener('input', function () {
  const words = this.value.trim() ? this.value.trim().split(/\s+/).length : 0;
  document.getElementById('wordCount').textContent = `${words} words`;
});

/* ═══════════════════ SAMPLE TEXTS ═══════════════════ */
document.getElementById('sampleSelect').addEventListener('change', function () {
  if (this.value && SAMPLES[this.value]) {
    document.getElementById('inputText').value = SAMPLES[this.value];
    document.getElementById('inputText').dispatchEvent(new Event('input'));
  }
});

/* ═══════════════════ RANGE SLIDERS ═══════════════════ */
document.getElementById('maxLen').addEventListener('input', function () {
  document.getElementById('maxLenVal').textContent = this.value;
});
document.getElementById('minLen').addEventListener('input', function () {
  document.getElementById('minLenVal').textContent = this.value;
});

/* ═══════════════════ PDF DROPZONE ═══════════════════ */
(function setupPdfDropzone() {
  const zone  = document.getElementById('pdfDropzone');
  const input = document.getElementById('pdfInput');
  const status = document.getElementById('pdfStatus');

  zone.addEventListener('click', () => input.click());
  input.addEventListener('change', () => { if (input.files[0]) setPdf(input.files[0]); });

  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const f = e.dataTransfer.files[0];
    if (f && f.name.toLowerCase().endsWith('.pdf')) setPdf(f);
    else toast('Only PDF files are supported', 'error');
  });

  function setPdf(file) {
    pdfFile = file;
    status.textContent = `📄 ${file.name} (${(file.size / 1024).toFixed(0)} KB)`;
    status.classList.remove('hidden');
  }
})();

/* ═══════════════════ URL FETCH ═══════════════════ */
document.getElementById('fetchUrlBtn').addEventListener('click', async () => {
  const url = document.getElementById('urlInput').value.trim();
  const statusEl = document.getElementById('urlStatus');
  const preview  = document.getElementById('urlPreview');
  if (!url) { toast('Enter a URL first', 'error'); return; }

  statusEl.textContent = '⏳ Fetching…';
  preview.classList.add('hidden');
  urlFetched = null;

  try {
    const res = await API.summarizeUrl(url, selectedModel);
    urlFetched = { title: res.title, text: '', sourceUrl: url };
    statusEl.textContent = `✅ Fetched — ${res.extracted_words ?? '?'} words`;
    document.getElementById('urlPreviewTitle').textContent = res.title || url;
    document.getElementById('urlPreviewText').textContent = res.summary
      ? `[Pre-summarized] ${res.summary}` : '';
    preview.classList.remove('hidden');
    // Show result directly
    showResult(res);
  } catch (err) {
    statusEl.textContent = `❌ ${err.message}`;
    toast(err.message, 'error');
  }
});

/* ═══════════════════ GENERATE ═══════════════════ */
document.getElementById('generateBtn').addEventListener('click', handleGenerate);

async function handleGenerate() {
  const btn      = document.getElementById('generateBtn');
  const stream   = document.getElementById('streamToggle').checked;
  const maxLen   = parseInt(document.getElementById('maxLen').value);
  const minLen   = parseInt(document.getElementById('minLen').value);
  const numBeams = parseInt(document.getElementById('numBeams').value);

  btn.disabled = true;

  showLoading('Generating summary…');

  try {
    if (currentMode === 'pdf') {
      if (!pdfFile) { toast('Drop a PDF first', 'error'); showEmpty(); btn.disabled = false; return; }
      const res = await API.summarizePdf(pdfFile, selectedModel, maxLen, minLen);
      showResult(res);
    } else if (currentMode === 'url') {
      const url = document.getElementById('urlInput').value.trim();
      if (!url) { toast('Enter a URL first', 'error'); showEmpty(); btn.disabled = false; return; }
      const res = await API.summarizeUrl(url, selectedModel, maxLen, minLen);
      showResult(res);
    } else {
      const text = document.getElementById('inputText').value.trim();
      if (text.split(/\s+/).length < 10) { toast('Please enter at least 10 words', 'error'); showEmpty(); btn.disabled = false; return; }
      const payload = { text, model_id: selectedModel, max_length: maxLen, min_length: minLen, num_beams: numBeams, length_penalty: 2.0 };

      if (stream) {
        showStreamStart();
        API.streamSummarize(
          payload,
          (token) => appendStreamToken(token),
          ()      => finishStream(payload),
          (err)   => { toast(err.message, 'error'); showEmpty(); btn.disabled = false; }
        );
        return; // btn re-enabled in finishStream
      } else {
        const res = await API.summarize(payload);
        showResult(res);
      }
    }
  } catch (err) {
    toast(err.message, 'error');
    showEmpty();
  } finally {
    btn.disabled = false;
  }
}

/* ── Output helpers ─────────────────────────────────── */
function showEmpty() {
  document.getElementById('emptyState').classList.remove('hidden');
  document.getElementById('loadingState').classList.add('hidden');
  document.getElementById('resultArea').classList.add('hidden');
  document.getElementById('outputActions').style.display = 'none';
}
function showLoading(msg) {
  document.getElementById('emptyState').classList.add('hidden');
  document.getElementById('loadingState').classList.remove('hidden');
  document.getElementById('resultArea').classList.add('hidden');
  document.getElementById('loadingMsg').textContent = msg;
  document.getElementById('outputActions').style.display = 'none';
}
function showResult(res) {
  document.getElementById('emptyState').classList.add('hidden');
  document.getElementById('loadingState').classList.add('hidden');
  document.getElementById('resultArea').classList.remove('hidden');
  document.getElementById('outputActions').style.display = '';
  document.getElementById('summaryCursor').classList.add('hidden');

  const summary = res.summary || '';
  document.getElementById('summaryText').textContent = summary;
  document.getElementById('mIn').textContent   = res.input_tokens  ?? '—';
  document.getElementById('mOut').textContent  = res.output_tokens ?? '—';
  document.getElementById('mComp').textContent = res.compression_ratio ? `${res.compression_ratio.toFixed(1)}×` : '—';
  document.getElementById('mLat').textContent  = res.latency_ms ? `${res.latency_ms.toFixed(0)}ms` : '—';
  document.getElementById('resultModelTag').textContent = res.model_id || selectedModel;

  lastSummary = summary;
  addHistory(res);
  document.getElementById('generateBtn').disabled = false;
}

/* ── Streaming helpers ─────────────────────────────── */
let streamText = '';
function showStreamStart() {
  streamText = '';
  document.getElementById('emptyState').classList.add('hidden');
  document.getElementById('loadingState').classList.add('hidden');
  document.getElementById('resultArea').classList.remove('hidden');
  document.getElementById('outputActions').style.display = '';
  document.getElementById('summaryText').textContent = '';
  document.getElementById('summaryCursor').classList.remove('hidden');
  ['mIn','mOut','mComp','mLat'].forEach(id => document.getElementById(id).textContent = '—');
  document.getElementById('resultModelTag').textContent = selectedModel;
}
function appendStreamToken(token) {
  streamText += (streamText ? ' ' : '') + token;
  document.getElementById('summaryText').textContent = streamText;
}
async function finishStream(payload) {
  document.getElementById('summaryCursor').classList.add('hidden');
  lastSummary = streamText;
  // Fetch proper metrics via non-stream endpoint
  try {
    const res = await API.summarize({ ...payload, num_beams: 1 });
    document.getElementById('mIn').textContent   = res.input_tokens;
    document.getElementById('mOut').textContent  = res.output_tokens;
    document.getElementById('mComp').textContent = `${res.compression_ratio.toFixed(1)}×`;
    document.getElementById('mLat').textContent  = `${res.latency_ms.toFixed(0)}ms`;
    addHistory(res);
  } catch { /* metrics not critical */ }
  document.getElementById('generateBtn').disabled = false;
}

/* ═══════════════════ COPY / EXPORT ═══════════════════ */
document.getElementById('copyBtn').addEventListener('click', () => {
  navigator.clipboard.writeText(lastSummary).then(() => toast('Copied to clipboard!', 'success'));
});

document.getElementById('exportBtn').addEventListener('click', () => {
  document.getElementById('exportMenu').classList.toggle('hidden');
});
document.addEventListener('click', e => {
  if (!e.target.closest('.export-wrap')) {
    document.getElementById('exportMenu').classList.add('hidden');
  }
});

document.querySelectorAll('#exportMenu button').forEach(btn => {
  btn.addEventListener('click', () => {
    const fmt = btn.dataset.fmt;
    const ts = new Date().toISOString().slice(0,16).replace('T','_');
    let content, mime, ext;
    if (fmt === 'txt') {
      content = lastSummary; mime = 'text/plain'; ext = 'txt';
    } else if (fmt === 'json') {
      content = JSON.stringify({
        summary: lastSummary,
        model: selectedModel,
        timestamp: new Date().toISOString(),
      }, null, 2);
      mime = 'application/json'; ext = 'json';
    } else {
      content = `# Summary\n\n${lastSummary}\n\n---\n*Generated by AI Text Summarizer · ${new Date().toLocaleString()}*`;
      mime = 'text/markdown'; ext = 'md';
    }
    const blob = new Blob([content], { type: mime });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `summary_${ts}.${ext}`;
    a.click();
    URL.revokeObjectURL(a.href);
    document.getElementById('exportMenu').classList.add('hidden');
    toast(`Exported as .${ext}`, 'success');
  });
});

/* ═══════════════════ HISTORY ═══════════════════ */
function addHistory(res) {
  const row = {
    time: new Date().toLocaleTimeString(),
    model: res.model_id || selectedModel,
    input: res.input_tokens ?? '—',
    output: res.output_tokens ?? '—',
    compression: res.compression_ratio ? `${res.compression_ratio.toFixed(1)}×` : '—',
    preview: (res.summary || '').slice(0, 80) + ((res.summary || '').length > 80 ? '…' : ''),
  };
  history.unshift(row);
  if (history.length > 50) history = history.slice(0, 50);
  localStorage.setItem('sums_history', JSON.stringify(history));
  renderHistory();
}
function renderHistory() {
  const section = document.getElementById('historySection');
  const tbody   = document.getElementById('historyBody');
  if (!history.length) { section.style.display = 'none'; return; }
  section.style.display = '';
  tbody.innerHTML = history.map(r => `
    <tr>
      <td>${r.time}</td>
      <td><code style="font-size:.72rem">${r.model.split('/').pop()}</code></td>
      <td>${r.input}</td>
      <td>${r.output}</td>
      <td>${r.compression}</td>
      <td class="preview-cell">${escHtml(r.preview)}</td>
    </tr>
  `).join('');
}
document.getElementById('clearHistoryBtn').addEventListener('click', () => {
  history = [];
  localStorage.removeItem('sums_history');
  renderHistory();
});

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

/* ═══════════════════ COMPARE TAB ═══════════════════ */
document.getElementById('compareBtn').addEventListener('click', async () => {
  const text = document.getElementById('cmpText').value.trim();
  if (text.split(/\s+/).length < 20) { toast('Enter at least 20 words', 'error'); return; }

  const modelIds = [...document.querySelectorAll('#cmpModelGrid input:checked')].map(i => i.value);
  if (modelIds.length < 2) { toast('Select at least 2 models', 'error'); return; }

  const btn = document.getElementById('compareBtn');
  btn.disabled = true;
  btn.textContent = '⏳ Running…';

  try {
    const res = await API.compare(text, modelIds);
    renderCompareResults(res);
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '⚖️ Run Comparison';
  }
});

function renderCompareResults(res) {
  const cards = document.getElementById('compareCards');
  cards.innerHTML = '';
  const labels = [];
  const latencies = [];

  Object.entries(res.results).forEach(([modelId, data]) => {
    labels.push(modelId.split('/').pop());
    latencies.push(data.latency_ms ? data.latency_ms.toFixed(0) : 0);

    const card = document.createElement('div');
    card.className = 'compare-card';
    if (data.status === 'error') {
      card.innerHTML = `<div class="compare-card-header"><span class="compare-card-model">${modelId}</span></div><p style="color:var(--red);font-size:.82rem">${data.detail}</p>`;
    } else {
      card.innerHTML = `
        <div class="compare-card-header">
          <span class="compare-card-model">${modelId.split('/').pop()}</span>
          <span class="compare-card-latency">⏱ ${data.latency_ms?.toFixed(0) ?? '?'}ms</span>
        </div>
        <div class="compare-card-text">${escHtml(data.summary || '')}</div>
        <div class="compare-card-metrics">
          <span class="compare-card-metric">📥 ${data.input_tokens} in</span>
          <span class="compare-card-metric">📤 ${data.output_tokens} out</span>
          <span class="compare-card-metric">🗜 ${data.compression_ratio?.toFixed(1) ?? '?'}×</span>
        </div>
      `;
    }
    cards.appendChild(card);
  });

  document.getElementById('compareResults').classList.remove('hidden');
  drawBarChart('compareChart', labels, latencies, 'Latency (ms)');
}

/* ═══════════════════ BATCH TAB ═══════════════════ */
document.querySelectorAll('.mode-btn[data-batch-mode]').forEach(btn => {
  btn.addEventListener('click', () => {
    const mode = btn.dataset.batchMode;
    document.querySelectorAll('.mode-btn[data-batch-mode]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('batchModeManual').classList.toggle('hidden', mode !== 'manual');
    document.getElementById('batchModeCsv').classList.toggle('hidden', mode !== 'csv');
  });
});

document.getElementById('batchInput').addEventListener('input', function () {
  const texts = parseBatchTexts(this.value);
  document.getElementById('batchCount').textContent = texts.length ? `${texts.length} text(s) detected` : '';
});

function parseBatchTexts(raw) {
  return raw.split('---').map(t => t.trim()).filter(t => t.split(/\s+/).length >= 5);
}

/* CSV upload */
(function setupCsvDropzone() {
  const zone  = document.getElementById('csvDropzone');
  const input = document.getElementById('csvInput');
  const status = document.getElementById('csvStatus');

  zone.addEventListener('click', () => input.click());
  input.addEventListener('change', () => { if (input.files[0]) parseCsv(input.files[0]); });
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const f = e.dataTransfer.files[0];
    if (f) parseCsv(f);
  });

  function parseCsv(file) {
    const reader = new FileReader();
    reader.onload = e => {
      const lines = e.target.result.split('\n');
      const header = lines[0].toLowerCase().split(',');
      const textIdx = header.findIndex(h => h.trim() === 'text');
      if (textIdx === -1) { toast('CSV must have a "text" column', 'error'); return; }
      const rows = lines.slice(1).map(l => l.split(',')[textIdx]?.trim()).filter(Boolean);
      document.getElementById('batchInput').value = rows.join('\n---\n');
      document.getElementById('batchInput').dispatchEvent(new Event('input'));
      status.textContent = `✅ ${rows.length} rows loaded from ${file.name}`;
    };
    reader.readAsText(file);
  }
})();

document.getElementById('batchRunBtn').addEventListener('click', async () => {
  const texts = parseBatchTexts(document.getElementById('batchInput').value);
  if (!texts.length) { toast('Add some texts first', 'error'); return; }

  const modelId = document.getElementById('batchModelSelect').value;
  const btn = document.getElementById('batchRunBtn');
  btn.disabled = true;

  const batchResults = document.getElementById('batchResults');
  const progress     = document.getElementById('batchProgress');
  const fill         = document.getElementById('batchProgressFill');
  const label        = document.getElementById('batchProgressLabel');
  const tbody        = document.getElementById('batchBody');

  batchResults.classList.remove('hidden');
  progress.classList.remove('hidden');
  tbody.innerHTML = '';
  document.getElementById('batchResultsTitle').textContent = `Processing ${texts.length} texts…`;

  let done = 0;
  try {
    const res = await API.batch(texts, modelId);
    res.results.forEach((r, i) => {
      done++;
      const pct = Math.round((done / texts.length) * 100);
      fill.style.width = `${pct}%`;
      label.textContent = `${done}/${texts.length} done`;

      const tr = document.createElement('tr');
      if (r.status === 'error') {
        tr.innerHTML = `<td>${i+1}</td><td class="preview-cell">${escHtml(texts[i].slice(0,60))}</td><td colspan="3" style="color:var(--red)">${r.detail}</td><td>❌</td>`;
      } else {
        tr.innerHTML = `
          <td>${i+1}</td>
          <td class="preview-cell">${escHtml(texts[i].slice(0,60))}…</td>
          <td class="preview-cell">${escHtml((r.summary||'').slice(0,80))}…</td>
          <td>${r.compression_ratio?.toFixed(1) ?? '?'}×</td>
          <td>✅</td>
        `;
      }
      tbody.appendChild(tr);
    });
    document.getElementById('batchResultsTitle').textContent = `${done} results · model: ${modelId.split('/').pop()}`;
    progress.classList.add('hidden');
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    btn.disabled = false;
  }
});

/* Download batch CSV */
document.getElementById('batchDownloadBtn').addEventListener('click', () => {
  const rows = [...document.querySelectorAll('#batchBody tr')];
  if (!rows.length) return;
  const csv = ['#,preview,summary,compression,status',
    ...rows.map(tr => [...tr.querySelectorAll('td')].map(td => `"${td.textContent.replace(/"/g,'""')}"`).join(','))
  ].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `batch_results_${Date.now()}.csv`;
  a.click();
});

/* ═══════════════════ EVALUATE TAB ═══════════════════ */
document.getElementById('useLastSummary').addEventListener('click', () => {
  if (lastSummary) {
    document.getElementById('evalGen').value = lastSummary;
    toast('Last summary loaded', 'success');
  } else {
    toast('Generate a summary first', 'error');
  }
});

document.getElementById('evalRunBtn').addEventListener('click', async () => {
  const ref = document.getElementById('evalRef').value.trim();
  const gen = document.getElementById('evalGen').value.trim();
  if (!ref || !gen) { toast('Enter both reference and generated summaries', 'error'); return; }

  const btn = document.getElementById('evalRunBtn');
  btn.disabled = true;
  btn.textContent = '⏳ Computing…';

  try {
    // Local simple ROUGE-like metrics (actual ROUGE from backend optional)
    const metrics = computeLocalMetrics(ref, gen);
    renderEvalResults(metrics, ref, gen);
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '📊 Compute ROUGE Metrics';
  }
});

function computeLocalMetrics(ref, gen) {
  const tokenize = s => s.toLowerCase().replace(/[^\w\s]/g,'').split(/\s+/).filter(Boolean);
  const ngrams = (tokens, n) => {
    const s = new Set();
    for (let i = 0; i <= tokens.length - n; i++) s.add(tokens.slice(i, i+n).join(' '));
    return s;
  };
  const f1 = (a, b) => {
    if (!a.size || !b.size) return 0;
    const inter = [...a].filter(x => b.has(x)).length;
    const p = inter / a.size, r = inter / b.size;
    return (p + r) === 0 ? 0 : 2 * p * r / (p + r);
  };
  const rt = tokenize(ref), gt = tokenize(gen);
  const r1 = f1(ngrams(rt,1), ngrams(gt,1));
  const r2 = f1(ngrams(rt,2), ngrams(gt,2));
  const lcs = longestCommonSubseq(rt, gt);
  const rLp = rt.length ? lcs/rt.length : 0;
  const rLr = gt.length ? lcs/gt.length : 0;
  const rL  = (rLp + rLr) === 0 ? 0 : 2 * rLp * rLr / (rLp + rLr);

  const refSents = ref.split(/[.!?]+/).filter(s=>s.trim().length>3);
  const avgSentLen = refSents.length ? (ref.split(/\s+/).length / refSents.length).toFixed(1) : '—';
  const comp = (rt.length && gt.length) ? (rt.length / gt.length).toFixed(2) : '—';

  return { rouge1: r1, rouge2: r2, rougeL: rL, rougeLsum: rL, avgSentLen, compression: comp };
}

function longestCommonSubseq(a, b) {
  const m = a.length, n = b.length;
  const dp = Array.from({length: m+1}, () => new Array(n+1).fill(0));
  for (let i = 1; i <= m; i++)
    for (let j = 1; j <= n; j++)
      dp[i][j] = a[i-1] === b[j-1] ? dp[i-1][j-1]+1 : Math.max(dp[i-1][j], dp[i][j-1]);
  return dp[m][n];
}

function renderEvalResults(m, ref, gen) {
  const gaugesEl = document.getElementById('rougeGauges');
  gaugesEl.innerHTML = ['rouge1','rouge2','rougeL'].map(key => {
    const val = (m[key]*100).toFixed(1);
    return `
      <div class="rouge-gauge">
        <div class="rouge-gauge-name">${key.toUpperCase()}</div>
        <div class="rouge-gauge-val">${val}%</div>
        <div class="rouge-gauge-bar"><div class="rouge-gauge-bar-fill" style="width:${val}%"></div></div>
      </div>`;
  }).join('');

  document.getElementById('evalComp').textContent     = `${m.compression}×`;
  document.getElementById('evalSentLen').textContent  = m.avgSentLen;
  document.getElementById('evalRougeLsum').textContent = `${(m.rougeLsum*100).toFixed(1)}%`;

  document.getElementById('evalResults').classList.remove('hidden');
  drawRadarChart('evalRadar',
    ['ROUGE-1','ROUGE-2','ROUGE-L'],
    [m.rouge1, m.rouge2, m.rougeL]
  );
}

/* ═══════════════════ AI AGENT TAB ═══════════════════ */
document.getElementById('agentRunBtn').addEventListener('click', runAgent);

async function runAgent() {
  const text = document.getElementById('agentInput').value.trim();
  if (text.split(/\s+/).length < 20) { toast('Enter at least 20 words for the agent', 'error'); return; }

  const btn = document.getElementById('agentRunBtn');
  btn.disabled = true;
  btn.textContent = '⏳ Agent running…';

  // Reset UI
  const stepsEl  = document.getElementById('agentSteps');
  const resultEl = document.getElementById('agentResult');
  stepsEl.classList.remove('hidden');
  resultEl.classList.add('hidden');
  ['1','2','3','4'].forEach(n => {
    setStepStatus(n, 'pending', '○', '');
  });

  // Simulate step-by-step progress while waiting
  setStepStatus('1', 'running', '⏳', 'Counting words, detecting domain…');
  await delay(400);
  setStepStatus('1', 'done', '✓', 'Text analyzed');
  setStepStatus('2', 'running', '⏳', 'Scoring domain keywords…');
  await delay(300);
  setStepStatus('2', 'done', '✓', 'Model selected');
  setStepStatus('3', 'running', '⏳', 'Running inference…');

  try {
    const result = await API.runAgent(text);

    setStepStatus('3', 'done', '✓', `Done in ${result.total_latency_ms.toFixed(0)}ms`);
    setStepStatus('4', 'running', '⏳', 'Computing ROUGE-L…');
    await delay(200);
    setStepStatus('4', 'done', '✓', `ROUGE-L: ${result.quality_score.toFixed(3)}`);

    renderAgentResult(result);
  } catch (err) {
    setStepStatus('3', 'error', '✗', err.message);
    toast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '🤖 Run Agent';
  }
}

function setStepStatus(n, cls, icon, detail) {
  const statusEl = document.getElementById(`agentStep${n}Status`);
  const detailEl = document.getElementById(`agentStep${n}Detail`);
  const stepEl   = document.getElementById(`agentStep${n}`);
  statusEl.className = `step-status ${cls}`;
  statusEl.textContent = icon;
  if (detail) detailEl.textContent = detail;
  stepEl.className = `agent-step ${cls === 'running' ? 'active' : cls === 'done' ? 'done' : ''}`;
}

function renderAgentResult(res) {
  const pct = Math.round(res.confidence * 100);
  const circumference = 2 * Math.PI * 34;
  const offset = circumference * (1 - res.confidence);
  document.getElementById('confidenceCircle').style.strokeDashoffset = offset;
  document.getElementById('confidencePct').textContent = `${pct}%`;

  document.getElementById('agentModelUsed').textContent = res.model_id.split('/').pop();
  document.getElementById('agentDomain').textContent    = res.analysis.domain || '—';
  document.getElementById('agentQuality').textContent   = res.quality_score.toFixed(3);
  document.getElementById('agentLatency').textContent   = `${res.total_latency_ms.toFixed(0)}ms`;
  document.getElementById('agentAttempts').textContent  = res.steps.length;

  document.getElementById('agentSummaryText').textContent = res.summary;
  lastSummary = res.summary;

  const analysisEl = document.getElementById('agentAnalysis');
  const a = res.analysis;
  const items = [
    ['Word count',  a.word_count],
    ['Sentences',   a.sentence_count],
    ['Avg sent len', a.avg_sentence_length],
    ['Complexity',  a.complexity],
    ['Domain',      a.domain],
    ['Max tokens',  a.max_length],
  ];
  analysisEl.innerHTML = items.map(([k, v]) => `
    <div class="analysis-item">
      <div class="analysis-key">${k}</div>
      <div class="analysis-val">${v}</div>
    </div>
  `).join('');

  document.getElementById('agentResult').classList.remove('hidden');
}

/* ═══════════════════ CHARTS (Canvas) ═══════════════════ */
function drawBarChart(canvasId, labels, values, yLabel) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.offsetWidth || 600;
  const H = canvas.height || 180;
  canvas.width = W;

  ctx.clearRect(0, 0, W, H);
  const max = Math.max(...values, 1);
  const pad = { top: 20, right: 20, bottom: 40, left: 50 };
  const chartW = W - pad.left - pad.right;
  const chartH = H - pad.top - pad.bottom;
  const barW = Math.min(60, (chartW / labels.length) - 10);

  ctx.fillStyle = '#8b949e';
  ctx.font = '11px Inter, sans-serif';
  ctx.textAlign = 'right';
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + chartH - (chartH * i / 4);
    ctx.fillText(Math.round(max * i / 4), pad.left - 6, y + 4);
    ctx.strokeStyle = '#30363d';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();
  }

  labels.forEach((lbl, i) => {
    const x = pad.left + (chartW / labels.length) * i + (chartW / labels.length - barW) / 2;
    const barH = (values[i] / max) * chartH;
    const y = pad.top + chartH - barH;

    const grad = ctx.createLinearGradient(0, y, 0, y + barH);
    grad.addColorStop(0, '#667eea');
    grad.addColorStop(1, '#764ba2');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.roundRect(x, y, barW, barH, 4);
    ctx.fill();

    ctx.fillStyle = '#8b949e';
    ctx.textAlign = 'center';
    ctx.font = '10px Inter, sans-serif';
    ctx.fillText(lbl, x + barW / 2, H - pad.bottom + 14);
    ctx.fillStyle = '#e6edf3';
    ctx.fillText(values[i], x + barW / 2, y - 5);
  });
}

function drawRadarChart(canvasId, labels, values) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const W = canvas.offsetWidth || 400;
  const H = canvas.height || 260;
  canvas.width = W;

  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, W, H);

  const cx = W / 2, cy = H / 2;
  const R = Math.min(cx, cy) - 40;
  const n = labels.length;
  const angle = i => (Math.PI * 2 * i / n) - Math.PI / 2;

  // Grid
  for (let ring = 1; ring <= 4; ring++) {
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const r = R * ring / 4;
      const x = cx + r * Math.cos(angle(i));
      const y = cy + r * Math.sin(angle(i));
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.strokeStyle = '#30363d';
    ctx.lineWidth = 1;
    ctx.stroke();
  }
  // Spokes
  for (let i = 0; i < n; i++) {
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + R * Math.cos(angle(i)), cy + R * Math.sin(angle(i)));
    ctx.strokeStyle = '#30363d';
    ctx.lineWidth = 1;
    ctx.stroke();
  }
  // Data polygon
  ctx.beginPath();
  values.forEach((v, i) => {
    const r = R * Math.min(v, 1);
    const x = cx + r * Math.cos(angle(i));
    const y = cy + r * Math.sin(angle(i));
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.closePath();
  ctx.fillStyle = 'rgba(102,126,234,0.2)';
  ctx.fill();
  ctx.strokeStyle = '#667eea';
  ctx.lineWidth = 2;
  ctx.stroke();

  // Labels
  ctx.fillStyle = '#8b949e';
  ctx.font = '12px Inter, sans-serif';
  ctx.textAlign = 'center';
  labels.forEach((lbl, i) => {
    const r = R + 20;
    const x = cx + r * Math.cos(angle(i));
    const y = cy + r * Math.sin(angle(i));
    ctx.fillText(lbl, x, y + 4);
    ctx.fillStyle = '#e6edf3';
    ctx.font = 'bold 11px Inter, sans-serif';
    ctx.fillText(`${(values[i]*100).toFixed(0)}%`, x, y + 18);
    ctx.fillStyle = '#8b949e';
    ctx.font = '12px Inter, sans-serif';
  });
}

/* ═══════════════════ UTILITY ═══════════════════ */
function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

/* ═══════════════════ INIT ═══════════════════ */
(async () => {
  renderHistory();
  await Promise.all([checkHealth(), loadModels()]);
  // Re-check health every 30s
  setInterval(checkHealth, 30_000);
})();
