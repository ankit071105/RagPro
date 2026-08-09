
const API = (location.hostname==='localhost'||location.hostname==='127.0.0.1')
  ? 'http://localhost:8000'
  : '/api';

const state = { view:'chat', theme:'dark', docs:[], filterDoc:'', charts:{}, chatHistory:[] };

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  checkHealth();
  loadDocuments();
  setInterval(checkHealth, 30000);
});

async function checkHealth() {
  try {
    const r = await fetch(`${API}/health`);
    const ok = r.ok;
    document.getElementById('status-dot').className = 'status-dot' + (ok ? '' : ' offline');
    document.getElementById('status-text').textContent = ok ? 'Connected' : 'Offline';
  } catch { document.getElementById('status-dot').className = 'status-dot offline'; document.getElementById('status-text').textContent = 'Offline'; }
}

// ── Theme ────────────────────────────────────────────────────
function toggleTheme() {
  state.theme = state.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', state.theme);
  document.getElementById('theme-icon').className = state.theme === 'dark' ? 'ti ti-moon' : 'ti ti-sun';
  Object.values(state.charts).forEach(c => c?.destroy?.());
  state.charts = {};
  if (state.view === 'dashboard') loadDashboard();
}

// ── Navigation ───────────────────────────────────────────────
function switchView(view) {
  document.querySelectorAll('[id^="view-"]').forEach(v => {
    v.style.display = 'none'; v.style.flex = '';
  });
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  const el = document.getElementById(`view-${view}`);
  el.style.display = 'flex';
  el.style.flex = '1';
  document.getElementById(`tab-${view}`).classList.add('active');
  state.view = view;
  if (view==='dashboard') loadDashboard();
  if (view==='history') loadHistory();
  if (view==='explore') loadExplore();
  if (view==='compare') populateCmpSelects();
}

// ── Documents ────────────────────────────────────────────────
async function loadDocuments() {
  try {
    const r = await fetch(`${API}/documents`);
    state.docs = await r.json();
    renderDocList();
    renderFilterSelect();
  } catch {}
}

function docIcon(type) {
  if (type==='pdf') return 'ti-file-type-pdf';
  if (type==='csv') return 'ti-table';
  return 'ti-file-text';
}

function renderDocList() {
  const el = document.getElementById('doc-list');
  if (!state.docs.length) {
    el.innerHTML = `<div style="padding:20px 14px;text-align:center;color:var(--text3);font-size:12px;">No documents yet</div>`;
    return;
  }
  el.innerHTML = state.docs.map(d => `
    <div class="doc-item ${state.filterDoc===d.filename?'active':''}" onclick="setDocFilter('${d.filename}')" style="animation:slideIn .2s ease;">
      <div class="doc-item-icon ${d.file_type}"><i class="ti ${docIcon(d.file_type)}" aria-hidden="true"></i></div>
      <div class="doc-item-meta">
        <div class="doc-item-name" title="${d.filename}">${d.filename}</div>
        <div class="doc-item-sub">${d.chunk_count} chunks · ${d.source==='kaggle'?'Kaggle':'Uploaded'}</div>
      </div>
      <button class="doc-item-del" onclick="event.stopPropagation();deleteDoc(${d.id},'${d.filename}')" aria-label="Remove ${d.filename}">
        <i class="ti ti-trash" aria-hidden="true"></i>
      </button>
    </div>`).join('');
}

function renderFilterSelect() {
  const sel = document.getElementById('doc-filter');
  const cur = sel.value;
  sel.innerHTML = '<option value="">All documents</option>' +
    state.docs.map(d => `<option value="${d.filename}"${d.filename===cur?' selected':''}>${d.filename}</option>`).join('');
}

function setDocFilter(name) {
  state.filterDoc = state.filterDoc===name ? '' : name;
  document.getElementById('doc-filter').value = state.filterDoc;
  renderDocList();
}

async function deleteDoc(id, name) {
  if (!confirm(`Remove "${name}" from the knowledge base?`)) return;
  await fetch(`${API}/documents/${id}`, {method:'DELETE'});
  if (state.filterDoc===name) state.filterDoc='';
  await loadDocuments();
}

// ── Upload ───────────────────────────────────────────────────
async function handleUpload(files) {
  if (!files?.length) return;
  document.getElementById('upload-modal').style.display = 'flex';
  const list = document.getElementById('upload-list');
  list.innerHTML = '';

  for (const file of files) {
    const id = `u${Date.now()}${Math.random().toString(36).slice(2)}`;
    list.insertAdjacentHTML('beforeend', `
      <div class="upl-item" id="${id}">
        <div class="upl-head">
          <div class="doc-item-icon ${getExt(file.name)}" style="width:28px;height:28px;">
            <i class="ti ${docIcon(getExt(file.name))}" aria-hidden="true"></i>
          </div>
          <span class="upl-name">${file.name}</span>
          <span id="${id}-ic"><div class="spinner"></div></span>
        </div>
        <div class="progress-track"><div class="progress-fill" id="${id}-bar" style="width:0%"></div></div>
        <div class="upl-msg" id="${id}-msg">Uploading…</div>
      </div>`);

    const bar = document.getElementById(`${id}-bar`);
    const msg = document.getElementById(`${id}-msg`);
    const ic  = document.getElementById(`${id}-ic`);
    setTimeout(() => bar.style.width='45%', 100);

    const form = new FormData();
    form.append('file', file);
    try {
      bar.style.width='72%';
      const r = await fetch(`${API}/upload`, {method:'POST',body:form});
      const data = await r.json();
      if (r.ok) {
        bar.style.width='100%'; bar.style.background='var(--green)';
        ic.innerHTML = `<i class="ti ti-circle-check" style="color:var(--green);font-size:18px;" aria-hidden="true"></i>`;
        msg.textContent = `${data.chunk_count} chunks · ${data.page_count} pages processed`;
        msg.style.color = 'var(--green)';
      } else { throw new Error(data.detail||'Upload failed'); }
    } catch(e) {
      bar.style.background='var(--red)';
      ic.innerHTML = `<i class="ti ti-circle-x" style="color:var(--red);font-size:18px;" aria-hidden="true"></i>`;
      msg.textContent = e.message; msg.style.color='var(--red)';
    }
  }
  await loadDocuments();
  setTimeout(() => closeModal('upload-modal'), 2200);
  document.getElementById('file-input').value='';
}

function getExt(name) {
  const e = name.split('.').pop().toLowerCase();
  return e==='csv'?'csv':e==='pdf'?'pdf':'txt';
}

function closeModal(id) { document.getElementById(id).style.display='none'; }

// ── Chat ─────────────────────────────────────────────────────
function setQuery(text) {
  const inp = document.getElementById('chat-input');
  inp.value = text;
  inp.style.height='auto';
  inp.style.height=Math.min(inp.scrollHeight,120)+'px';
  sendQuery();
}

async function sendQuery() {
  const inp = document.getElementById('chat-input');
  const query = inp.value.trim();
  if (!query) return;
  inp.value=''; inp.style.height='44px';

  const msgs = document.getElementById('chat-messages');
  const welcome = msgs.querySelector('[data-welcome]');
  if (welcome) welcome.remove();

  // User message
  msgs.insertAdjacentHTML('beforeend', `
    <div class="msg-wrap user">
      <div class="msg-avatar user"><i class="ti ti-user" aria-hidden="true"></i></div>
      <div class="msg-body"><div class="msg-bubble user">${esc(query)}</div></div>
    </div>`);

  // Typing
  const tid = `t${Date.now()}`;
  msgs.insertAdjacentHTML('beforeend', `
    <div class="msg-wrap" id="${tid}">
      <div class="msg-avatar ai"><i class="ti ti-brain" aria-hidden="true"></i></div>
      <div class="msg-body">
        <div class="msg-bubble ai"><div class="typing-dots"><div class="tdot"></div><div class="tdot"></div><div class="tdot"></div></div></div>
      </div>
    </div>`);
  msgs.scrollTop = msgs.scrollHeight;

  const btn = document.getElementById('send-btn');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div>';

  clearRightPanel();

  try {
    const r = await fetch(`${API}/query`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({query, filter_doc: state.filterDoc||null, history: state.chatHistory.slice(-4)})
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail||'Query failed');

    document.getElementById(tid)?.remove();

    const intentBadge = renderIntentBadge(data.intent);
    const confBadge = data.scores ? renderConfBadge(data.scores.overall) : '';

    msgs.insertAdjacentHTML('beforeend', `
      <div class="msg-wrap">
        <div class="msg-avatar ai"><i class="ti ti-brain" aria-hidden="true"></i></div>
        <div class="msg-body" style="flex:1;min-width:0;">
          <div class="msg-meta" style="margin-bottom:6px;">${intentBadge}${confBadge}</div>
          <div class="msg-bubble ai"><div class="prose" style="font-size:14px;">${marked.parse(data.answer)}</div></div>
        </div>
      </div>`);

    state.chatHistory.push({query, answer:data.answer});

    // Show intent tag
    if (data.intent) {
      document.getElementById('intent-tag').style.display='inline-flex';
      document.getElementById('intent-text').textContent=data.intent;
    }

    renderSources(data.sources||[]);
    if (data.scores) renderScores(data.scores);
    if (data.follow_ups?.length) renderFollowUps(data.follow_ups);

    msgs.scrollTop = msgs.scrollHeight;
  } catch(e) {
    document.getElementById(tid)?.remove();
    msgs.insertAdjacentHTML('beforeend', `
      <div class="msg-wrap">
        <div class="msg-avatar ai" style="background:var(--red);"><i class="ti ti-alert-triangle" aria-hidden="true"></i></div>
        <div class="msg-body"><div class="msg-bubble ai" style="border-color:rgba(239,68,68,.3);color:var(--red);">${esc(e.message)}</div></div>
      </div>`);
    msgs.scrollTop = msgs.scrollHeight;
  } finally {
    btn.disabled=false;
    btn.innerHTML='<i class="ti ti-send" aria-hidden="true"></i>Send';
  }
}

function renderIntentBadge(intent) {
  const map = {factoid:'badge-accent',summary:'badge-green',comparison:'badge-yellow',conversational:'badge-purple'};
  const cls = map[intent]||'badge-gray';
  return `<span class="badge ${cls}"><i class="ti ti-bolt" aria-hidden="true"></i>${intent}</span>`;
}

function renderConfBadge(score) {
  const cls = score>=.8?'badge-green':score>=.6?'badge-yellow':'badge-red';
  return ` <span class="badge ${cls}"><i class="ti ti-stars" aria-hidden="true"></i>${Math.round(score*100)}% confidence</span>`;
}

function clearRightPanel() {
  document.getElementById('sources-content').innerHTML = '<p style="font-size:12px;color:var(--text3);">Retrieving sources…</p>';
  document.getElementById('scores-section').style.display='none';
  document.getElementById('followups-section').style.display='none';
}

function renderSources(sources) {
  const el = document.getElementById('sources-content');
  if (!sources.length) { el.innerHTML='<p style="font-size:12px;color:var(--text3);">No sources retrieved.</p>'; return; }
  el.innerHTML = sources.map((s,i) => `
    <div class="source-card" style="animation:slideIn ${.05+i*.07}s ease;">
      <div class="source-card-head">
        <i class="ti ${docIcon(s.file_type)}" style="font-size:14px;color:var(--text3);" aria-hidden="true"></i>
        <span class="source-card-name" title="${s.filename}">${s.filename}</span>
        <span class="badge badge-gray" style="font-size:10px;flex-shrink:0;">p.${s.page}</span>
      </div>
      <div class="source-card-text">${esc(s.preview)}</div>
      <div style="margin-top:6px;font-size:10px;color:var(--accent-h);font-weight:600;">${(s.score*100).toFixed(1)}% match</div>
    </div>`).join('');
}

function renderScores(scores) {
  document.getElementById('scores-section').style.display='block';
  const items=[
    {label:'Faithfulness',key:'faithfulness',color:'var(--green)'},
    {label:'Relevance',key:'relevance',color:'var(--accent-h)'},
    {label:'Context precision',key:'context_precision',color:'var(--yellow)'},
    {label:'Overall',key:'overall',color:'var(--purple)'}
  ];
  document.getElementById('scores-content').innerHTML = items.map(it => `
    <div class="score-row">
      <div class="score-label-row">
        <span class="score-label">${it.label}</span>
        <span class="score-val" style="color:${it.color};">${Math.round((scores[it.key]||0)*100)}%</span>
      </div>
      <div class="score-track">
        <div class="score-fill" style="width:${Math.round((scores[it.key]||0)*100)}%;background:${it.color};"></div>
      </div>
    </div>`).join('');
}

function renderFollowUps(fus) {
  document.getElementById('followups-section').style.display='block';
  document.getElementById('followups-content').innerHTML = fus.map(q =>
    `<button class="fu-chip" onclick="setQuery(${JSON.stringify(q)})">${esc(q)}</button>`).join('');
}

// ── Search ───────────────────────────────────────────────────
async function doSearch() {
  const query = document.getElementById('search-input').value.trim();
  if (!query) return;
  const el = document.getElementById('search-results');
  el.innerHTML = `<div class="empty-state"><div class="spinner" style="width:24px;height:24px;border-color:rgba(99,102,241,.2);border-top-color:var(--accent);"></div><p style="color:var(--text2);margin-top:8px;">Searching…</p></div>`;
  try {
    const r = await fetch(`${API}/search`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,top_k:8})});
    const data = await r.json();
    if (!data.results?.length) {
      el.innerHTML=`<div class="empty-state"><div class="empty-icon"><i class="ti ti-search-off" aria-hidden="true"></i></div><div class="empty-title">No results found</div><p class="empty-sub">Try a different query or upload more documents.</p></div>`;
      return;
    }
    el.innerHTML = data.results.map((res,i) => `
      <div class="search-result">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
          <span class="badge badge-gray">#${i+1}</span>
          <span style="font-size:12px;font-weight:700;color:var(--accent-h);">${esc(res.filename)}</span>
          <span style="font-size:11px;color:var(--text3);">Page ${res.page}</span>
          <span style="margin-left:auto;" class="badge badge-green">${(res.score*100).toFixed(1)}%</span>
        </div>
        <p style="font-size:13px;color:var(--text);line-height:1.7;">${highlight(res.text, query)}</p>
        <button class="btn" style="margin-top:10px;font-size:11px;" onclick="switchView('chat');setQuery('Tell me more about: '+${JSON.stringify(res.text.slice(0,80))})">
          <i class="ti ti-arrow-right" aria-hidden="true"></i>Ask about this
        </button>
      </div>`).join('');
  } catch(e) {
    el.innerHTML=`<p style="color:var(--red);padding:20px;">${esc(e.message)}</p>`;
  }
}

function highlight(text, query) {
  const words = query.split(' ').filter(w=>w.length>2);
  let r = esc(text.slice(0,500));
  words.forEach(w => {
    const re = new RegExp(esc(w),'gi');
    r = r.replace(re, m=>`<mark style="background:rgba(99,102,241,.2);color:var(--accent-h);border-radius:2px;padding:0 2px;">${m}</mark>`);
  });
  return r + (text.length>500?'…':'');
}

// ── Compare ──────────────────────────────────────────────────
function populateCmpSelects() {
  ['cmp-a','cmp-b'].forEach(id => {
    const sel = document.getElementById(id);
    const cur = sel.value;
    sel.innerHTML = '<option value="">Select document…</option>' +
      state.docs.map(d=>`<option value="${d.filename}"${d.filename===cur?' selected':''}>${d.filename}</option>`).join('');
  });
}

async function doCompare() {
  const docA = document.getElementById('cmp-a').value;
  const docB = document.getElementById('cmp-b').value;
  const query = document.getElementById('cmp-query').value.trim() || 'key findings';
  if (!docA||!docB) { alert('Select both documents'); return; }
  if (docA===docB) { alert('Select two different documents'); return; }

  const el = document.getElementById('compare-result');
  el.innerHTML=`<div class="empty-state"><div class="spinner" style="width:24px;height:24px;border-color:rgba(99,102,241,.2);border-top-color:var(--accent);"></div><p style="color:var(--text2);margin-top:8px;">Comparing documents…</p></div>`;

  try {
    const r = await fetch(`${API}/compare`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,doc_a:docA,doc_b:docB})});
    const data = await r.json();
    const sc = data.scores||{};
    el.innerHTML=`
      <div class="compare-card">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;padding-bottom:14px;border-bottom:1px solid var(--border);">
          <span class="badge badge-accent">${esc(docA)}</span>
          <i class="ti ti-arrows-exchange" style="color:var(--text3);font-size:16px;" aria-hidden="true"></i>
          <span class="badge badge-purple">${esc(docB)}</span>
          <div style="margin-left:auto;display:flex;gap:6px;">
            <span class="badge badge-${sc.overall>=.8?'green':sc.overall>=.6?'yellow':'red'}">
              <i class="ti ti-stars" aria-hidden="true"></i>${Math.round((sc.overall||0)*100)}% score
            </span>
          </div>
        </div>
        <div class="prose" style="font-size:14px;line-height:1.7;">${marked.parse(data.comparison)}</div>
      </div>`;
  } catch(e) {
    el.innerHTML=`<p style="color:var(--red);padding:20px;">${esc(e.message)}</p>`;
  }
}

// ── Explore ──────────────────────────────────────────────────
async function loadExplore() {
  await loadDocuments();
  const el = document.getElementById('explore-grid');
  if (!state.docs.length) {
    el.innerHTML=`<div class="empty-state" style="grid-column:1/-1;"><div class="empty-icon"><i class="ti ti-folder-off" aria-hidden="true"></i></div><div class="empty-title">No documents indexed</div><p class="empty-sub">Upload PDF or CSV files to get started.</p><button class="btn primary" style="margin-top:8px;" onclick="document.getElementById('file-input').click()"><i class="ti ti-upload" aria-hidden="true"></i>Upload documents</button></div>`;
    return;
  }
  el.innerHTML = state.docs.map((d,i) => `
    <div class="doc-card" style="animation:fadeUp ${i*.04}s ease;">
      <div class="doc-card-icon ${d.file_type}"><i class="ti ${docIcon(d.file_type)}" aria-hidden="true"></i></div>
      <div class="doc-card-name" title="${d.filename}">${d.filename}</div>
      <div class="doc-card-meta">${d.file_type.toUpperCase()} · ${d.chunk_count} chunks · ${d.page_count} pages · ${d.source==='kaggle'?'Kaggle':'Uploaded'}</div>
      <div style="font-size:11px;color:var(--text3);margin-bottom:12px;">${new Date(d.uploaded_at).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'})}</div>
      <div class="action-row">
        <button class="btn primary" onclick="switchView('chat');setDocFilter('${d.filename}');"><i class="ti ti-message-2" aria-hidden="true"></i>Ask</button>
        <button class="btn" onclick="showInsights('${d.filename}')"><i class="ti ti-bulb" aria-hidden="true"></i>Insights</button>
        <button class="btn" onclick="showQuestions('${d.filename}')"><i class="ti ti-help-circle" aria-hidden="true"></i>Auto Q</button>
        <button class="btn danger" onclick="deleteDoc(${d.id},'${d.filename}')"><i class="ti ti-trash" aria-hidden="true"></i></button>
      </div>
    </div>`).join('');
}

async function showInsights(filename) {
  openDetailModal(`<i class="ti ti-bulb" aria-hidden="true"></i>Insights — ${filename}`);
  document.getElementById('detail-content').innerHTML=`<div class="empty-state"><div class="spinner" style="width:22px;height:22px;border-color:rgba(99,102,241,.2);border-top-color:var(--accent);"></div><p style="color:var(--text2);margin-top:8px;font-size:13px;">Analyzing document…</p></div>`;
  try {
    const r = await fetch(`${API}/documents/${encodeURIComponent(filename)}/insights`);
    const d = await r.json(); const ins = d.insights;
    document.getElementById('detail-content').innerHTML=`
      <div style="display:flex;flex-direction:column;gap:14px;">
        <div style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--r2);padding:14px;">
          <div style="font-size:10px;font-weight:700;letter-spacing:1px;color:var(--text3);text-transform:uppercase;margin-bottom:8px;">Summary</div>
          <p style="font-size:13px;color:var(--text);line-height:1.6;">${esc(ins.summary||'—')}</p>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
          <div style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--r2);padding:14px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1px;color:var(--text3);text-transform:uppercase;margin-bottom:8px;">Key topics</div>
            <div style="display:flex;flex-wrap:wrap;gap:4px;">${(ins.key_topics||[]).map(t=>`<span class="badge badge-accent">${esc(t)}</span>`).join('')}</div>
          </div>
          <div style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--r2);padding:14px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:1px;color:var(--text3);text-transform:uppercase;margin-bottom:8px;">Key entities</div>
            <div style="display:flex;flex-wrap:wrap;gap:4px;">${(ins.key_entities||[]).map(e=>`<span class="badge badge-purple">${esc(e)}</span>`).join('')}</div>
          </div>
        </div>
        <div style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--r2);padding:14px;">
          <div style="font-size:10px;font-weight:700;letter-spacing:1px;color:var(--text3);text-transform:uppercase;margin-bottom:8px;">Critical points</div>
          <ul style="margin:0;padding-left:16px;">${(ins.critical_points||[]).map(p=>`<li style="font-size:13px;color:var(--text);margin-bottom:4px;line-height:1.6;">${esc(p)}</li>`).join('')}</ul>
        </div>
        <div style="display:flex;gap:8px;">
          <span class="badge badge-green"><i class="ti ti-tag" aria-hidden="true"></i>${esc(ins.document_type||'unknown')}</span>
          <span class="badge badge-${ins.sentiment==='positive'?'green':ins.sentiment==='negative'?'red':'gray'}"><i class="ti ti-mood-smile" aria-hidden="true"></i>${esc(ins.sentiment||'neutral')}</span>
        </div>
      </div>`;
  } catch(e) { document.getElementById('detail-content').innerHTML=`<p style="color:var(--red);">${esc(e.message)}</p>`; }
}

async function showQuestions(filename) {
  openDetailModal(`<i class="ti ti-help-circle" aria-hidden="true"></i>Auto-generated questions — ${filename}`);
  document.getElementById('detail-content').innerHTML=`<div class="empty-state"><div class="spinner" style="width:22px;height:22px;border-color:rgba(99,102,241,.2);border-top-color:var(--accent);"></div><p style="color:var(--text2);margin-top:8px;font-size:13px;">Generating questions…</p></div>`;
  try {
    const r = await fetch(`${API}/documents/${encodeURIComponent(filename)}/questions`);
    const d = await r.json();
    document.getElementById('detail-content').innerHTML=`
      <p style="font-size:12px;color:var(--text2);margin-bottom:12px;">Click any question to ask it in chat.</p>
      <div style="display:flex;flex-direction:column;gap:8px;">
        ${(d.questions||[]).map((q,i)=>`
          <button onclick="closeModal('detail-modal');switchView('chat');setDocFilter('${filename}');setQuery(${JSON.stringify(q)})"
            style="display:flex;align-items:flex-start;gap:10px;padding:12px;border-radius:var(--r2);border:1px solid var(--border);background:none;color:var(--text);font-size:13px;cursor:pointer;text-align:left;transition:all .15s;animation:fadeUp ${i*.05}s ease;"
            onmouseover="this.style.borderColor='var(--accent)';this.style.background='rgba(99,102,241,.05)'"
            onmouseout="this.style.borderColor='var(--border)';this.style.background='none'">
            <span style="font-size:11px;font-weight:700;color:var(--accent);background:rgba(99,102,241,.1);border-radius:4px;padding:2px 6px;flex-shrink:0;margin-top:1px;">${i+1}</span>
            <span style="line-height:1.5;">${esc(q)}</span>
            <i class="ti ti-arrow-right" style="color:var(--text3);font-size:14px;flex-shrink:0;margin-left:auto;margin-top:2px;" aria-hidden="true"></i>
          </button>`).join('')}
      </div>`;
  } catch(e) { document.getElementById('detail-content').innerHTML=`<p style="color:var(--red);">${esc(e.message)}</p>`; }
}

function openDetailModal(title) {
  document.getElementById('detail-title').innerHTML = title;
  document.getElementById('detail-modal').style.display='flex';
}

// ── Dashboard ────────────────────────────────────────────────
async function loadDashboard() {
  try {
    const r = await fetch(`${API}/dashboard`);
    const d = await r.json();
    document.getElementById('s-docs').textContent = d.total_docs;
    document.getElementById('s-queries').textContent = d.total_queries;
    document.getElementById('s-faith').textContent = ((d.avg_faithfulness||0)*100).toFixed(0)+'%';
    document.getElementById('s-rel').textContent = ((d.avg_relevance||0)*100).toFixed(0)+'%';
    document.getElementById('s-score').textContent = ((d.avg_score||0)*100).toFixed(0)+'%';
    buildScoresChart(d.recent_queries||[]);
    buildIntentChart(d.intent_distribution||{});
    buildTrendChart(d.recent_queries||[]);
  } catch {}
}

function chartDefaults() {
  const dark = state.theme==='dark';
  return {
    grid: dark?'rgba(255,255,255,.04)':'rgba(0,0,0,.04)',
    text: dark?'#8b90b8':'#5a5f85',
    tooltipBg: dark?'#1c2030':'#ffffff',
    tooltipText: dark?'#e8eaf6':'#1a1d35'
  };
}

function buildScoresChart(queries) {
  const ctx = document.getElementById('ch-scores');
  if (!ctx) return;
  if (state.charts.scores) state.charts.scores.destroy();
  const d = chartDefaults();
  const rev = [...queries].reverse();
  state.charts.scores = new Chart(ctx, {
    type:'bar',
    data:{
      labels: rev.map((_,i)=>`Q${i+1}`),
      datasets:[
        {label:'Faithfulness',data:rev.map(q=>Math.round((q.faithfulness||0)*100)),backgroundColor:'rgba(16,185,129,.7)',borderRadius:4},
        {label:'Relevance',data:rev.map(q=>Math.round((q.relevance||0)*100)),backgroundColor:'rgba(99,102,241,.7)',borderRadius:4},
        {label:'Overall',data:rev.map(q=>Math.round((q.overall_score||0)*100)),backgroundColor:'rgba(245,158,11,.7)',borderRadius:4}
      ]
    },
    options:{responsive:true,maintainAspectRatio:true,plugins:{legend:{labels:{color:d.text,font:{size:11}}},tooltip:{backgroundColor:d.tooltipBg,titleColor:d.tooltipText,bodyColor:d.tooltipText}},scales:{x:{ticks:{color:d.text,font:{size:10}},grid:{color:d.grid}},y:{ticks:{color:d.text,font:{size:10}},grid:{color:d.grid},min:0,max:100}}}
  });
}

function buildIntentChart(dist) {
  const ctx = document.getElementById('ch-intent');
  if (!ctx) return;
  if (state.charts.intent) state.charts.intent.destroy();
  const d = chartDefaults();
  const labels = Object.keys(dist).length ? Object.keys(dist) : ['No data'];
  const values = Object.values(dist).length ? Object.values(dist) : [1];
  state.charts.intent = new Chart(ctx, {
    type:'doughnut',
    data:{labels,datasets:[{data:values,backgroundColor:['rgba(99,102,241,.8)','rgba(16,185,129,.8)','rgba(245,158,11,.8)','rgba(167,139,250,.8)'],borderWidth:0,borderRadius:4}]},
    options:{responsive:true,maintainAspectRatio:true,plugins:{legend:{labels:{color:d.text,font:{size:11}}},tooltip:{backgroundColor:d.tooltipBg,titleColor:d.tooltipText,bodyColor:d.tooltipText}}}
  });
}

function buildTrendChart(queries) {
  const ctx = document.getElementById('ch-trend');
  if (!ctx) return;
  if (state.charts.trend) state.charts.trend.destroy();
  const d = chartDefaults();
  const rev = [...queries].reverse();
  state.charts.trend = new Chart(ctx, {
    type:'line',
    data:{
      labels:rev.map(q=>new Date(q.created_at).toLocaleDateString('en-US',{month:'short',day:'numeric'})),
      datasets:[{label:'Overall %',data:rev.map(q=>Math.round((q.overall_score||0)*100)),borderColor:'#6366f1',backgroundColor:'rgba(99,102,241,.08)',tension:.4,fill:true,pointBackgroundColor:'#6366f1',pointRadius:4,pointHoverRadius:6}]
    },
    options:{responsive:true,maintainAspectRatio:true,plugins:{legend:{labels:{color:d.text,font:{size:11}}},tooltip:{backgroundColor:d.tooltipBg,titleColor:d.tooltipText,bodyColor:d.tooltipText}},scales:{x:{ticks:{color:d.text,font:{size:10}},grid:{color:d.grid}},y:{ticks:{color:d.text,font:{size:10}},grid:{color:d.grid},min:0,max:100}}}
  });
}

// ── History ──────────────────────────────────────────────────
async function loadHistory() {
  const filter = document.getElementById('hist-filter')?.value||'';
  try {
    const r = await fetch(`${API}/history?limit=100`);
    let data = await r.json();
    if (filter) data = data.filter(d=>d.intent===filter);
    const el = document.getElementById('history-table');
    if (!data.length) {
      el.innerHTML=`<div class="empty-state"><div class="empty-icon"><i class="ti ti-history-off" aria-hidden="true"></i></div><div class="empty-title">No queries yet</div><p class="empty-sub">Start asking questions to see history.</p></div>`;
      return;
    }
    el.innerHTML=`<table class="data-table">
      <thead><tr>
        <th>Query</th><th>Intent</th><th>Faithfulness</th><th>Relevance</th><th>Score</th><th>Time</th>
      </tr></thead>
      <tbody>${data.map(row=>`
        <tr onclick="showHistoryRow(${JSON.stringify(JSON.stringify(row))})" style="cursor:pointer;">
          <td style="max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(row.query)}</td>
          <td><span class="badge badge-accent">${row.intent}</span></td>
          <td style="color:var(--green);font-weight:700;">${Math.round((row.faithfulness||0)*100)}%</td>
          <td style="color:var(--accent-h);font-weight:700;">${Math.round((row.relevance||0)*100)}%</td>
          <td><span class="badge badge-${(row.overall_score||0)>=.8?'green':(row.overall_score||0)>=.6?'yellow':'red'}">${Math.round((row.overall_score||0)*100)}%</span></td>
          <td style="color:var(--text3);font-size:12px;">${new Date(row.created_at).toLocaleString()}</td>
        </tr>`).join('')}
      </tbody></table>`;
  } catch {}
}

function showHistoryRow(rowStr) {
  const row = JSON.parse(rowStr);
  openDetailModal(`<i class="ti ti-history" aria-hidden="true"></i>Query detail`);
  document.getElementById('detail-content').innerHTML=`
    <div style="display:flex;flex-direction:column;gap:12px;">
      <div style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--r2);padding:12px;">
        <div style="font-size:10px;color:var(--text3);font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;">Query</div>
        <p style="font-size:14px;font-weight:600;color:var(--text);">${esc(row.query)}</p>
      </div>
      <div style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--r2);padding:12px;">
        <div style="font-size:10px;color:var(--text3);font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;">Answer</div>
        <div class="prose" style="font-size:13px;">${marked.parse(row.answer)}</div>
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;">
        <span class="badge badge-accent"><i class="ti ti-bolt" aria-hidden="true"></i>${row.intent}</span>
        <span class="badge badge-green"><i class="ti ti-shield-check" aria-hidden="true"></i>${Math.round((row.faithfulness||0)*100)}%</span>
        <span class="badge badge-purple"><i class="ti ti-target" aria-hidden="true"></i>${Math.round((row.relevance||0)*100)}%</span>
        <span class="badge badge-${(row.overall_score||0)>=.8?'green':(row.overall_score||0)>=.6?'yellow':'red'}"><i class="ti ti-stars" aria-hidden="true"></i>${Math.round((row.overall_score||0)*100)}%</span>
      </div>
    </div>`;
}

async function exportCSV() { window.open(`${API}/history/export`, '_blank'); }

// ── Utils ────────────────────────────────────────────────────
function esc(t) { return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
