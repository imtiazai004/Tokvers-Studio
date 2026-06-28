const CLIENT_KEYS = [
  'anthropic_api_key',
  'openai_api_key',
  'elevenlabs_api_key',
  'elevenlabs_voice_id_female',
  'elevenlabs_voice_id_male',
  'fish_audio_api_key',
  'grok_api_key',
  'google_ai_studio_api_key',
  'higgsfield_api_key',
  'apify_api_token',
  'brave_search_api_key',
  'deepgram_api_key',
];

async function loadSettings() {
  const res = await fetch('/settings');
  const data = await res.json();

  CLIENT_KEYS.forEach(key => {
    const input = document.getElementById(key);
    const statusEl = document.getElementById('status_' + key);
    if (!input) return;

    // /settings returns { set: bool, value: masked } per key
    const entry = data[key] || {};
    const isSet = entry.set || (typeof entry === 'string' && entry);
    // never echo secrets back into the field — show a ✓ if configured,
    // leave the input empty (placeholder) so typing only updates it
    input.value = '';
    if (statusEl) {
      statusEl.textContent = isSet ? '✓ Configured' : '';
      statusEl.style.color = '#48bb78';
    }
  });
}

async function saveSettings() {
  const data = {};

  CLIENT_KEYS.forEach(key => {
    const input = document.getElementById(key);
    if (input) data[key] = input.value;
  });

  const res = await fetch('/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });

  if (res.ok) {
    const msg = document.getElementById('saveMsg');
    msg.classList.remove('hidden');
    setTimeout(() => msg.classList.add('hidden'), 2500);
    CLIENT_KEYS.forEach(key => {
      const input = document.getElementById(key);
      if (input) input.value = '';
    });
    await loadSettings();
  }
}

// Submit Video Performance Data
async function submitVideoPerformance() {
  const title = document.getElementById('videoTitle').value.trim();
  const views = parseInt(document.getElementById('videoViews').value) || 0;
  const likes = parseInt(document.getElementById('videoLikes').value) || 0;
  const comments = parseInt(document.getElementById('videoComments').value) || 0;
  const shares = parseInt(document.getElementById('videoShares').value) || 0;

  const resultEl = document.getElementById('videoSubmitResult');
  const btn = event.target;

  if (!title) {
    resultEl.innerHTML = '❌ Please enter a video title';
    resultEl.style.color = '#fc8181';
    return;
  }

  if (views === 0) {
    resultEl.innerHTML = '❌ Please enter at least the view count';
    resultEl.style.color = '#fc8181';
    return;
  }

  btn.disabled = true;
  btn.textContent = '⏳ Saving...';
  resultEl.innerHTML = '';

  try {
    const res = await fetch('/performance/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title,
        views,
        likes,
        comments,
        shares
      })
    });

    const data = await res.json();

    if (data.success) {
      resultEl.innerHTML = `✅ Video tracked! Engagement: ${data.engagement_rate}%`;
      resultEl.style.color = '#9ae6b4';

      // Clear form
      document.getElementById('videoTitle').value = '';
      document.getElementById('videoViews').value = '';
      document.getElementById('videoLikes').value = '';
      document.getElementById('videoComments').value = '';
      document.getElementById('videoShares').value = '';

      // Show celebration for a bit
      setTimeout(() => {
        resultEl.innerHTML = '📈 System learning from your video! Keep uploading and tracking for better results.';
        resultEl.style.color = '#63b3ed';
      }, 2000);
    } else {
      resultEl.innerHTML = '❌ ' + (data.error || 'Failed to save');
      resultEl.style.color = '#fc8181';
    }
  } catch (error) {
    resultEl.innerHTML = '❌ Error: ' + error.message;
    resultEl.style.color = '#fc8181';
  }

  btn.disabled = false;
  btn.textContent = '✅ Save Video Performance';
}

loadSettings();
