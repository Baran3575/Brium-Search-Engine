const f = document.getElementById('f');
const q = document.getElementById('q');
const r = document.getElementById('results');
const hero = document.getElementById('hero');
const crawling = document.getElementById('crawling');

// Detect Android WebView bridge and make links open in-app
const isAndroid = typeof BriumAndroid !== 'undefined';

document.addEventListener('click', (e) => {
  const link = e.target.closest('a');
  if (link && link.href && link.href.startsWith('http')) {
    if (isAndroid) {
      e.preventDefault();
      BriumAndroid.openInApp(link.href);
    }
  }
});

f.addEventListener('submit', async (e) => {
  e.preventDefault();
  const query = q.value.trim();
  if (!query) return;
  hero.classList.add('has-results');
  r.innerHTML = '<div class="empty">Searching…</div>';
  try {
    const res = await fetch(`/search?q=${encodeURIComponent(query)}&top_k=20`);
    const d = await res.json();
    crawling.style.display = d.crawling ? 'block' : 'none';
    if (!res.ok) { r.innerHTML = `<div class="empty">Error</div>`; return; }
    if (d.results.length === 0) {
      r.innerHTML = `<div class="empty">No results yet<div class="hint">Crawling the web for "${query}" — results will appear shortly</div></div>`;
      _poll(query);
      return;
    }
    r.innerHTML = d.results.map(item =>
      `<div class="result">
        <div class="url">${item.url}</div>
        <div class="title"><a href="${item.url}" target="_blank">${item.title || item.url}</a></div>
        <div class="snippet">${item.snippet || ''}</div>
        <div class="meta">score ${item.score.toFixed(3)}</div>
      </div>`
    ).join('');
    if (d.crawling) _poll(query);
  } catch (err) { r.innerHTML = `<div class="empty">Request failed</div>`; }
});

let pollTimer;
function _poll(query) {
  clearTimeout(pollTimer);
  pollTimer = setTimeout(async () => {
    const res = await fetch(`/search?q=${encodeURIComponent(query)}&top_k=20`);
    const d = await res.json();
    crawling.style.display = d.crawling ? 'block' : 'none';
    if (d.results.length > 0) {
      crawling.style.display = 'none';
      r.innerHTML = d.results.map(item =>
        `<div class="result">
          <div class="url">${item.url}</div>
          <div class="title"><a href="${item.url}" target="_blank">${item.title || item.url}</a></div>
          <div class="meta">score ${item.score.toFixed(3)}</div>
        </div>`
      ).join('');
      return;
    }
    _poll(query);
  }, 3000);
}

const urlParams = new URLSearchParams(window.location.search);
const initialQ = urlParams.get('q');
if (initialQ) { q.value = initialQ; f.dispatchEvent(new Event('submit')); }
