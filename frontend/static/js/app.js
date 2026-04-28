/* ═══════════════════════════════════════════════════════
   App — all interactivity, state management, charts
   ═══════════════════════════════════════════════════════ */

const SAMPLES = {
  climate: `Climate change represents one of the most pressing challenges facing humanity in the 21st century. Rising global temperatures, driven primarily by the accumulation of greenhouse gases in the atmosphere, are causing widespread disruptions to natural ecosystems and human societies alike. Scientists have documented significant increases in extreme weather events, including more intense hurricanes, prolonged droughts, and devastating wildfires. The Intergovernmental Panel on Climate Change (IPCC) has warned that limiting global warming to 1.5 degrees Celsius above pre-industrial levels requires immediate and unprecedented reductions in carbon emissions across all sectors of the economy. Renewable energy sources such as solar and wind power have seen dramatic cost reductions over the past decade, making the transition to a clean energy economy increasingly feasible. However, systemic changes in agriculture, transportation, urban planning, and industrial processes are also necessary to achieve the deep decarbonization required to avoid the worst impacts of climate change.`,

  ai: `Large language models have revolutionized natural language processing over the past few years, demonstrating remarkable capabilities across a wide range of tasks including text generation, translation, summarization, question answering, and code completion. These models, trained on vast corpora of text data using transformer architectures and self-supervised learning objectives, have shown emergent abilities that were not explicitly programmed or anticipated. GPT-4, Claude, Gemini, and other frontier models now perform at or above human level on many standardized benchmarks. Researchers are actively investigating the mechanisms underlying these capabilities through interpretability studies, probing experiments, and theoretical analyses. Key challenges remain, including reducing hallucinations, improving factual accuracy, ensuring alignment with human values, and making these systems more computationally efficient. The rapid pace of development has also sparked important debates around AI safety, bias, misuse, and the long-term societal implications of deploying increasingly capable AI systems at scale.`,

  cloud: `Cloud computing has fundamentally transformed how organizations build, deploy, and operate software systems. The major cloud providers, Amazon Web Services, Microsoft Azure, and Google Cloud Platform, offer hundreds of managed services that abstract away the complexity of infrastructure management, enabling engineering teams to focus on delivering business value. Containerization technologies like Docker and orchestration platforms such as Kubernetes have become standard tools for packaging and deploying applications in cloud environments. The adoption of infrastructure-as-code practices, using tools like Terraform and Pulumi, allows teams to version-control their infrastructure and deploy repeatable, auditable environments. Microservices architectures have enabled organizations to scale individual components independently and deploy changes more frequently with reduced risk. However, the shift to cloud-native development has also introduced new challenges around cost optimization, security, observability, and the complexity of distributed systems. Site Reliability Engineering practices and platform engineering teams have emerged to address these operational challenges at scale.`,
};

/* ── State ──────────────────────────────────────────── */
let currentMode = 'text';
let currentDomain = 'general';
let currentStyle = 'detailed';
let lastSummary = '';
let history = JSON.parse(localStorage.getItem('sums_history') || '[]');
let pdfFile = null;

/* ── Tiny DOM helpers ───────────────────────────────── */
const $ = id => document.getElementById(id);
function show(id)  { $(id).classList.remove('mode-hidden'); }
function hide(id)  { $(id).classList.add('mode-hidden'); }
function setText(id, val) { $(id).textContent = val; }

/* ═══════════════ TOAST ═══════════════ */
function toast(msg, type = 'info', dur = 4000) {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span class="toast-icon">${type === 'success' ? '✓' : type === 'error' ? '✗' : 'i'}</span><span>${msg}</span>`;
  $('toastContainer').appendChild(el);
  setTimeout(() => { el.classList.add('removing'); setTimeout(() => el.remove(), 300); }, dur);
}

/* ═══════════════ TABS ═══════════════ */
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
  });
});

/* ═══════════════ HEALTH ═══════════════ */
async function checkHealth() {
  try {
    const h = await API.health();
    $('statusPill').className = 'status-pill online';
    $('statusText').textContent = h.loaded_models.length
      ? `Online — ${h.loaded_models[0]?.split(':')[0] ?? 'Ollama'}`
      : 'Online — waiting for model';
  } catch {
    $('statusPill').className = 'status-pill offline';
    $('statusText').textContent = 'Offline — start ollama serve';
  }
}

/* ═══════════════ INPUT MODES ═══════════════ */
document.querySelectorAll('#inputModeSeg .seg-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    currentMode = btn.dataset.mode;
    document.querySelectorAll('#inputModeSeg .seg-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.input-mode').forEach(el => el.classList.remove('active-mode'));
    document.getElementById('mode-' + currentMode).classList.add('active-mode');
  });
});

/* ═══════════════ DOMAIN PILLS ═══════════════ */
document.querySelectorAll('.domain-pill').forEach(btn => {
  btn.addEventListener('click', () => {
    currentDomain = btn.dataset.domain;
    document.querySelectorAll('.domain-pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  });
});

/* ═══════════════ STYLE SELECTOR ═══════════════ */
document.querySelectorAll('.style-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    currentStyle = btn.dataset.style;
    document.querySelectorAll('.style-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  });
});

/* ═══════════════ WORD COUNT ═══════════════ */
$('inputText').addEventListener('input', function () {
  const w = this.value.trim() ? this.value.trim().split(/\s+/).length : 0;
  $('wordCount').textContent = `${w} words`;
});

/* ═══════════════ SAMPLES ═══════════════ */
$('sampleSelect').addEventListener('change', function () {
  if (SAMPLES[this.value]) {
    $('inputText').value = SAMPLES[this.value];
    $('inputText').dispatchEvent(new Event('input'));
  }
});

/* ═══════════════ SLIDERS ═══════════════ */
$('maxLen').addEventListener('input', () => $('maxLenVal').textContent = $('maxLen').value);
$('minLen').addEventListener('input', () => $('minLenVal').textContent = $('minLen').value);

/* ═══════════════ PDF DROPZONE ═══════════════ */
(function () {
  const zone = $('pdfDropzone'), inp = $('pdfInput'), stat = $('pdfStatus');
  zone.addEventListener('click', () => inp.click());
  inp.addEventListener('change', () => inp.files[0] && setPdf(inp.files[0]));
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('drag-over');
    const f = e.dataTransfer.files[0];
    f && f.name.toLowerCase().endsWith('.pdf') ? setPdf(f) : toast('Only PDF files supported', 'error');
  });
  function setPdf(f) {
    pdfFile = f;
    stat.textContent = `${f.name} (${(f.size / 1024).toFixed(0)} KB)`;
    stat.classList.remove('mode-hidden');
  }
})();

/* ═══════════════ URL FETCH ═══════════════ */
$('fetchUrlBtn').addEventListener('click', async () => {
  const url = $('urlInput').value.trim();
  if (!url) { toast('Enter a URL', 'error'); return; }
  const stat = $('urlStatus'), prev = $('urlPreview');
  stat.textContent = 'Fetching...';
  prev.classList.add('mode-hidden');
  setOutputLoading('Fetching and summarizing...');
  try {
    const res = await API.summarizeUrl(url, parseInt($('maxLen').value), parseInt($('minLen').value));
    stat.textContent = `Done — ${res.extracted_words ?? '?'} words extracted`;
    $('urlPreviewTitle').textContent = res.title || url;
    $('urlPreviewText').textContent = res.summary ? res.summary.slice(0, 150) + '...' : '';
    prev.classList.remove('mode-hidden');
    setOutputResult(res);
  } catch (err) {
    stat.textContent = `Error: ${err.message}`;
    setOutputEmpty();
    toast(err.message, 'error');
  }
});

/* ═══════════════ GENERATE ═══════════════ */
$('generateBtn').addEventListener('click', handleGenerate);

async function handleGenerate() {
  const btn = $('generateBtn');
  const maxLen = parseInt($('maxLen').value);
  const minLen = parseInt($('minLen').value);
  const stream = $('streamToggle').checked;
  btn.disabled = true;

  try {
    if (currentMode === 'pdf') {
      if (!pdfFile) { toast('Drop a PDF file first', 'error'); return; }
      setOutputLoading('Extracting and summarizing PDF...');
      const res = await API.summarizePdf(pdfFile, maxLen, minLen);
      setOutputResult(res);

    } else if (currentMode === 'url') {
      const url = $('urlInput').value.trim();
      if (!url) { toast('Enter a URL first', 'error'); return; }
      setOutputLoading('Fetching and summarizing...');
      const res = await API.summarizeUrl(url, maxLen, minLen);
      setOutputResult(res);

    } else {
      const text = $('inputText').value.trim();
      if (!text || text.split(/\s+/).length < 10) { toast('Enter at least 10 words', 'error'); return; }
      const payload = { text, max_length: maxLen, min_length: minLen, domain: currentDomain, style: currentStyle };

      if (stream) {
        setOutputStreaming();
        API.streamSummarize(
          payload,
          token  => appendStreamToken(token),
          ()     => finalizeStream(payload),
          err    => { toast(err.message, 'error'); setOutputEmpty(); btn.disabled = false; }
        );
        return; // re-enabled in finalizeStream
      } else {
        setOutputLoading('Generating summary...');
        const res = await API.summarize(payload);
        setOutputResult(res);
      }
    }
  } catch (err) {
    toast(err.message, 'error');
    setOutputEmpty();
  } finally {
    btn.disabled = false;
  }
}

/* ── Output state machine ───────────────────────────── */
function setOutputEmpty() {
  show('emptyState'); hide('loadingState'); hide('resultArea');
  $('outputActions').classList.add('output-actions-hidden');
}
function setOutputLoading(msg) {
  hide('emptyState'); show('loadingState'); hide('resultArea');
  $('outputActions').classList.add('output-actions-hidden');
  setText('loadingMsg', msg);
}
function setOutputResult(res) {
  hide('emptyState'); hide('loadingState'); show('resultArea');
  $('outputActions').classList.remove('output-actions-hidden');
  hide('summaryCursor');
  const s = res.summary || '';
  $('summaryText').textContent = s;
  setText('mIn',   res.input_tokens  ?? '—');
  setText('mOut',  res.output_tokens ?? '—');
  setText('mComp', res.compression_ratio ? `${res.compression_ratio.toFixed(1)}x` : '—');
  setText('mLat',  res.latency_ms    ? `${res.latency_ms.toFixed(0)}ms` : '—');
  lastSummary = s;
  addHistory(res);
  $('generateBtn').disabled = false;
}

/* ── Streaming ──────────────────────────────────────── */
let streamBuf = '';
function setOutputStreaming() {
  streamBuf = '';
  hide('emptyState'); hide('loadingState'); show('resultArea');
  $('outputActions').classList.remove('output-actions-hidden');
  $('summaryText').textContent = '';
  show('summaryCursor');
  ['mIn','mOut','mComp','mLat'].forEach(id => setText(id, '—'));
}
function appendStreamToken(token) {
  streamBuf += token;
  $('summaryText').textContent = streamBuf;
}
async function finalizeStream(payload) {
  hide('summaryCursor');
  lastSummary = streamBuf;
  // Fetch metrics only (quick call with cached model)
  try {
    const res = await API.summarize({ ...payload, max_length: parseInt($('maxLen').value) });
    setText('mIn',   res.input_tokens);
    setText('mOut',  res.output_tokens);
    setText('mComp', `${res.compression_ratio.toFixed(1)}x`);
    setText('mLat',  `${res.latency_ms.toFixed(0)}ms`);
    addHistory(res);
  } catch { /* metrics optional */ }
  $('generateBtn').disabled = false;
}

/* ═══════════════ COPY / EXPORT ═══════════════ */
$('copyBtn').addEventListener('click', () => {
  if (!lastSummary) return;
  navigator.clipboard.writeText(lastSummary).then(() => toast('Copied!', 'success'));
});

$('exportBtn').addEventListener('click', () => {
  $('exportMenu').classList.toggle('export-menu-open');
});
document.addEventListener('click', e => {
  if (!e.target.closest('.export-wrap')) $('exportMenu').classList.remove('export-menu-open');
});

document.querySelectorAll('#exportMenu button').forEach(btn => {
  btn.addEventListener('click', () => {
    const fmt = btn.dataset.fmt;
    const ts = new Date().toISOString().slice(0, 16).replace('T', '_');
    let content, mime, ext;
    if (fmt === 'json') {
      content = JSON.stringify({ summary: lastSummary, timestamp: new Date().toISOString() }, null, 2);
      mime = 'application/json'; ext = 'json';
    } else if (fmt === 'md') {
      content = `# Summary\n\n${lastSummary}\n\n---\n*${new Date().toLocaleString()}*`;
      mime = 'text/markdown'; ext = 'md';
    } else {
      content = lastSummary; mime = 'text/plain'; ext = 'txt';
    }
    const a = Object.assign(document.createElement('a'), {
      href: URL.createObjectURL(new Blob([content], { type: mime })),
      download: `summary_${ts}.${ext}`,
    });
    a.click(); URL.revokeObjectURL(a.href);
    $('exportMenu').classList.remove('export-menu-open');
    toast(`Exported as .${ext}`, 'success');
  });
});

/* ═══════════════ HISTORY ═══════════════ */
function addHistory(res) {
  history.unshift({
    time: new Date().toLocaleTimeString(),
    input: res.input_tokens ?? '—',
    output: res.output_tokens ?? '—',
    compression: res.compression_ratio ? `${res.compression_ratio.toFixed(1)}x` : '—',
    preview: (res.summary || '').slice(0, 90),
  });
  if (history.length > 40) history.pop();
  localStorage.setItem('sums_history', JSON.stringify(history));
  renderHistory();
}
function renderHistory() {
  const section = $('historySection'), body = $('historyBody');
  if (!history.length) { section.classList.add('mode-hidden'); return; }
  section.classList.remove('mode-hidden');
  body.innerHTML = history.map(r => `
    <tr>
      <td>${r.time}</td>
      <td>${r.input}</td><td>${r.output}</td><td>${r.compression}</td>
      <td class="preview-cell">${esc(r.preview)}</td>
    </tr>`).join('');
}
$('clearHistoryBtn').addEventListener('click', () => {
  history = []; localStorage.removeItem('sums_history'); renderHistory();
});
function esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

/* ═══════════════ COMPARE ═══════════════ */
$('compareBtn').addEventListener('click', async () => {
  const text = $('cmpText').value.trim();
  if (text.split(/\s+/).length < 20) { toast('Enter at least 20 words', 'error'); return; }
  const btn = $('compareBtn');
  btn.disabled = true; btn.textContent = 'Running...';
  try {
    const res = await API.compare(text);
    renderCompareResults(res);
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    btn.disabled = false; btn.textContent = 'Run Comparison';
  }
});

function renderCompareResults(res) {
  const cards = $('compareCards');
  cards.innerHTML = '';
  const labels = [], lengths = [];
  const styleNames = { brief: 'Brief', detailed: 'Detailed' };

  Object.entries(res.results).forEach(([style, data]) => {
    labels.push(styleNames[style] || style);
    lengths.push(data.output_tokens ?? 0);

    const card = document.createElement('div');
    card.className = 'compare-card';
    if (data.status === 'error') {
      card.innerHTML = `<div class="compare-card-header"><span class="compare-card-model">${styleNames[style] || style}</span></div><p style="color:var(--red);font-size:.82rem">${esc(data.detail)}</p>`;
    } else {
      card.innerHTML = `
        <div class="compare-card-header">
          <span class="compare-card-model">${styleNames[style] || style} Summary</span>
          <span class="compare-card-latency">${data.latency_ms?.toFixed(0) ?? '?'}ms</span>
        </div>
        <div class="compare-card-text">${esc(data.summary || '')}</div>
        <div class="compare-card-metrics">
          <span class="compare-card-metric">${data.input_tokens ?? '?'} in</span>
          <span class="compare-card-metric">${data.output_tokens ?? '?'} out</span>
          <span class="compare-card-metric">${data.compression_ratio?.toFixed(1) ?? '?'}x compression</span>
        </div>`;
    }
    cards.appendChild(card);
  });

  $('compareResults').classList.remove('mode-hidden');
  drawBarChart('compareChart', labels, lengths);
}

/* ═══════════════ BATCH ═══════════════ */
document.querySelectorAll('.seg-btn[data-batch-mode]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.seg-btn[data-batch-mode]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const m = btn.dataset.batchMode;
    $('batchModeManual').classList.toggle('mode-hidden', m !== 'manual');
    $('batchModeCsv').classList.toggle('mode-hidden', m !== 'csv');
  });
});

$('batchInput').addEventListener('input', function () {
  const n = parseBatch(this.value).length;
  $('batchCount').textContent = n ? `${n} text(s) detected` : '';
});

function parseBatch(raw) {
  return raw.split('---').map(t => t.trim()).filter(t => t.split(/\s+/).length >= 5);
}

(function () {
  const zone = $('csvDropzone'), inp = $('csvInput'), stat = $('csvStatus');
  zone.addEventListener('click', () => inp.click());
  inp.addEventListener('change', () => inp.files[0] && loadCsv(inp.files[0]));
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => { e.preventDefault(); zone.classList.remove('drag-over'); e.dataTransfer.files[0] && loadCsv(e.dataTransfer.files[0]); });
  function loadCsv(f) {
    const r = new FileReader();
    r.onload = e => {
      const lines = e.target.result.split('\n');
      const idx = lines[0].toLowerCase().split(',').findIndex(h => h.trim() === 'text');
      if (idx < 0) { toast('CSV needs a "text" column', 'error'); return; }
      const rows = lines.slice(1).map(l => l.split(',')[idx]?.trim()).filter(Boolean);
      $('batchInput').value = rows.join('\n---\n');
      $('batchInput').dispatchEvent(new Event('input'));
      stat.textContent = `${rows.length} rows loaded from ${f.name}`;
    };
    r.readAsText(f);
  }
})();

$('batchRunBtn').addEventListener('click', async () => {
  const texts = parseBatch($('batchInput').value);
  if (!texts.length) { toast('Add texts separated by ---', 'error'); return; }
  const btn = $('batchRunBtn');
  btn.disabled = true;
  $('batchResults').classList.remove('mode-hidden');
  $('batchProgress').classList.remove('mode-hidden');
  $('batchBody').innerHTML = '';
  setText('batchResultsTitle', `Processing ${texts.length} texts...`);
  try {
    const res = await API.batch(texts);
    $('batchProgress').classList.add('mode-hidden');
    res.results.forEach((r, i) => {
      const pct = Math.round(((i + 1) / texts.length) * 100);
      $('batchProgressFill').style.width = `${pct}%`;
      $('batchProgressLabel').textContent = `${i + 1}/${texts.length}`;
      const fullInput = texts[i];
      const fullSummary = r.summary || '';
      const tr = document.createElement('tr');
      tr.dataset.fullInput = fullInput;
      tr.dataset.fullSummary = fullSummary;
      if (r.status === 'error') {
        tr.innerHTML = `<td>${i+1}</td><td class="preview-cell">${esc(fullInput.slice(0,60))}…</td><td colspan="2" style="color:var(--red)">${esc(r.detail)}</td><td>Failed</td>`;
      } else {
        const previewId = `batchPreview${i}`;
        tr.innerHTML = `<td>${i+1}</td><td class="preview-cell">${esc(fullInput.slice(0,60))}…</td><td class="preview-cell" style="cursor:pointer" onclick="toggleBatchPreview('${previewId}')">${esc(fullSummary.slice(0,80))}… <span style="color:var(--accent);font-size:.75rem">[expand]</span></td><td>${r.compression_ratio?.toFixed(1)??'?'}x</td><td style="color:var(--green)">Done</td>`;
      }
      $('batchBody').appendChild(tr);
      if (r.status !== 'error') {
        const previewRow = document.createElement('tr');
        previewRow.id = `batchPreview${i}`;
        previewRow.style.display = 'none';
        previewRow.innerHTML = `<td colspan="5" style="padding:12px 16px;background:rgba(102,126,234,.04);border-top:none"><div style="font-size:.8rem;color:var(--text-muted);margin-bottom:6px">Full summary:</div><div style="font-size:.875rem;line-height:1.6">${esc(fullSummary)}</div></td>`;
        $('batchBody').appendChild(previewRow);
      }
    });
    setText('batchResultsTitle', `${res.results.length} results`);
  } catch (err) { toast(err.message, 'error'); }
  finally { btn.disabled = false; }
});

function toggleBatchPreview(id) {
  const row = document.getElementById(id);
  if (!row) return;
  row.style.display = row.style.display === 'none' ? '' : 'none';
}
window.toggleBatchPreview = toggleBatchPreview;

$('batchDownloadBtn').addEventListener('click', () => {
  const rows = [...document.querySelectorAll('#batchBody tr[data-full-input]')];
  if (!rows.length) return;
  const escape = v => `"${(v||'').replace(/"/g,'""')}"`;
  const csv = ['#,input,summary,compression,status', ...rows.map((tr, i) => {
    const tds = tr.querySelectorAll('td');
    const num = tds[0]?.textContent || (i+1);
    const compression = tds[3]?.textContent || '';
    const status = tds[4]?.textContent || '';
    return [escape(num), escape(tr.dataset.fullInput), escape(tr.dataset.fullSummary), escape(compression), escape(status)].join(',');
  })].join('\n');
  const a = Object.assign(document.createElement('a'), {
    href: URL.createObjectURL(new Blob([csv], { type: 'text/csv' })),
    download: `batch_${Date.now()}.csv`,
  });
  a.click();
});

/* ═══════════════ EVALUATE ═══════════════ */
$('useLastSummary').addEventListener('click', () => {
  if (!lastSummary) { toast('Generate a summary first', 'error'); return; }
  $('evalGen').value = lastSummary;
  toast('Loaded', 'success');
});

$('evalRunBtn').addEventListener('click', () => {
  const ref = $('evalRef').value.trim(), gen = $('evalGen').value.trim();
  if (!ref || !gen) { toast('Fill in both fields', 'error'); return; }
  const btn = $('evalRunBtn');
  btn.disabled = true; btn.textContent = 'Computing...';
  const m = rouge(ref, gen);
  renderEval(m);
  btn.disabled = false; btn.textContent = 'Compute ROUGE Metrics';
});

function rouge(ref, gen) {
  const tok = s => s.toLowerCase().replace(/[^\w\s]/g,'').split(/\s+/).filter(Boolean);
  const ngrams = (t, n) => { const s = new Set(); for (let i = 0; i <= t.length-n; i++) s.add(t.slice(i,i+n).join(' ')); return s; };
  const f1 = (a, b) => { if (!a.size||!b.size) return 0; const i=[...a].filter(x=>b.has(x)).length; const p=i/a.size,r=i/b.size; return p+r===0?0:2*p*r/(p+r); };
  const rt = tok(ref), gt = tok(gen);
  const r1 = f1(ngrams(rt,1), ngrams(gt,1));
  const r2 = f1(ngrams(rt,2), ngrams(gt,2));
  const lcs = lcsLen(rt, gt);
  const rLp = rt.length?lcs/rt.length:0, rLr=gt.length?lcs/gt.length:0;
  const rL = rLp+rLr===0?0:2*rLp*rLr/(rLp+rLr);
  const sents = ref.split(/[.!?]+/).filter(s=>s.trim().length>3);
  return { r1, r2, rL, comp: rt.length&&gt.length?(rt.length/gt.length).toFixed(2):'—', avgSent: sents.length?(ref.split(/\s+/).length/sents.length).toFixed(1):'—' };
}
function lcsLen(a, b) {
  const dp = Array.from({length:a.length+1},()=>new Array(b.length+1).fill(0));
  for (let i=1;i<=a.length;i++) for (let j=1;j<=b.length;j++) dp[i][j]=a[i-1]===b[j-1]?dp[i-1][j-1]+1:Math.max(dp[i-1][j],dp[i][j-1]);
  return dp[a.length][b.length];
}
function renderEval(m) {
  $('rougeGauges').innerHTML = [['ROUGE-1',m.r1],['ROUGE-2',m.r2],['ROUGE-L',m.rL]].map(([k,v])=>`
    <div class="rouge-gauge">
      <div class="rouge-gauge-name">${k}</div>
      <div class="rouge-gauge-val">${(v*100).toFixed(1)}%</div>
      <div class="rouge-gauge-bar"><div class="rouge-gauge-bar-fill" style="width:${(v*100).toFixed(1)}%"></div></div>
    </div>`).join('');
  setText('evalComp', `${m.comp}x`);
  setText('evalSentLen', m.avgSent);
  setText('evalRougeLsum', `${(m.rL*100).toFixed(1)}%`);
  $('evalResults').classList.remove('mode-hidden');
  drawRadar('evalRadar', ['ROUGE-1','ROUGE-2','ROUGE-L'], [m.r1, m.r2, m.rL]);
}

/* ═══════════════ AI AGENT ═══════════════ */
$('agentRunBtn').addEventListener('click', runAgent);

async function runAgent() {
  const text = $('agentInput').value.trim();
  if (text.split(/\s+/).length < 20) { toast('Enter at least 20 words', 'error'); return; }
  const btn = $('agentRunBtn');
  btn.disabled = true; btn.textContent = 'Running...';

  $('agentSteps').classList.remove('mode-hidden');
  $('agentResult').classList.add('mode-hidden');
  ['1','2','3','4'].forEach(n => step(n,'pending','—',''));

  step('1','running','...','Counting words, detecting domain...');
  await wait(350);
  step('1','done','Done','Text analyzed');
  step('2','running','...','Choosing prompt strategy...');
  await wait(250);
  step('2','done','Done','Strategy selected');
  step('3','running','...','Sending to Llama 3.3 70B...');

  try {
    const res = await API.runAgent(text);
    step('3','done','Done', `Completed in ${res.total_latency_ms?.toFixed(0)}ms`);
    step('4','running','...','Computing ROUGE-L quality score...');
    await wait(200);
    step('4','done','Done', `ROUGE-L: ${res.quality_score?.toFixed(3)}`);
    renderAgentResult(res);
  } catch (err) {
    step('3','error','Failed', err.message);
    toast(`Agent error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false; btn.textContent = 'Run Agent';
  }
}

const STEP_ICONS = {
  pending: `<svg width="18" height="18" viewBox="0 0 18 18"><circle cx="9" cy="9" r="7" fill="none" stroke="currentColor" stroke-width="1.5" stroke-dasharray="3 3"/></svg>`,
  running: `<span class="step-spinner"></span>`,
  done:    `<svg width="18" height="18" viewBox="0 0 18 18"><circle cx="9" cy="9" r="8" fill="var(--green)" fill-opacity=".15"/><circle cx="9" cy="9" r="8" fill="none" stroke="var(--green)" stroke-width="1.5"/><polyline points="5.5,9 7.8,11.5 12.5,6.5" fill="none" stroke="var(--green)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  error:   `<svg width="18" height="18" viewBox="0 0 18 18"><circle cx="9" cy="9" r="8" fill="var(--red)" fill-opacity=".15"/><circle cx="9" cy="9" r="8" fill="none" stroke="var(--red)" stroke-width="1.5"/><line x1="6" y1="6" x2="12" y2="12" stroke="var(--red)" stroke-width="2" stroke-linecap="round"/><line x1="12" y1="6" x2="6" y2="12" stroke="var(--red)" stroke-width="2" stroke-linecap="round"/></svg>`,
};
function step(n, cls, _icon, detail) {
  const s = $(`agentStep${n}Status`), d = $(`agentStep${n}Detail`), el = $(`agentStep${n}`);
  s.className = `step-status ${cls}`; s.innerHTML = STEP_ICONS[cls] || '';
  if (detail) d.textContent = detail;
  el.className = `agent-step${cls==='running'?' active':cls==='done'?' done':''}`;
}

function renderAgentResult(res) {
  const circ = 2 * Math.PI * 34;
  $('confidenceCircle').style.strokeDashoffset = circ * (1 - (res.confidence || 0));
  setText('confidencePct', `${Math.round((res.confidence||0)*100)}%`);
  setText('agentDomain',  res.analysis?.domain || '—');
  setText('agentStyle',   res.analysis?.style  || '—');
  setText('agentQuality', res.quality_score?.toFixed(3) || '—');
  setText('agentLatency', `${res.total_latency_ms?.toFixed(0)}ms`);
  setText('agentAttempts', res.steps?.length ?? 1);
  $('agentSummaryText').textContent = res.summary;
  lastSummary = res.summary;

  const a = res.analysis || {};
  $('agentAnalysis').innerHTML = [
    ['Word count',      a.word_count],
    ['Sentences',       a.sentence_count],
    ['Avg sent length', a.avg_sentence_length],
    ['Complexity',      a.complexity],
    ['Domain',          a.domain],
    ['Max tokens',      a.max_length],
  ].map(([k,v]) => `<div class="analysis-item"><div class="analysis-key">${k}</div><div class="analysis-val">${v??'—'}</div></div>`).join('');

  $('agentResult').classList.remove('mode-hidden');
}

$('agentCopyBtn').addEventListener('click', () => {
  if (!lastSummary) return;
  navigator.clipboard.writeText(lastSummary).then(() => toast('Copied!', 'success'));
});

/* ═══════════════ CHARTS ═══════════════ */
function drawBarChart(id, labels, values) {
  const c = $(id); if (!c) return;
  const W = c.offsetWidth || 500, H = c.height || 160;
  c.width = W;
  const ctx = c.getContext('2d');
  ctx.clearRect(0,0,W,H);
  const max = Math.max(...values, 1);
  const pad = {t:20, r:20, b:36, l:40};
  const cW = W-pad.l-pad.r, cH = H-pad.t-pad.b;
  const bW = Math.min(80, cW/labels.length - 16);
  ctx.fillStyle='#8b949e'; ctx.font='11px Inter,sans-serif'; ctx.textAlign='right';
  for (let i=0;i<=4;i++) {
    const y=pad.t+cH-cH*i/4;
    ctx.fillText(Math.round(max*i/4), pad.l-5, y+4);
    ctx.strokeStyle='#30363d'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(W-pad.r,y); ctx.stroke();
  }
  labels.forEach((lbl,i) => {
    const x = pad.l + (cW/labels.length)*i + (cW/labels.length-bW)/2;
    const bH = (values[i]/max)*cH, y = pad.t+cH-bH;
    const g = ctx.createLinearGradient(0,y,0,y+bH);
    g.addColorStop(0,'#667eea'); g.addColorStop(1,'#764ba2');
    ctx.fillStyle=g; ctx.beginPath(); ctx.roundRect(x,y,bW,bH,4); ctx.fill();
    ctx.fillStyle='#8b949e'; ctx.textAlign='center'; ctx.font='11px Inter,sans-serif';
    ctx.fillText(lbl, x+bW/2, H-pad.b+14);
    ctx.fillStyle='#e6edf3'; ctx.font='bold 11px Inter,sans-serif';
    ctx.fillText(values[i], x+bW/2, y-5);
  });
}

function drawRadar(id, labels, values) {
  const c = $(id); if (!c) return;
  const W = c.offsetWidth||360, H = c.height||260;
  c.width = W;
  const ctx = c.getContext('2d');
  ctx.clearRect(0,0,W,H);
  const cx=W/2, cy=H/2, R=Math.min(cx,cy)-44, n=labels.length;
  const ang = i => Math.PI*2*i/n - Math.PI/2;
  for (let r=1;r<=4;r++) {
    ctx.beginPath();
    for (let i=0;i<n;i++) { const a=ang(i),l=R*r/4; i?ctx.lineTo(cx+l*Math.cos(a),cy+l*Math.sin(a)):ctx.moveTo(cx+l*Math.cos(a),cy+l*Math.sin(a)); }
    ctx.closePath(); ctx.strokeStyle='#30363d'; ctx.lineWidth=1; ctx.stroke();
  }
  for (let i=0;i<n;i++) { ctx.beginPath(); ctx.moveTo(cx,cy); ctx.lineTo(cx+R*Math.cos(ang(i)),cy+R*Math.sin(ang(i))); ctx.strokeStyle='#30363d'; ctx.lineWidth=1; ctx.stroke(); }
  ctx.beginPath();
  values.forEach((v,i)=>{ const r=R*Math.min(v,1),a=ang(i); i?ctx.lineTo(cx+r*Math.cos(a),cy+r*Math.sin(a)):ctx.moveTo(cx+r*Math.cos(a),cy+r*Math.sin(a)); });
  ctx.closePath(); ctx.fillStyle='rgba(102,126,234,0.22)'; ctx.fill(); ctx.strokeStyle='#667eea'; ctx.lineWidth=2; ctx.stroke();
  ctx.textAlign='center';
  labels.forEach((lbl,i)=>{ const r=R+22,a=ang(i); ctx.fillStyle='#8b949e'; ctx.font='12px Inter,sans-serif'; ctx.fillText(lbl,cx+r*Math.cos(a),cy+r*Math.sin(a)+4); ctx.fillStyle='#e6edf3'; ctx.font='bold 11px Inter,sans-serif'; ctx.fillText(`${(values[i]*100).toFixed(0)}%`,cx+r*Math.cos(a),cy+r*Math.sin(a)+18); });
}

/* ═══════════════ UTIL ═══════════════ */
function wait(ms) { return new Promise(r => setTimeout(r, ms)); }

/* ═══════════════ INIT ═══════════════ */
(async () => {
  setOutputEmpty();
  renderHistory();
  await checkHealth();
  setInterval(checkHealth, 30000);
})();
