const fetchForm = document.getElementById('fetchForm');
const pinUrlInput = document.getElementById('pinUrl');
const pasteBtn = document.getElementById('pasteBtn');
const submitBtn = document.getElementById('submitBtn');

// PRO VAULT UI IDs
const resultVault = document.getElementById('resultVault');
const resBadge = document.getElementById('resBadge');
const mediaViewport = document.getElementById('mediaViewport');
const mediaHeading = document.getElementById('mediaHeading');
const mediaSubinfo = document.getElementById('mediaSubinfo');
const btnDirectDownload = document.getElementById('btnDirectDownload');
const dlBtnText = document.getElementById('dlBtnText');
const btnCopyDirect = document.getElementById('btnCopyDirect');

const historyWrap = document.getElementById('historyWrap');
const historyItems = document.getElementById('historyItems');
const clearVaultBtn = document.getElementById('clearVaultBtn');

let forceDownloadLink = ''; // Isme proxy link save hoga share karne ke liye

function toast(msg) {
  const t = document.getElementById('toast');
  if (!t) return;
  document.getElementById('toastMsg').textContent = msg;
  t.classList.add('show');
  clearTimeout(t._h);
  t._h = setTimeout(() => t.classList.remove('show'), 2400);
}

// 1. SMART CLIPBOARD PASTE
pasteBtn.addEventListener('click', async () => {
  try {
    if (navigator.clipboard && navigator.clipboard.readText) {
      const text = await navigator.clipboard.readText();
      if (text) {
        pinUrlInput.value = text.trim();
        toast('Link pasted from clipboard');
        return;
      }
    }
  } catch (_) {}
  pinUrlInput.focus();
  toast('Paste permission required / Paste manually');
});

// 2. FETCH FROM API
fetchForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const rawUrl = pinUrlInput.value.trim();
  if (!rawUrl) return;

  submitBtn.disabled = true;
  submitBtn.textContent = '⚡ EXTRACTING...';
  toast('Isolating Media Pipeline...');

  try {
    const res = await fetch(`/api/fetch?url=${encodeURIComponent(rawUrl)}`);
    const data = await res.json();

    if (!res.ok || data.status !== 'success') {
      throw new Error(data.message || 'Unable to extract pin');
    }

    renderResult(data);
    persistVault(data);
    toast('Master Stream Unlocked!');
  } catch (err) {
    toast(`Error: ${err.message}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = '⚡ EXTRACT';
  }
});

// 3. RENDER PREVIEW & LINKS
function renderResult(data) {
  // Pura Absolute link banaya jo share karne par browser block bypass karke auto-download trigger karega
  forceDownloadLink = window.location.origin + data.proxy_download;
  
  if (mediaHeading) mediaHeading.textContent = data.title;
  if (mediaSubinfo) mediaSubinfo.textContent = data.type === 'video' ? 'Direct Pipeline Stream · MP4 Video' : 'Direct Pipeline Stream · 4K Image';

  if (data.type === 'video') {
    if (resBadge) resBadge.textContent = '1080P MASTER VIDEO';
    // Direct Pinterest Original URL for instant Video Playback
    if (mediaViewport) mediaViewport.innerHTML = `<video controls autoplay loop playsinline src="${data.url}" style="max-width: 100%; max-height: 480px;"></video>`;
    if (dlBtnText) dlBtnText.textContent = '⬇ DOWNLOAD MP4';
  } else {
    if (resBadge) resBadge.textContent = '4K ORIGINAL IMAGE';
    // Direct Pinterest Original URL for Image View
    if (mediaViewport) mediaViewport.innerHTML = `<img src="${data.url}" alt="Pin Media" loading="lazy" style="max-width: 100%; max-height: 480px;">`;
    if (dlBtnText) dlBtnText.textContent = '⬇ DOWNLOAD 4K JPG';
  }

  // 1-Click download using the backend proxy file attachment headers
  if (btnDirectDownload) btnDirectDownload.href = data.proxy_download;
  
  if (resultVault) {
    resultVault.style.display = 'block';
    resultVault.scrollIntoView({ behavior: 'smooth' });
  }
}

// 4. COPY AUTO-DOWNLOAD LINK (For sharing)
if (btnCopyDirect) {
  btnCopyDirect.addEventListener('click', () => {
    if (!forceDownloadLink) return;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(forceDownloadLink);
      toast('Force-Download Link Copied!');
    } else {
      const temp = document.createElement('input');
      temp.value = forceDownloadLink;
      document.body.appendChild(temp);
      temp.select();
      document.execCommand('copy');
      document.body.removeChild(temp);
      toast('Force-Download Link Copied!');
    }
  });
}

// 5. LOCAL HISTORY VAULT
function fetchVault() {
  try { return JSON.parse(localStorage.getItem('og_vault_pro')) || []; }
  catch (e) { return []; }
}

function persistVault(item) {
  let list = fetchVault();
  list = list.filter(i => i.url !== item.url);
  list.unshift(item);
  if (list.length > 6) list.pop(); // Max 6 items
  localStorage.setItem('og_vault_pro', JSON.stringify(list));
  renderVault();
}

function renderVault() {
  const list = fetchVault();
  if (!list.length) {
    if (historyWrap) historyWrap.style.display = 'none';
    return;
  }

  if (historyItems) {
    historyItems.innerHTML = list.map(item => `
      <div class="history-card" onclick='restoreVaultItem(${JSON.stringify(item)})'>
        <img class="history-thumb" src="${item.url}" alt="Vault Item" loading="lazy">
        <div class="history-name">${item.title}</div>
      </div>
    `).join('');
  }

  if (historyWrap) historyWrap.style.display = 'block';
}

// Global function window ke liye taaki onclick element usko dhundh sake
window.restoreVaultItem = function(item) {
  renderResult(item);
};

if (clearVaultBtn) {
  clearVaultBtn.addEventListener('click', () => {
    localStorage.removeItem('og_vault_pro');
    renderVault();
    toast('Vault History Cleared');
  });
}

// Initial Load
renderVault();
