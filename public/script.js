const fetchForm = document.getElementById('fetchForm');
const pinUrlInput = document.getElementById('pinUrl');
const pasteBtn = document.getElementById('pasteBtn');
const submitBtn = document.getElementById('submitBtn');

const resultVault = document.getElementById('resultVault');
const mediaViewport = document.getElementById('mediaViewport');
const resBadge = document.getElementById('resBadge');
const mediaHeading = document.getElementById('mediaHeading');
const btnDirectDownload = document.getElementById('btnDirectDownload');
const dlBtnText = document.getElementById('dlBtnText');
const btnCopyDirect = document.getElementById('btnCopyDirect');

const historyWrap = document.getElementById('historyWrap');
const historyItems = document.getElementById('historyItems');
const clearVaultBtn = document.getElementById('clearVaultBtn');

let activeDownloadLink = '';

function toast(msg) {
  const t = document.getElementById('toast');
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
  activeDownloadLink = data.url; 
  mediaHeading.textContent = data.title;

  if (data.type === 'video') {
    resBadge.textContent = '1080P MASTER VIDEO';
    mediaViewport.innerHTML = `<video controls autoplay loop playsinline src="${data.url}"></video>`;
    dlBtnText.textContent = '⬇ DOWNLOAD MP4';
  } else {
    resBadge.textContent = '4K ORIGINAL IMAGE';
    mediaViewport.innerHTML = `<img src="${data.url}" alt="Pin Media" loading="lazy">`;
    dlBtnText.textContent = '⬇ DOWNLOAD 4K JPG';
  }

  btnDirectDownload.href = data.proxy_download;
  
  resultVault.style.display = 'block';
  resultVault.scrollIntoView({ behavior: 'smooth' });
}

// 4. COPY ORIGINAL LINK
btnCopyDirect.addEventListener('click', () => {
  if (!activeDownloadLink) return;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(activeDownloadLink);
    toast('Direct CDN Link Copied!');
  } else {
    const temp = document.createElement('input');
    temp.value = activeDownloadLink;
    document.body.appendChild(temp);
    temp.select();
    document.execCommand('copy');
    document.body.removeChild(temp);
    toast('Direct CDN Link Copied!');
  }
});

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
    historyWrap.style.display = 'none';
    return;
  }

  historyItems.innerHTML = list.map(item => `
    <div class="history-card" onclick='restoreVaultItem(${JSON.stringify(item)})'>
      <img class="history-thumb" src="${item.url}" alt="Vault Item" loading="lazy">
      <div class="history-name">${item.title}</div>
    </div>
  `).join('');

  historyWrap.style.display = 'block';
}

window.restoreVaultItem = function(item) {
  renderResult(item);
};

clearVaultBtn.addEventListener('click', () => {
  localStorage.removeItem('og_vault_pro');
  renderVault();
  toast('Vault History Cleared');
});

// Init
renderVault();
