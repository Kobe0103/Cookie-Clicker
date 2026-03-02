let currentState = null;

async function api(path, method = 'GET', body = null) {
  const res = await fetch(path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : null
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || 'Request failed');
  }
  return data;
}

function applyTheme(theme) {
  document.documentElement.style.setProperty('--bg', theme.background);
  document.documentElement.style.setProperty('--primary', theme.primary);
  document.documentElement.style.setProperty('--accent', theme.accent);

  document.getElementById('title').textContent = theme.title;
  document.getElementById('resource-emoji').textContent = theme.emoji;
  document.getElementById('resource-name').textContent = theme.resourceName;
  document.getElementById('click-btn').textContent = theme.actionLabel;
}

function render(state) {
  currentState = state;
  applyTheme(state.theme);

  document.getElementById('resource-count').textContent = state.resource_count.toFixed(2);
  document.getElementById('total-clicks').textContent = state.total_clicks;
  document.getElementById('cps').textContent = state.cps.toFixed(2);

  const wrap = document.getElementById('upgrades');
  const template = document.getElementById('upgrade-template');
  wrap.innerHTML = '';

  state.upgrades.forEach((upgrade) => {
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector('.upgrade-name').textContent = upgrade.name;
    node.querySelector('.upgrade-description').textContent = `${upgrade.description} (+${upgrade.cps}/sec)`;
    node.querySelector('.upgrade-owned').textContent = upgrade.quantity;

    const btn = node.querySelector('.buy-btn');
    btn.textContent = `Buy (${upgrade.next_cost.toFixed(2)})`;
    btn.disabled = state.resource_count < upgrade.next_cost;
    btn.addEventListener('click', () => buy(upgrade.id));

    wrap.appendChild(node);
  });
}

async function refresh() {
  const state = await api('/api/state');
  render(state);
}

async function clickResource() {
  const state = await api('/api/click', 'POST');
  render(state);
}

async function buy(upgradeId) {
  const response = await api('/api/buy', 'POST', { upgrade_id: upgradeId });
  render(response.state);
}

document.getElementById('click-btn').addEventListener('click', clickResource);
refresh();
setInterval(refresh, 1000);
