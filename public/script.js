const fetchForm = document.getElementById('fetchForm');
const pinUrlInput = document.getElementById('pinUrl');
const pasteBtn = document.getElementById('pasteBtn');
const submitBtn = document.getElementById('submitBtn');

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

let forceDownloadLink = ''; 

function toast(msg) {
  const t = document.getElementById('toast');
  if (!t) return;
  document.getElementById('toastMsg').textContent = msg;
  t.classList.add('show');
  clearTimeout(t._h);
  t._h = setTimeout(() => t.classList.remove('show'), 2400);
}

// Format seconds to mm:ss
function formatTime(seconds) {
  let min = Math.floor(seconds / 60);
  let sec = Math.floor(seconds % 60);
  return `${min}:${sec < 10 ? '0' : ''}${sec}`;
}

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

// Custom Video Player Builder
function buildCustomVideoPlayer(videoUrl, posterUrl) {
  return `
    <div class="vp-wrapper" id="customPlayer">
      <video id="vpVid" src="${videoUrl}" poster="${posterUrl}" playsinline preload="metadata"></video>
      <button class="vp-big-play" id="vpBigPlay">
        <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
      </button>
      <div class="vp-controls">
        <button class="vp-btn" id="vpPlay">
          <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
        </button>
        <div class="vp-progress-wrap">
          <input type="range" class="vp-progress" id="vpSeek" min="0" max="100" value="0" step="0.1">
        </div>
        <span class="vp-time" id="vpTime">0:00</span>
        <button class="vp-btn" id="vpMute">
          <svg viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/></svg>
        </button>
      </div>
    </div>
  `;
}

function initVideoLogic() {
  const wrapper = document.getElementById('customPlayer');
  const vid = document.getElementById('vpVid');
  const bigPlay = document.getElementById('vpBigPlay');
  const playBtn = document.getElementById('vpPlay');
  const seek = document.getElementById('vpSeek');
  const time = document.getElementById('vpTime');
  const muteBtn = document.getElementById('vpMute');

  if(!vid) return;

  let isDragging = false;

  const togglePlay = () => {
    vid.paused ? vid.play() : vid.pause();
  };

  const updatePlayIcons = () => {
    if (vid.paused) {
      bigPlay.style.display = 'flex';
      playBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
      wrapper.classList.remove('active');
    } else {
      bigPlay.style.display = 'none';
      playBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>';
      wrapper.classList.add('active');
    }
  };

  vid.addEventListener('play', updatePlayIcons);
  vid.addEventListener('pause', updatePlayIcons);
  vid.addEventListener('click', togglePlay);
  bigPlay.addEventListener('click', togglePlay);
  playBtn.addEventListener('click', togglePlay);

  vid.addEventListener('timeupdate', () => {
    if (!isDragging) {
      const progress = (vid.currentTime / vid.duration) * 100 || 0;
      seek.value = progress;
    }
    time.textContent = formatTime(vid.currentTime);
  });

  seek.addEventListener('input', () => isDragging = true);
  seek.addEventListener('change', (e) => {
    vid.currentTime = (e.target.value / 100) * vid.duration;
    isDragging = false;
  });

  muteBtn.addEventListener('click', () => {
    vid.muted = !vid.muted;
    muteBtn.innerHTML = vid.muted 
      ? '<svg viewBox="0 0 24 24"><path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/></svg>'
      : '<svg viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/></svg>';
  });
}

function renderResult(data) {
  forceDownloadLink = window.location.origin + data.proxy_download;
  
  if (previewTitle) previewTitle.textContent = data.title;
  if (previewMeta) previewMeta.textContent = data.type === 'video' ? 'Direct Pipeline Stream · MP4 Video' : 'Direct Pipeline Stream · 4K Image';

  if (data.type === 'video') {
    if (mediaTypeTag) mediaTypeTag.textContent = 'VIDEO · 1080P MASTER';
    // Yaha apna TAGDA custom player inject ho raha hai
    if (mediaWrapper) {
        mediaWrapper.innerHTML = buildCustomVideoPlayer(data.url, data.thumbnail);
        initVideoLogic(); // Listeners attach karna
    }
    if (btnPrimaryText) btnPrimaryText.textContent = '⬇ DOWNLOAD MP4';
    if (btnPrimarySub) btnPrimarySub.textContent = 'Master Quality Video';
  } else {
    if (mediaTypeTag) mediaTypeTag.textContent = 'IMAGE · 4K ORIGINAL';
    if (mediaWrapper) mediaWrapper.innerHTML = `<img src="${data.url}" alt="Pin Media" loading="lazy" style="max-width: 100%; max-height: 480px; object-fit: contain;">`;
    if (btnPrimaryText) btnPrimaryText.textContent = '⬇ DOWNLOAD 4K JPG';
    if (btnPrimarySub) btnPrimarySub.textContent = 'Original Raw Image';
  }

  if (btnPrimaryDl) btnPrimaryDl.href = data.proxy_download;
  
  if (previewBlock) {
    previewBlock.style.display = 'block';
    previewBlock.scrollIntoView({ behavior: 'smooth' });
  }
}

if (btnCopyLink) {
  btnCopyLink.addEventListener('click', () => {
    if (!forceDownloadLink) return;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(forceDownloadLink);
      toast('Link Copied!'); // Updated Toast Text
    } else {
      const temp = document.createElement('input');
      temp.value = forceDownloadLink;
      document.body.appendChild(temp);
      temp.select();
      document.execCommand('copy');
      document.body.removeChild(temp);
      toast('Link Copied!'); // Updated Toast Text
    }
  });
}

function fetchVault() {
  try { return JSON.parse(localStorage.getItem('og_vault_pro')) || []; }
  catch (e) { return []; }
}

function persistVault(item) {
  let list = fetchVault();
  list = list.filter(i => i.url !== item.url);
  
  // Save specific payload including thumbnail
  list.unshift({
      title: item.title,
      type: item.type,
      url: item.url,
      thumbnail: item.thumbnail || item.url, // Video h to thumb, image h to url
      proxy_download: item.proxy_download
  });

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
        <img class="history-thumb" src="${item.thumbnail}" alt="Vault Item" loading="lazy">
        <div class="history-title">${item.title}</div>
      </div>
    `).join('');
  }

  if (historySection) historySection.style.display = 'block';
}

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

renderVault();
