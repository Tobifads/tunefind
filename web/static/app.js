const uploadForm = document.getElementById('upload-form');
const uploadStatus = document.getElementById('upload-status');
const searchForm = document.getElementById('search-form');
const searchStatus = document.getElementById('search-status');
const results = document.getElementById('results');

function renderMatches(matches) {
  results.innerHTML = '';
  matches.forEach((match) => {
    const card = document.createElement('div');
    card.className = 'result-card';
    card.innerHTML = `
      <div>
        <strong>${match.filename}</strong><br />
        <small>Beat ID: ${match.beat_id}</small>
      </div>
      <div>Score: ${match.score}</div>
    `;
    results.appendChild(card);
  });
}

uploadForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  uploadStatus.textContent = 'Uploading...';
  const data = new FormData(uploadForm);
  try {
    const res = await fetch('/upload', { method: 'POST', body: data });
    const payload = await res.json();
    if (!res.ok) throw new Error(payload.error || 'Upload failed');
    uploadStatus.textContent = `Uploaded: ${payload.filename}`;
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
    renderMatches(payload.matches);
  } catch (err) {
    searchStatus.textContent = err.message;
  }
});
