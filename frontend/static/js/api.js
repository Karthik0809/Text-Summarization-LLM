/* API communication layer */
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
  async health() {
    const r = await fetch(`${BASE}/health`);
    if (!r.ok) throw new Error('Offline');
    return r.json();
  },

  async summarize(payload) {
    return _post('/summarize', payload);
  },

  async summarizeUrl(url, maxLength = 350, minLength = 50) {
    return _post('/summarize/url', { url, max_length: maxLength, min_length: minLength });
  },

  async summarizePdf(file, maxLength = 350, minLength = 50) {
    const fd = new FormData();
    fd.append('file', file);
    const params = new URLSearchParams({ max_length: maxLength, min_length: minLength });
    const res = await fetch(`${BASE}/summarize/pdf?${params}`, { method: 'POST', body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },

  streamSummarize(payload, onToken, onDone, onError) {
    fetch(`${BASE}/summarize/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(async res => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        onError(new Error(err.detail || `HTTP ${res.status}`)); return;
      }
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const lines = buf.split('\n'); buf = lines.pop();
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6);
          if (data === '[DONE]') { onDone(); return; }
          if (data.startsWith('[ERROR]')) { onError(new Error(data.slice(8))); return; }
          if (data.trim()) onToken(data);
        }
      }
      onDone();
    }).catch(onError);
  },

  async compare(text) {
    return _post('/compare', { text, max_length: 400, min_length: 30 });
  },

  async batch(texts) {
    return _post('/summarize/batch', { texts, max_length: 350, min_length: 50 });
  },

  async runAgent(text) {
    return _post('/agent/run', { text });
  },
};

window.API = API;
