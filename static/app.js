const SAVE_KEY = 'themeable_clicker_save_v2';
let config = null;
let state = null;

function defaultState() {
  const owned = {};
  for (const upgrade of config.upgrades) owned[upgrade.id] = 0;
  return {
    resourceCount: 0,
    totalClicks: 0,
    lastUpdated: Date.now(),
    owned
  };
}

function loadSave() {
  try {
    const raw = localStorage.getItem(SAVE_KEY);
    if (!raw) return defaultState();
    const parsed = JSON.parse(raw);
    const base = defaultState();
    return {
      ...base,
      ...parsed,
      owned: { ...base.owned, ...(parsed.owned || {}) }
    };
  } catch {
    return defaultState();
  }
}

function save() {
  localStorage.setItem(SAVE_KEY, JSON.stringify(state));
}

function currentCps() {
  return config.upgrades.reduce((sum, u) => sum + (state.owned[u.id] || 0) * u.cps, 0);
}

function applyOfflineProgress() {
  const now = Date.now();
  const elapsed = Math.max((now - state.lastUpdated) / 1000, 0);
  state.resourceCount += currentCps() * elapsed;
  state.lastUpdated = now;
}

function nextCost(upgrade) {
  const qty = state.owned[upgrade.id] || 0;
  return upgrade.base_cost * (upgrade.cost_multiplier || 1.15) ** qty;
}

function applyTheme() {
  const t = config.theme;
  document.documentElement.style.setProperty('--bg', t.background || '#0b0f14');
  document.documentElement.style.setProperty('--primary', t.primary || '#4cc9f0');
  document.documentElement.style.setProperty('--accent', t.accent || '#7b2cbf');
  document.getElementById('game-title').textContent = t.title;
  document.getElementById('resource-name').textContent = t.resourceName;
  document.getElementById('resource-emoji').textContent = t.emoji || '✨';
  document.getElementById('click-btn').textContent = t.actionLabel || 'Generate';
}

function render() {
  applyTheme();
  document.getElementById('resource-count').textContent = state.resourceCount.toFixed(2);
  document.getElementById('total-clicks').textContent = state.totalClicks;
  document.getElementById('cps').textContent = currentCps().toFixed(2);

  const wrap = document.getElementById('upgrades');
  const tpl = document.getElementById('upgrade-template');
  wrap.innerHTML = '';

  for (const upgrade of config.upgrades) {
    const node = tpl.content.firstElementChild.cloneNode(true);
    const cost = nextCost(upgrade);

    node.querySelector('.upgrade-name').textContent = upgrade.name;
    node.querySelector('.upgrade-desc').textContent = `${upgrade.description} (+${upgrade.cps}/sec)`;
    node.querySelector('.upgrade-owned').textContent = state.owned[upgrade.id] || 0;

    const btn = node.querySelector('.buy-btn');
    btn.textContent = `Buy (${cost.toFixed(2)})`;
    btn.disabled = state.resourceCount < cost;
    btn.addEventListener('click', () => {
      if (state.resourceCount < cost) return;
      state.resourceCount -= cost;
      state.owned[upgrade.id] = (state.owned[upgrade.id] || 0) + 1;
      save();
      render();
    });

    wrap.appendChild(node);
  }
}

function clickMain() {
  applyOfflineProgress();
  state.resourceCount += 1;
  state.totalClicks += 1;
  save();
  render();
}

function resetSave() {
  localStorage.removeItem(SAVE_KEY);
  state = defaultState();
  save();
  render();
}

async function init() {
  const response = await fetch('/config/game_config.json');
  config = await response.json();
  state = loadSave();
  applyOfflineProgress();
  save();
  render();

  document.getElementById('click-btn').addEventListener('click', clickMain);
  document.getElementById('reset-btn').addEventListener('click', resetSave);

  setInterval(() => {
    applyOfflineProgress();
    save();
    render();
  }, 1000);
}

init();
