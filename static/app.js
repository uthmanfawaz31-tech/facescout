// StreamScout Dashboard Application State
let appState = {
  leads: [],
  keywords: [],
  isActive: false,
  pollTimer: null,
  currentTab: 'auto'
};

// Initialization
document.addEventListener('DOMContentLoaded', () => {
  fetchKeywords();
  fetchStatus();
  setInterval(fetchStatus, 3000);
});

// Tab Switching
function switchTab(tabName) {
  appState.currentTab = tabName;
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('active', 'border-blue-500', 'text-white', 'font-semibold');
    btn.classList.add('border-transparent', 'text-gray-400');
  });
  document.querySelectorAll('.tab-content').forEach(sec => sec.classList.add('hidden'));

  const activeBtn = document.getElementById(`tab-btn-${tabName}`);
  const activeContent = document.getElementById(`tab-content-${tabName}`);

  if (activeBtn && activeContent) {
    activeBtn.classList.add('active', 'border-blue-500', 'text-white', 'font-semibold');
    activeBtn.classList.remove('border-transparent', 'text-gray-400');
    activeContent.classList.remove('hidden');
  }
}

// Fetch Keywords
async function fetchKeywords() {
  try {
    const res = await fetch('/api/keywords');
    const data = await res.json();
    appState.keywords = data.keywords || [];
    renderKeywords();
  } catch (err) {
    console.error('Error fetching keywords:', err);
  }
}

function renderKeywords() {
  const container = document.getElementById('keywords-container');
  const countEl = document.getElementById('kw-count');
  if (countEl) countEl.innerText = appState.keywords.length;
  if (!container) return;

  container.innerHTML = appState.keywords.map((kw, i) => `
    <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs bg-gray-800 text-gray-200 border border-gray-700">
      ${escapeHtml(kw)}
      <button onclick="removeKeyword(${i})" class="text-gray-500 hover:text-red-400 ml-1">
        <i class="fa-solid fa-xmark text-[10px]"></i>
      </button>
    </span>
  `).join('');
}

function addKeyword() {
  const input = document.getElementById('new-keyword-input');
  const val = input.value.trim().toLowerCase();
  if (val && !appState.keywords.includes(val)) {
    appState.keywords.push(val);
    input.value = '';
    renderKeywords();
  }
}

function removeKeyword(index) {
  appState.keywords.splice(index, 1);
  renderKeywords();
}

async function saveKeywords() {
  try {
    const res = await fetch('/api/keywords', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keywords: appState.keywords })
    });
    if (res.ok) {
      alert('Keywords saved successfully!');
    }
  } catch (err) {
    alert('Failed to save keywords');
  }
}

// Status & Lead Polling
async function fetchStatus() {
  try {
    const res = await fetch('/api/scout/status');
    const data = await res.json();

    appState.isActive = data.is_active;
    appState.leads = data.leads || [];

    // Update UI Indicators
    const statusText = document.getElementById('status-text');
    const statusDot = document.getElementById('status-dot');
    const statTotalLeads = document.getElementById('stat-total-leads');
    const btnStart = document.getElementById('btn-start-scout');
    const btnStop = document.getElementById('btn-stop-scout');

    if (statTotalLeads) statTotalLeads.innerText = appState.leads.length;

    if (appState.isActive) {
      statusText.innerText = 'Scanning...';
      statusText.className = 'font-semibold text-blue-400';
      statusDot.className = 'w-2.5 h-2.5 rounded-full bg-blue-500 animate-ping';
      if (btnStart) btnStart.classList.add('hidden');
      if (btnStop) btnStop.classList.remove('hidden');
    } else {
      statusText.innerText = data.current_action || 'Idle';
      statusText.className = 'font-semibold text-gray-300';
      statusDot.className = 'w-2.5 h-2.5 rounded-full bg-emerald-500';
      if (btnStart) btnStart.classList.remove('hidden');
      if (btnStop) btnStop.classList.add('hidden');
    }

    // Render Logs
    const logBox = document.getElementById('console-logs');
    const logCount = document.getElementById('log-count');
    if (logBox && data.logs) {
      logBox.innerHTML = data.logs.map(l => `<div>${escapeHtml(l)}</div>`).join('');
      logBox.scrollTop = logBox.scrollHeight;
      if (logCount) logCount.innerText = `${data.logs.length} messages`;
    }

    renderLeads();
  } catch (err) {
    console.error('Error fetching status:', err);
  }
}

// Start Scouting
async function startScouting() {
  const groupUrl = document.getElementById('auto-group-url').value.trim();
  if (!groupUrl) {
    alert('Please enter a Facebook Group link!');
    return;
  }

  const maxPosts = parseInt(document.getElementById('auto-max-posts').value) || 30;
  const deepBio = document.getElementById('auto-deep-bio').checked;
  const headless = document.getElementById('auto-headless').checked;

  try {
    const res = await fetch('/api/scout/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        group_url: groupUrl,
        keywords: appState.keywords,
        max_posts: maxPosts,
        scan_comments: true,
        deep_profile_scan: deepBio,
        headless: headless
      })
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.detail || 'Failed to start scouting');
    } else {
      fetchStatus();
    }
  } catch (err) {
    alert('Failed to connect to backend.');
  }
}

// Stop Scouting
async function stopScouting() {
  await fetch('/api/scout/stop', { method: 'POST' });
  fetchStatus();
}

// Launch Visible Browser to Login to FB
async function openLoginBrowser() {
  try {
    const res = await fetch('/api/browser/login', { method: 'POST' });
    const data = await res.json();
    alert('Visible Chrome launched! Please log in to Facebook in that window. Once logged in, your session is saved permanently.');
    fetchStatus();
  } catch (err) {
    alert('Error launching browser.');
  }
}

// Generate In-Group Search Links
async function generateSearchLinks() {
  const groupUrl = document.getElementById('links-group-url').value.trim();
  if (!groupUrl) {
    alert('Please enter a Facebook Group URL.');
    return;
  }

  const container = document.getElementById('search-links-container');
  container.innerHTML = `<div class="col-span-full text-xs text-blue-400">Generating stealth links...</div>`;

  try {
    const res = await fetch('/api/scout/generate-search-links', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ group_url: groupUrl })
    });
    const data = await res.json();

    if (!res.ok) {
      container.innerHTML = `<div class="col-span-full text-xs text-red-400">${data.detail}</div>`;
      return;
    }

    container.innerHTML = data.links.map(item => `
      <a href="${item.url}" target="_blank" class="flex items-center justify-between p-3 rounded-xl bg-gray-900 hover:bg-gray-800 border border-gray-800 hover:border-indigo-500/50 transition group">
        <div class="flex items-center space-x-2">
          <i class="fa-solid fa-magnifying-glass text-indigo-400 text-xs"></i>
          <span class="text-xs font-medium text-gray-200">Search "<b>${escapeHtml(item.keyword)}</b>"</span>
        </div>
        <i class="fa-solid fa-arrow-up-right-from-square text-xs text-gray-500 group-hover:text-indigo-400 transition"></i>
      </a>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div class="col-span-full text-xs text-red-400">Failed to generate links.</div>`;
  }
}

// Instant Paste Content
async function submitPastedContent() {
  const text = document.getElementById('paste-input').value.trim();
  if (!text) {
    alert('Please paste some Facebook post or comment text first.');
    return;
  }

  try {
    const res = await fetch('/api/scout/paste', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text_or_html: text })
    });
    const data = await res.json();

    if (res.ok) {
      alert(`Success! Extracted ${data.leads_found} lead(s). Check the results below.`);
      fetchStatus();
      document.getElementById('paste-input').value = '';
    } else {
      alert('Error parsing content.');
    }
  } catch (err) {
    alert('Server communication error.');
  }
}

// Telegram Bot Connect
async function connectTelegramBot() {
  const token = document.getElementById('tg-bot-token').value.trim();
  if (!token) {
    alert('Please enter your Telegram Bot Token.');
    return;
  }

  try {
    const res = await fetch('/api/telegram/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bot_token: token })
    });
    const data = await res.json();
    alert(data.message || 'Telegram Bot connected!');
    fetchStatus();
  } catch (err) {
    alert('Failed to connect Telegram Bot.');
  }
}

async function disconnectTelegramBot() {
  try {
    const res = await fetch('/api/telegram/stop', { method: 'POST' });
    const data = await res.json();
    alert(data.message || 'Telegram Bot disconnected.');
    fetchStatus();
  } catch (err) {
    alert('Failed to stop Telegram Bot.');
  }
}

// Clear Leads
async function clearAllLeads() {
  if (confirm('Are you sure you want to clear all leads from this session?')) {
    await fetch('/api/leads/clear', { method: 'POST' });
    fetchStatus();
  }
}

// Render Leads Grid
function renderLeads() {
  const container = document.getElementById('leads-container');
  const countEl = document.getElementById('filtered-lead-count');
  if (!container) return;

  const intentFilter = document.getElementById('filter-intent')?.value || 'ALL';
  const contactFilter = document.getElementById('filter-contact')?.value || 'ALL';
  const searchQuery = (document.getElementById('lead-search-query')?.value || '').toLowerCase();

  let filtered = appState.leads.filter(lead => {
    // Intent filter
    if (intentFilter !== 'ALL' && lead.intent !== intentFilter) return false;

    // Contact filter
    if (contactFilter === 'HAS_WHATSAPP' && (!lead.contacts.whatsapp || lead.contacts.whatsapp.length === 0)) return false;
    if (contactFilter === 'HAS_TELEGRAM' && (!lead.contacts.telegram || lead.contacts.telegram.length === 0)) return false;
    if (contactFilter === 'HAS_ANY' && (!lead.contacts.whatsapp?.length && !lead.contacts.telegram?.length && !lead.contacts.discord?.length)) return false;

    // Search query
    if (searchQuery) {
      const matchName = lead.author_name.toLowerCase().includes(searchQuery);
      const matchText = lead.raw_text.toLowerCase().includes(searchQuery);
      const matchWa = lead.contacts.whatsapp?.some(w => w.includes(searchQuery));
      const matchTg = lead.contacts.telegram?.some(t => t.toLowerCase().includes(searchQuery));
      return matchName || matchText || matchWa || matchTg;
    }
    return true;
  });

  if (countEl) countEl.innerText = filtered.length;

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="col-span-full card-glass rounded-2xl p-12 text-center text-gray-500 space-y-2">
        <i class="fa-solid fa-filter text-2xl text-gray-600 mb-2"></i>
        <p class="text-sm font-medium">No leads match the current filters</p>
        <p class="text-xs text-gray-500">Try switching filters to 'All' or start a new group scan.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(lead => {
    // Intent Badge
    let badgeClass = "bg-gray-800 text-gray-300 border-gray-700";
    let badgeLabel = lead.intent;
    let badgeIcon = "fa-comment-dots";

    if (lead.intent === "REQUESTING") {
      badgeClass = "bg-rose-500/20 text-rose-300 border-rose-500/30";
      badgeLabel = "🔥 HOT LEAD (Asking for Service)";
      badgeIcon = "fa-fire";
    } else if (lead.intent === "SELLER") {
      badgeClass = "bg-amber-500/20 text-amber-300 border-amber-500/30";
      badgeLabel = "📢 Competitor / Seller";
      badgeIcon = "fa-bullhorn";
    }

    // Direct Contact Buttons
    const waButtons = (lead.contacts.whatsapp_links || []).map((link, idx) => `
      <a href="${link}" target="_blank" class="px-2.5 py-1 rounded-lg bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300 border border-emerald-500/30 text-xs font-medium flex items-center gap-1 transition">
        <i class="fa-brands fa-whatsapp text-emerald-400"></i> ${lead.contacts.whatsapp[idx] || 'WhatsApp'}
      </a>
    `).join('');

    const tgButtons = (lead.contacts.telegram_links || []).map((link, idx) => `
      <a href="${link}" target="_blank" class="px-2.5 py-1 rounded-lg bg-sky-600/30 hover:bg-sky-600/50 text-sky-300 border border-sky-500/30 text-xs font-medium flex items-center gap-1 transition">
        <i class="fa-brands fa-telegram text-sky-400"></i> @${lead.contacts.telegram[idx] || 'Telegram'}
      </a>
    `).join('');

    const dcBadges = (lead.contacts.discord || []).map(tag => `
      <span class="px-2.5 py-1 rounded-lg bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-medium flex items-center gap-1">
        <i class="fa-brands fa-discord text-indigo-400"></i> ${escapeHtml(tag)}
      </span>
    `).join('');

    const kwChips = (lead.matched_keywords || []).map(kw => `
      <span class="tag-badge text-[10px] px-2 py-0.5 rounded">${escapeHtml(kw)}</span>
    `).join('');

    const fbProfileLink = lead.author_profile_url ? `
      <a href="${lead.author_profile_url}" target="_blank" class="text-xs text-blue-400 hover:underline flex items-center gap-1">
        <i class="fa-brands fa-facebook"></i> View FB Profile
      </a>
    ` : '';

    return `
      <div class="card-glass rounded-2xl p-5 flex flex-col justify-between space-y-4 border border-gray-800 hover:border-gray-700 transition">
        <div class="space-y-3">
          <!-- Card Header -->
          <div class="flex items-start justify-between gap-2">
            <div>
              <span class="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${badgeClass}">
                <i class="fa-solid ${badgeIcon} text-[9px]"></i> ${badgeLabel}
              </span>
              <h4 class="text-sm font-bold text-white mt-1.5">${escapeHtml(lead.author_name)}</h4>
            </div>
            ${fbProfileLink}
          </div>

          <!-- Keywords -->
          <div class="flex flex-wrap gap-1">
            ${kwChips}
          </div>

          <!-- Raw Snippet -->
          <p class="text-xs text-gray-300 bg-gray-900/90 rounded-xl p-3 border border-gray-800/80 font-sans line-clamp-4">
            "${escapeHtml(lead.raw_text)}"
          </p>
        </div>

        <!-- Contact Section & Actions -->
        <div class="space-y-3 pt-2 border-t border-gray-800/80">
          <div class="space-y-1.5">
            <span class="text-[10px] font-medium text-gray-500 uppercase tracking-wider">Direct Outreach Channels:</span>
            <div class="flex flex-wrap gap-1.5">
              ${waButtons || ''}
              ${tgButtons || ''}
              ${dcBadges || ''}
              ${(!waButtons && !tgButtons && !dcBadges) ? '<span class="text-xs text-gray-500 italic">No external contact posted in text</span>' : ''}
            </div>
          </div>

          <!-- Outreach Button -->
          <button onclick="openOutreachModal('${escapeHtml(lead.author_name)}', '${lead.matched_keywords?.[0] || 'firestick'}', '${lead.contacts.whatsapp_links?.[0] || ''}', '${lead.contacts.telegram_links?.[0] || ''}')" class="w-full py-2 px-3 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-semibold flex items-center justify-center gap-1.5 border border-gray-700 transition">
            <i class="fa-solid fa-comment-medical text-blue-400"></i> Generate Outreach Pitch
          </button>
        </div>
      </div>
    `;
  }).join('');
}

// Outreach Modal Helpers
function openOutreachModal(authorName, keyword, waLink, tgLink) {
  const modal = document.getElementById('outreach-modal');
  const nameEl = document.getElementById('outreach-lead-name');
  const msgEl = document.getElementById('outreach-message');
  const waBtn = document.getElementById('outreach-wa-btn');
  const tgBtn = document.getElementById('outreach-tg-btn');

  nameEl.innerText = authorName;

  const pitch = `Hi ${authorName}! Saw your post in the Facebook group regarding ${keyword}. If you're still looking for a smooth, buffer-free service for live sports, UK/US channels with reliable m3u or xtream codes, I can hook you up with a quick test line. Let me know what app/device you're using!`;
  msgEl.value = pitch;

  if (waLink) {
    waBtn.classList.remove('hidden');
    waBtn.href = `${waLink}?text=${encodeURIComponent(pitch)}`;
  } else {
    waBtn.classList.add('hidden');
  }

  if (tgLink) {
    tgBtn.classList.remove('hidden');
    tgBtn.href = tgLink;
  } else {
    tgBtn.classList.add('hidden');
  }

  modal.classList.remove('hidden');
}

function closeOutreachModal() {
  document.getElementById('outreach-modal').classList.add('hidden');
}

function copyOutreachText() {
  const msg = document.getElementById('outreach-message').value;
  navigator.clipboard.writeText(msg);
  alert('Outreach pitch copied to clipboard!');
}

function pasteToInput(inputId) {
  navigator.clipboard.readText().then(text => {
    document.getElementById(inputId).value = text;
  });
}

function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
