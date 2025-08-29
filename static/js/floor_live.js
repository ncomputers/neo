const canvas = document.getElementById('floor-live');
const ctx = canvas.getContext('2d');
const zoneSelect = document.getElementById('zone-filter');

const STATE_COLORS = {
  open: '#4ade80',
  prep: '#facc15',
  ready: '#3b82f6',
  billed: '#f97316',
  locked: '#9ca3af'
};

function resize() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  draw(currentTables);
}
window.addEventListener('resize', resize);

let currentTables = [];

function draw(tables) {
  if (!ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  tables.forEach(t => {
    if (zoneSelect.value && t.zone !== zoneSelect.value) {
      return;
    }
    const color = STATE_COLORS[t.state?.toLowerCase()] || '#e5e7eb';
    ctx.fillStyle = color;
    const x = t.x ?? 0;
    const y = t.y ?? 0;
    const width = t.width ?? 80;
    const height = t.height ?? 80;
    ctx.fillRect(x, y, width, height);
    if (t.label) {
      ctx.fillStyle = '#000';
      ctx.fillText(t.label, x + 4, y + 12);
    }
  });
}

async function fetchTables() {
  const tenant = new URLSearchParams(window.location.search).get('tenant');
  if (!tenant) return [];
  const resp = await fetch(`/api/outlet/${tenant}/tables/map`);
  const json = await resp.json();
  return json.data ?? [];
}

async function init() {
  currentTables = await fetchTables();
  const zones = Array.from(new Set(currentTables.map(t => t.zone).filter(Boolean)));
  zones.forEach(z => {
    const opt = document.createElement('option');
    opt.value = z;
    opt.textContent = z;
    zoneSelect.appendChild(opt);
  });
  draw(currentTables);
  const tenant = new URLSearchParams(window.location.search).get('tenant');
  if (tenant) {
    const evt = new EventSource(`/floor/stream?tenant=${tenant}`);
    evt.onmessage = e => {
      try {
        const payload = JSON.parse(e.data);
        if (Array.isArray(payload.tables)) {
          currentTables = payload.tables;
          draw(currentTables);
        }
      } catch (_) {
        // ignore malformed messages
      }
    };
  }
}

zoneSelect.addEventListener('change', () => draw(currentTables));

resize();
init();
