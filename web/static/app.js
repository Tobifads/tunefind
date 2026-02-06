const libraryForm = document.getElementById('library-form');
const libraryStatus = document.getElementById('library-status');
const libraryResults = document.getElementById('library-results');
const uploadForm = document.getElementById('upload-form');
const uploadStatus = document.getElementById('upload-status');
const searchForm = document.getElementById('search-form');
const searchStatus = document.getElementById('search-status');
const results = document.getElementById('results');

function renderMatches(container, matches) {
  container.innerHTML = '';
  if (!matches.length) {
    container.innerHTML = '<div class="result-card">No beats found yet.</div>';
    return;
  }
  matches.forEach((match) => {
    const card = document.createElement('div');
    card.className = 'result-card';
    const detail = match.score
      ? `Score: ${match.score}`
      : `Duration: ${match.duration_s.toFixed(2)}s`;
    card.innerHTML = `
      <div>
        <strong>${match.filename}</strong><br />
        <small>Beat ID: ${match.beat_id}</small>
      </div>
      <div>${detail}</div>
    `;
    container.appendChild(card);
  });
}

async function loadLibrary(ownerId) {
  libraryStatus.textContent = 'Loading library...';
  try {
    const res = await fetch(`/beats?owner_id=${encodeURIComponent(ownerId)}`);
    const payload = await res.json();
    if (!res.ok) throw new Error(payload.error || 'Failed to load library');
    libraryStatus.textContent = `Library has ${payload.count} beat(s).`;
    renderMatches(libraryResults, payload.beats);
  } catch (err) {
    libraryStatus.textContent = err.message;
    libraryResults.innerHTML = '';
  }
}

libraryForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const ownerId = new FormData(libraryForm).get('owner_id');
  if (ownerId) {
    loadLibrary(ownerId);
  }
});

uploadForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  uploadStatus.textContent = 'Uploading...';
  const data = new FormData(uploadForm);
  try {
    const res = await fetch('/upload', { method: 'POST', body: data });
    const payload = await res.json();
    if (!res.ok) throw new Error(payload.error || 'Upload failed');
    uploadStatus.textContent = `Uploaded: ${payload.filename}`;
    const ownerId = data.get('owner_id');
    if (ownerId) {
      loadLibrary(ownerId);
    }
  } catch (err) {
    uploadStatus.textContent = err.message;
  }
});

searchForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  searchStatus.textContent = 'Searching...';
  results.innerHTML = '';
  const data = new FormData(searchForm);
  try {
    const res = await fetch('/search', { method: 'POST', body: data });
    const payload = await res.json();
    if (!res.ok) throw new Error(payload.error || 'Search failed');
    searchStatus.textContent = `Found ${payload.count} match(es).`;
    renderMatches(results, payload.matches);
  } catch (err) {
    searchStatus.textContent = err.message;
  }
});
