let ws = null;
let selectedTool = 'grok';            // primary video tool (kept = selectedTools[0])
let selectedTools = ['grok'];         // video generation — one or more
let selectedVoices = ['elevenlabs'];  // voice generation — one or both
let selectedBrain = 'claude';         // AI brain (single)
let selectedMode = 'auto';
let selectedVideoType = 'product_demo';
let selectedCharacterId = null;
let currentVideoId = null;
let clientId = Math.random().toString(36).substring(2, 10);
let productImageBase64 = null;
let selectedScriptMode = 'ai';
let batchCount = 1;

// ─── Image Upload ───────────────────────────────────────

function handleProductImageUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    productImageBase64 = e.target.result;
    const preview = document.getElementById('imagePreview');
    preview.innerHTML = `<img src="${productImageBase64}" alt="Product Image" />`;
    preview.classList.remove('hidden');
    document.getElementById('imageUploadText').textContent = '✓ Image loaded';
  };
  reader.readAsDataURL(file);
}

// ─── Script Mode ────────────────────────────────────────

function selectScriptMode(mode) {
  selectedScriptMode = mode;
  document.querySelectorAll('.script-mode-btn').forEach(b => b.classList.remove('active'));
  document.querySelector(`[data-mode="${mode}"]`).classList.add('active');

  const scriptInput = document.getElementById('scriptInput');
  if (mode === 'manual') {
    scriptInput.style.display = 'block';
  } else {
    scriptInput.style.display = 'none';
    scriptInput.value = '';
  }
}

// ─── Batch Count ────────────────────────────────────────

function updateBatchCount() {
  batchCount = parseInt(document.getElementById('batchCount').value) || 1;
  batchCount = Math.max(1, Math.min(10, batchCount));
}

document.addEventListener('change', (e) => {
  if (e.target.id === 'batchCount') updateBatchCount();
});

// ─── Tool / Mode / Character Selection ─────────────────

function selectVideoType(type) {
  selectedVideoType = type;
  document.querySelectorAll('.type-card').forEach(c => c.classList.remove('active'));
  document.querySelector(`[data-type="${type}"]`).classList.add('active');
}

function selectTool(tool) {
  selectedTool = tool;
  document.querySelectorAll('.tool-card[data-tool]').forEach(c => c.classList.remove('active'));
  document.querySelector(`[data-tool="${tool}"]`).classList.add('active');
}

// Video Generation — multi-select (use one or more); keep at least one
function toggleTool(el, tool) {
  const i = selectedTools.indexOf(tool);
  if (i >= 0) {
    if (selectedTools.length > 1) { selectedTools.splice(i, 1); el.classList.remove('active'); }
  } else {
    selectedTools.push(tool); el.classList.add('active');
  }
  selectedTool = selectedTools[0];   // primary tool for the pipeline payload
}

// Voice Generation — multi-select (use one or both); keep at least one
function toggleVoice(el, voice) {
  const i = selectedVoices.indexOf(voice);
  if (i >= 0) {
    if (selectedVoices.length > 1) { selectedVoices.splice(i, 1); el.classList.remove('active'); }
  } else {
    selectedVoices.push(voice); el.classList.add('active');
  }
}

// AI Brain — single-select
function selectBrain(el, brain) {
  selectedBrain = brain;
  document.querySelectorAll('.tool-card[data-brain]').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
}

function selectMode(mode) {
  selectedMode = mode;
  document.querySelectorAll('.approach-card').forEach(c => c.classList.remove('active'));
  document.querySelector(`[data-mode="${mode}"]`).classList.add('active');
}

function selectCharacter(el, id) {
  selectedCharacterId = id ? parseInt(id) : null;
  document.querySelectorAll('.char-card').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
}

// ─── WebSocket ──────────────────────────────────────────

function connectWebSocket() {
  ws = new WebSocket(`ws://${window.location.host}/ws/${clientId}`);
  ws.onmessage = handleMessage;
  ws.onclose = () => setTimeout(connectWebSocket, 2000);
}

function handleMessage(event) {
  const data = JSON.parse(event.data);
  if (data.type === 'result') {
    showResult(data);
    document.getElementById('generateBtn').disabled = false;
    return;
  }
  updateProgress(data);
}

// ─── Progress ───────────────────────────────────────────

const stepOrder = ['research', 'script', 'voice', 'video', 'editing', 'quality', 'done'];

function updateProgress(data) {
  const { step, message, percent } = data;
  document.getElementById('progressBar').style.width = percent + '%';
  document.getElementById('progressLabel').textContent = message;

  document.querySelectorAll('.agent-step').forEach(el => {
    const s = el.id.replace('step-', '');
    const statusEl = el.querySelector('.step-status');
    if (s === step) {
      el.classList.add('active');
      el.classList.remove('done');
      if (statusEl) statusEl.textContent = 'Working...';
    } else if (stepOrder.indexOf(s) < stepOrder.indexOf(step)) {
      el.classList.remove('active');
      el.classList.add('done');
      if (statusEl) statusEl.textContent = 'Done';
    }
  });

  if (step === 'error') {
    document.getElementById('errorSection').classList.remove('hidden');
    document.getElementById('errorMessage').textContent = message;
    document.getElementById('generateBtn').disabled = false;
  }
}

// ─── Show Result ────────────────────────────────────────

function showResult(data) {
  if (!data.success) {
    document.getElementById('errorSection').classList.remove('hidden');
    document.getElementById('errorMessage').textContent = data.error || 'Unknown error';
    return;
  }

  document.getElementById('resultSection').classList.remove('hidden');
  document.getElementById('errorSection').classList.add('hidden');

  currentVideoId = data.db_id || null;

  const score = data.quality_score || 0;
  const badge = document.getElementById('qualityBadge');
  badge.textContent = `Quality: ${score}/10`;
  badge.className = 'quality-badge ' + (score >= 6 ? 'good' : 'bad');

  const modeLabel = data.script_mode === 'rewrite' ? 'Rewrite' : 'New Angle';
  document.getElementById('approachBadge').textContent = modeLabel;

  const authScore = data.quality_report?.ugc_authenticity_score || 0;
  document.getElementById('authenticityBadge').textContent = `Authenticity: ${authScore}/10`;

  const charBadge = document.getElementById('charUsedBadge');
  if (data.character) {
    charBadge.textContent = `Character: ${data.character}`;
    charBadge.classList.remove('hidden');
  } else {
    charBadge.classList.add('hidden');
  }

  document.getElementById('previewVideo').src = `/output/videos/${data.job_id}/final_tiktok.mp4`;

  if (data.hook) {
    document.getElementById('hookBox').innerHTML = `<strong>HOOK</strong>${data.hook}`;
  }

  const tags = data.hashtags || [];
  document.getElementById('hashtagsBox').innerHTML = tags.map(t => `<span class="hashtag-pill">${t}</span>`).join('');

  document.getElementById('downloadBtn').onclick = () => {
    window.location.href = `/download/${data.job_id}`;
  };

  const qr = data.quality_report || {};
  document.getElementById('qualityReport').innerHTML = `
    <strong style="color:#aaa">Quality Report</strong><br>
    Hook Strength: ${qr.hook_strength || 'N/A'} &nbsp;|&nbsp;
    Tool: ${data.tool_used || 'N/A'}<br>
    ${qr.issues?.length ? 'Issues: ' + qr.issues.join(', ') : ''}
  `;

  document.getElementById('progressBar').style.width = '100%';
  document.getElementById('progressLabel').textContent = 'Video ready!';
  document.querySelectorAll('.agent-step').forEach(el => {
    el.classList.remove('active');
    el.classList.add('done');
    const s = el.querySelector('.step-status');
    if (s) s.textContent = 'Done';
  });

  loadHistory();
}

// ─── Generate ───────────────────────────────────────────

async function startGeneration() {
  const productName = document.getElementById('productName').value.trim();
  const productDesc = document.getElementById('productDesc').value.trim();
  const niche = document.getElementById('niche').value;
  updateBatchCount();

  if (!productName) {
    alert('Please enter a product name first.');
    return;
  }

  document.getElementById('generateBtn').disabled = true;
  document.getElementById('resultSection').classList.add('hidden');
  document.getElementById('errorSection').classList.add('hidden');

  document.querySelectorAll('.agent-step').forEach(el => {
    el.classList.remove('active', 'done');
    const s = el.querySelector('.step-status');
    if (s) s.textContent = 'Waiting...';
  });
  document.getElementById('progressBar').style.width = '0%';
  document.getElementById('progressLabel').textContent = 'Starting pipeline...';

  const scriptMode = selectedMode === 'auto' ? null : selectedMode;
  let manualScript = null;

  if (selectedScriptMode === 'manual') {
    manualScript = document.getElementById('scriptInput').value.trim();
    if (!manualScript) {
      alert('Please enter your script or select AI Write Mode.');
      document.getElementById('generateBtn').disabled = false;
      return;
    }
  }

  const payload = {
    topic: productName,
    niche,
    video_tool: selectedTool,
    video_tools: selectedTools,
    voice_tools: selectedVoices,
    ai_brain: selectedBrain,
    video_type: selectedVideoType,
    product_name: productName,
    product_description: productDesc,
    script_mode: scriptMode,
    character_id: selectedCharacterId,
    product_image: productImageBase64,
    manual_script: manualScript,
    batch_count: batchCount,
  };

  await fetch(`/generate/${clientId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
}

// ─── History ────────────────────────────────────────────

async function loadHistory() {
  const res = await fetch('/history');
  const data = await res.json();
  const list = document.getElementById('historyList');
  list.innerHTML = '';

  if (!data.videos?.length) {
    list.innerHTML = '<p style="color:#444;font-size:0.8rem">No videos generated yet.</p>';
    return;
  }

  data.videos.forEach(v => {
    const div = document.createElement('div');
    div.className = 'history-item';
    div.innerHTML = `
      <div class="h-topic">${v.topic}</div>
      <div class="h-meta">${v.niche} · ${v.date?.slice(0,10) || ''}${v.character ? ' · ' + v.character : ''}</div>
      <div class="h-badges">
        <span class="h-badge">${v.tool}</span>
        <span class="h-badge">Score: ${v.score?.toFixed(0) || '0'}</span>
      </div>
    `;
    list.appendChild(div);
  });
}

// ─── Feedback ───────────────────────────────────────────

async function submitFeedback() {
  const views = parseInt(document.getElementById('fbViews').value) || 0;
  const likes = parseInt(document.getElementById('fbLikes').value) || 0;
  const sales = parseInt(document.getElementById('fbSales').value) || 0;

  if (!currentVideoId) { alert('No video selected.'); return; }

  await fetch(`/performance/${currentVideoId}?views=${views}&likes=${likes}&shares=${sales}`, {
    method: 'POST'
  });

  document.querySelector('.feedback-btn').textContent = 'Saved! Agents updated.';
  setTimeout(() => document.querySelector('.feedback-btn').textContent = 'Update Performance', 2000);
}

// ─── Character Modal ────────────────────────────────────

async function openCharacterModal() {
  document.getElementById('characterModal').classList.remove('hidden');
  await loadModalCharacters();
}

function closeCharacterModal(e) {
  if (!e || e.target === document.getElementById('characterModal')) {
    document.getElementById('characterModal').classList.add('hidden');
  }
}

async function loadModalCharacters() {
  const res = await fetch('/characters');
  const data = await res.json();
  const list = document.getElementById('modalCharacterList');

  if (!data.characters?.length) {
    list.innerHTML = '<p style="color:#555;font-size:0.8rem">No characters saved yet. Create one above.</p>';
    return;
  }

  list.innerHTML = data.characters.map(c => `
    <div class="modal-char-item">
      <div class="modal-char-img">
        ${c.image_path ? `<img src="/assets/characters/${c.image_path.split(/[\\/]/).pop()}" />` : '<div class="char-initials">' + c.name[0] + '</div>'}
      </div>
      <div class="modal-char-info">
        <div class="modal-char-name">${c.name}</div>
        <div class="modal-char-sub">${c.appearance || ''}</div>
        <div class="modal-char-stats">${c.videos_created} videos · Avg score ${(c.avg_performance || 0).toFixed(0)}</div>
      </div>
      <button class="modal-char-delete" onclick="deleteCharacter(${c.id})">✕</button>
    </div>
  `).join('');
}

async function previewCharImage(input) {
  if (!input.files?.length) return;
  const file = input.files[0];
  const reader = new FileReader();
  reader.onload = e => {
    document.getElementById('charImagePreview').innerHTML = `<img src="${e.target.result}" style="max-height:80px;border-radius:8px;" />`;
  };
  reader.readAsDataURL(file);
}

async function createCharacter() {
  const name = document.getElementById('charName').value.trim();
  if (!name) { alert('Please enter a character name.'); return; }

  const form = new FormData();
  form.append('name', name);
  form.append('appearance', document.getElementById('charAppearance').value.trim());
  form.append('personality', document.getElementById('charPersonality').value.trim());
  form.append('description', document.getElementById('charDescription').value.trim());
  form.append('niche', document.getElementById('charNiche').value);
  form.append('voice_gender', document.getElementById('charVoiceGender').value);

  const imageInput = document.getElementById('charImageInput');
  if (imageInput.files?.length) {
    form.append('image', imageInput.files[0]);
  }

  const res = await fetch('/characters', { method: 'POST', body: form });
  const data = await res.json();

  if (data.status === 'created') {
    document.getElementById('charName').value = '';
    document.getElementById('charAppearance').value = '';
    document.getElementById('charPersonality').value = '';
    document.getElementById('charDescription').value = '';
    document.getElementById('charImagePreview').innerHTML = '📷 Reference Image (Optional)<br><small>Upload an image to use the same character across all scenes (image-to-video)</small>';
    imageInput.value = '';

    await loadModalCharacters();
    await refreshCharacterPicker();
  }
}

async function deleteCharacter(id) {
  if (!confirm('Delete this character?')) return;
  await fetch(`/characters/${id}`, { method: 'DELETE' });
  await loadModalCharacters();
  await refreshCharacterPicker();
}

async function refreshCharacterPicker() {
  const res = await fetch('/characters');
  const data = await res.json();
  const picker = document.getElementById('characterPicker');

  const noChar = picker.querySelector('.no-char');
  picker.innerHTML = '';
  picker.appendChild(noChar);

  data.characters.forEach(c => {
    const card = document.createElement('div');
    card.className = 'char-card';
    card.dataset.id = c.id;
    card.onclick = () => selectCharacter(card, c.id);

    const img = c.image_path
      ? `<img src="/assets/characters/${c.image_path.split(/[\\/]/).pop()}" class="char-avatar-img" />`
      : `<div class="char-avatar">${c.name[0]}</div>`;

    card.innerHTML = `
      ${img}
      <div class="char-name">${c.name}</div>
      <div class="char-desc">${c.niche}</div>
    `;
    picker.appendChild(card);
  });
}

// ─── Init ───────────────────────────────────────────────

connectWebSocket();
loadHistory();
refreshCharacterPicker();
