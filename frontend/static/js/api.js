/* ═══════════════════════════════════════════════
   API communication layer — all fetch/SSE calls
   ═══════════════════════════════════════════════ */

const BASE = '/api/v1';

async function _post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

const API = {
  /* ── Health ─────────────────────────────────────────── */
  async health() {
    const res = await fetch(`${BASE}/health`);
    if (!res.ok) throw new Error('Offline');
    return res.json();
  },

  /* ── Models ─────────────────────────────────────────── */
  async models() {
    const res = await fetch(`${BASE}/models`);
    if (!res.ok) throw new Error('Failed to fetch models');
    return res.json();
  },

  /* ── Summarize: text ────────────────────────────────── */
  async summarize(payload) {
    return _post('/summarize', payload);
  },

  /* ── Summarize: URL ─────────────────────────────────── */
  async summarizeUrl(url, modelId, maxLength = 256, minLength = 50) {
    return _post('/summarize/url', {
      url,
      model_id: modelId,
      max_length: maxLength,
      min_length: minLength,
    });
  },

  /* ── Summarize: PDF (multipart) ─────────────────────── */
  async summarizePdf(file, modelId, maxLength = 256, minLength = 50) {
    const fd = new FormData();
    fd.append('file', file);
    const params = new URLSearchParams({ model_id: modelId, max_length: maxLength, min_length: minLength });
    const res = await fetch(`${BASE}/summarize/pdf?${params}`, { method: 'POST', body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },

  /* ── Summarize: streaming SSE ───────────────────────── */
  streamSummarize(payload, onToken, onDone, onError) {
    fetch(`${BASE}/summarize/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        onError(new Error(err.detail || `HTTP ${res.status}`));
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6);
          if (data === '[DONE]') { onDone(); return; }
          if (data.startsWith('[ERROR]')) { onError(new Error(data.slice(8))); return; }
          onToken(data);
        }
      }
      onDone();
    }).catch(onError);
  },

  /* ── Compare ────────────────────────────────────────── */
  async compare(text, modelIds, maxLength = 256, minLength = 50) {
    return _post('/compare', {
      text,
      model_ids: modelIds,
      max_length: maxLength,
      min_length: minLength,
    });
  },

  /* ── Batch ──────────────────────────────────────────── */
  async batch(texts, modelId, maxLength = 256, minLength = 50) {
    return _post('/summarize/batch', {
      texts,
      model_id: modelId,
      max_length: maxLength,
      min_length: minLength,
    });
  },

  /* ── Evaluate (ROUGE) ───────────────────────────────── */
  async evaluate(reference, generated) {
    return _post('/evaluate', { reference, generated });
  },

  /* ── AI Agent ───────────────────────────────────────── */
  async runAgent(text) {
    return _post('/agent/run', { text });
  },
};

window.API = API;
