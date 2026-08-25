const fetchForm = document.getElementById('fetchForm');
const pinUrlInput = document.getElementById('pinUrl');
const pasteBtn = document.getElementById('pasteBtn');
const submitBtn = document.getElementById('submitBtn');

// Aapke HTML ke exact IDs match kar diye gaye hain
const previewBlock = document.getElementById('previewBlock');
const mediaTypeTag = document.getElementById('mediaTypeTag');
const mediaWrapper = document.getElementById('mediaWrapper');
const previewTitle = document.getElementById('previewTitle');
const previewMeta = document.getElementById('previewMeta');
const btnPrimaryDl = document.getElementById('btnPrimaryDl');
const btnPrimaryText = document.getElementById('btnPrimaryText');
const btnPrimarySub = document.getElementById('btnPrimarySub');
const btnCopyLink = document.getElementById('btnCopyLink');

const historySection = document.getElementById('historySection');
const historyGrid = document.getElementById('historyGrid');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');

// Isme wo link save hoga jo share karne par direct download force karega
let forceDownloadLink = ''; 

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
    submitBtn.textContent = '⚡ FETCH';
  }
});

// 3. RENDER PREVIEW & LINKS
function renderResult(data) {
  // Pura Absolute link banaya jo share karne par browser me play hone ke bajaye direct download hoga
  forceDownloadLink = window.location.origin + data.proxy_download;
  
  if (previewTitle) previewTitle.textContent = data.title;
  if (previewMeta) previewMeta.textContent = data.type === 'video' ? 'Direct Pipeline Stream · MP4 Video' : 'Direct Pipeline Stream · 4K Image';

  if (data.type === 'video') {
    if (mediaTypeTag) mediaTypeTag.textContent = 'VIDEO · 1080P MASTER';
    // Preview ke liye Original URL taaki buffer na ho aur instant play ho
    if (mediaWrapper) mediaWrapper.innerHTML = `<video controls autoplay loop playsinline src="${data.url}" style="max-width: 100%; max-height: 480px;"></video>`;
    if (btnPrimaryText) btnPrimaryText.textContent = '⬇ DOWNLOAD MP4';
    if (btnPrimarySub) btnPrimarySub.textContent = 'Master Quality Video';
  } else {
    if (mediaTypeTag) mediaTypeTag.textContent = 'IMAGE · 4K ORIGINAL';
    // Preview ke liye Original URL
    if (mediaWrapper) mediaWrapper.innerHTML = `<img src="${data.url}" alt="Pin Media" loading="lazy" style="max-width: 100%; max-height: 480px;">`;
    if (btnPrimaryText) btnPrimaryText.textContent = '⬇ DOWNLOAD 4K JPG';
    if (btnPrimarySub) btnPrimarySub.textContent = 'Original Raw Image';
  }

  // 1-Click download using the backend proxy file attachment headers
  if (btnPrimaryDl) btnPrimaryDl.href = data.proxy_download;
  
  if (previewBlock) {
    previewBlock.style.display = 'block';
    previewBlock.scrollIntoView({ behavior: 'smooth' });
  }
}

// 4. COPY AUTO-DOWNLOAD LINK (For sharing)
if (btnCopyLink) {
  btnCopyLink.addEventListener('click', () => {
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
  if (list.length > 6) list.pop(); 
  localStorage.setItem('og_vault_pro', JSON.stringify(list));
  renderVault();
}

function renderVault() {
  const list = fetchVault();
  if (!list.length) {
    if (historySection) historySection.style.display = 'none';
    return;
  }

  if (historyGrid) {
    historyGrid.innerHTML = list.map(item => `
      <div class="history-card" onclick='restoreVaultItem(${JSON.stringify(item)})'>
        <img class="history-thumb" src="${item.url}" alt="Vault Item" loading="lazy">
        <div class="history-title">${item.title}</div>
      </div>
    `).join('');
  }

  if (historySection) historySection.style.display = 'block';
}

// Global function window ke liye taaki onclick element usko dhundh sake
window.restoreVaultItem = function(item) {
  renderResult(item);
};

if (clearHistoryBtn) {
  clearHistoryBtn.addEventListener('click', () => {
    localStorage.removeItem('og_vault_pro');
    renderVault();
    toast('Vault History Cleared');
  });
}

// Initial Load
renderVault();
