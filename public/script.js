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

let directMediaUrl = '';

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
  toast('Please paste manually');
});

// 2. FETCH FROM API
fetchForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const rawUrl = pinUrlInput.value.trim();
  if (!rawUrl) return;

  submitBtn.disabled = true;
  submitBtn.textContent = '⚡ EXTRACTING...';
  toast('Resolving Pin Data...');

  try {
    const res = await fetch(`/api/fetch?url=${encodeURIComponent(rawUrl)}`);
    const data = await res.json();

    if (!res.ok || data.status !== 'success') {
      throw new Error(data.message || 'Unable to extract pin');
    }

    renderMedia(data);
    toast('Media Extracted Successfully!');
  } catch (err) {
    toast(`Error: ${err.message}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = '⚡ EXTRACT';
  }
});

// 3. RENDER MEDIA PREVIEW
function renderMedia(data) {
  directMediaUrl = data.url;
  previewTitle.textContent = data.title;

  if (data.type === 'video') {
    mediaTypeTag.textContent = 'VIDEO · 1080P MASTER';
    mediaWrapper.innerHTML = `
      <video controls autoplay loop playsinline src="${data.url}"></video>
    `;
    btnPrimaryText.textContent = '⬇ DOWNLOAD MP4 VIDEO';
    btnPrimarySub.textContent = 'Direct Pinterest CDN Stream';
  } else {
    mediaTypeTag.textContent = 'IMAGE · 4K ORIGINAL';
    mediaWrapper.innerHTML = `
      <img src="${data.url}" alt="Pinterest Image" loading="lazy">
    `;
    btnPrimaryText.textContent = '⬇ DOWNLOAD 4K IMAGE';
    btnPrimarySub.textContent = 'Direct Pinterest CDN Raw';
  }

  btnPrimaryDl.href = data.url;
  btnPrimaryDl.target = '_blank';
  previewBlock.style.display = 'block';
  previewBlock.scrollIntoView({ behavior: 'smooth' });
}

// 4. COPY DIRECT CDN LINK
btnCopyLink.addEventListener('click', () => {
  if (!directMediaUrl) return;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(directMediaUrl);
    toast('Direct Pinterest CDN Link Copied!');
  } else {
    const temp = document.createElement('input');
    temp.value = directMediaUrl;
    document.body.appendChild(temp);
    temp.select();
    document.execCommand('copy');
    document.body.removeChild(temp);
    toast('Direct Pinterest CDN Link Copied!');
  }
});
