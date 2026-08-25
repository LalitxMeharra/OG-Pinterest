const fetchForm = document.getElementById('fetchForm');
const pinUrlInput = document.getElementById('pinUrl');
const pasteBtn = document.getElementById('pasteBtn');
const submitBtn = document.getElementById('submitBtn');

const previewBlock = document.getElementById('previewBlock');
const mediaWrapper = document.getElementById('mediaWrapper');
const mediaTypeTag = document.getElementById('mediaTypeTag');
const previewTitle = document.getElementById('previewTitle');
const btnPrimaryDl = document.getElementById('btnPrimaryDl');
const btnPrimaryText = document.getElementById('btnPrimaryText');
const btnPrimarySub = document.getElementById('btnPrimarySub');
const btnCopyLink = document.getElementById('btnCopyLink');

const historySection = document.getElementById('historySection');
const historyGrid = document.getElementById('historyGrid');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');

let activeDownloadUrl = '';

function toast(msg) {
  const t = document.getElementById('toast');
  document.getElementById('toastMsg').textContent = msg;
  t.classList.add('show');
  clearTimeout(t._h);
  t._h = setTimeout(() => t.classList.remove('show'), 2400);
}

// 1. SMART CLIPBOARD PASTE WITH FALLBACK
pasteBtn.addEventListener('click', async () => {
  try {
    if (navigator.clipboard && navigator.clipboard.readText) {
      const text = await navigator.clipboard.readText();
      if (text) {
        pinUrlInput.value = text.trim();
        toast('Link Pasted from Clipboard');
        return;
      }
    }
  } catch (_) {}
  
  // Fallback if permission blocked
  pinUrlInput.focus();
  toast('Please paste manually using Ctrl+V / Long press');
});

// 2. FETCH PIN VIA VERCEL BACKEND
fetchForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const rawUrl = pinUrlInput.value.trim();
  if (!rawUrl) return;

  submitBtn.disabled = true;
  submitBtn.textContent = '⚡ FETCHING...';
  toast('Decoupling & Resolving Media Stream...');

  try {
    const res = await fetch(`/api/fetch?url=${encodeURIComponent(rawUrl)}`);
    const data = await res.json();

    if (!res.ok || data.status !== 'success') {
      throw new Error(data.message || 'Failed to extract pin');
    }

    renderMedia(data);
    saveToHistory(data);
    toast('Media Stream Decrypted!');
  } catch (err) {
    toast(`Error: ${err.message}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = '⚡ FETCH';
  }
});

// 3. RENDER MEDIA PREVIEW
function renderMedia(data) {
  activeDownloadUrl = window.location.origin + data.proxy_download;
  previewTitle.textContent = data.title;

  if (data.type === 'video') {
    mediaTypeTag.textContent = 'VIDEO · 1080P HD';
    mediaWrapper.innerHTML = `
      <video controls autoplay loop playsinline src="${data.proxy_stream}"></video>
    `;
    btnPrimaryText.textContent = '⬇ DOWNLOAD MP4 VIDEO';
    btnPrimarySub.textContent = 'Direct High-Bitrate Master';
  } else {
    mediaTypeTag.textContent = 'IMAGE · 4K ORIGINAL';
    mediaWrapper.innerHTML = `
      <img src="${data.proxy_stream}" alt="Decrypted Pin" loading="lazy">
    `;
    btnPrimaryText.textContent = '⬇ DOWNLOAD 4K IMAGE';
    btnPrimarySub.textContent = 'Original Raw JPG/PNG';
  }

  btnPrimaryDl.href = data.proxy_download;
  previewBlock.style.display = 'block';
  previewBlock.scrollIntoView({ behavior: 'smooth' });
}

// 4. COPY DIRECT PROXY LINK
btnCopyLink.addEventListener('click', () => {
  if (!activeDownloadUrl) return;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(activeDownloadUrl);
    toast('Direct Download Link Copied!');
  } else {
    const tempInput = document.createElement('input');
    tempInput.value = activeDownloadUrl;
    document.body.appendChild(tempInput);
    tempInput.select();
    document.execCommand('copy');
    document.body.removeChild(tempInput);
    toast('Direct Download Link Copied!');
  }
});

// 5. CLIENT-SIDE RECENT VAULT (localStorage)
function getHistory() {
  try {
    return JSON.parse(localStorage.getItem('og_pin_vault')) || [];
  } catch (e) {
    return [];
  }
}

function saveToHistory(item) {
  let list = getHistory();
  list = list.filter(i => i.title !== item.title);
  list.unshift({
    title: item.title,
    type: item.type,
    thumbnail: item.thumbnail,
    proxy_stream: item.proxy_stream,
    proxy_download: item.proxy_download
  });
  if (list.length > 6) list.pop();
  localStorage.setItem('og_pin_vault', JSON.stringify(list));
  renderHistory();
}

function renderHistory() {
  const list = getHistory();
  if (!list.length) {
    historySection.style.display = 'none';
    return;
  }

  historyGrid.innerHTML = list.map(item => `
    <div class="history-card" onclick='restoreFromHistory(${JSON.stringify(item)})'>
      <img class="history-thumb" src="${item.thumbnail}" alt="Thumb" loading="lazy">
      <div class="history-title">${item.title}</div>
    </div>
  `).join('');

  historySection.style.display = 'block';
}

window.restoreFromHistory = function(item) {
  renderMedia(item);
};

clearHistoryBtn.addEventListener('click', () => {
  localStorage.removeItem('og_pin_vault');
  renderHistory();
  toast('Vault History Cleared');
});

// Init History Load
renderHistory();
