let currentBalance = 0;
let qrBalance = 0;
let lastStatsData = null;

async function loadBalance(force = false) {
    const balanceEl = document.getElementById('balance');
    
    if (!force && currentBalance > 0) {
        balanceEl.textContent = (currentBalance - 1000).toFixed(2) + ' MDL';
        return;
    }
    
    try {
        const resp = await fetch('/api/balance');
        if (!resp.ok) throw new Error('API error');
        const data = await resp.json();
        currentBalance = data.balance || 0;
        balanceEl.textContent = (currentBalance - 1000).toFixed(2) + ' MDL';
    } catch (e) {
        console.error('Ошибка баланса:', e);
        if (currentBalance > 0) {
            balanceEl.textContent = (currentBalance - 1000).toFixed(2) + ' MDL';
        }
    }
}

async function loadQrBalance(force = false) {
    const qrEl = document.getElementById('qrBalance');
    
    if (!force && qrBalance > 0) {
        qrEl.textContent = qrBalance + ' MDL';
        return;
    }
    
    try {
        const resp = await fetch('/api/qr-balance');
        if (!resp.ok) throw new Error('API error');
        const data = await resp.json();
        qrBalance = data.qr_balance || '0';
        qrEl.textContent = qrBalance + ' MDL';
    } catch (e) {
        console.error('Ошибка QR-баланса:', e);
        if (qrBalance > 0) {
            qrEl.textContent = qrBalance + ' MDL';
        }
    }
}

async function loadStats(force = false) {
    const btn = document.getElementById('refreshBtn');
    const loader = document.getElementById('loader');
    const error = document.getElementById('error');
    const content = document.getElementById('content');
    const lastUpdate = document.getElementById('lastUpdate');

    if (!force && lastStatsData) {
        renderStats(lastStatsData);
        return;
    }

    btn.classList.add('loading');
    btn.textContent = '⏳ Загрузка...';
    loader.classList.remove('d-none');
    error.classList.add('d-none');

    try {
        const response = await fetch('/api/stats');
        if (!response.ok) throw new Error('Ошибка сервера: ' + response.status);

        const data = await response.json();
        if (data.error) throw new Error(data.error);

        lastStatsData = data;
        error.classList.add('d-none');
        content.classList.remove('d-none');
        
        // Если данные из БД (токен умер) — показываем предупреждение
        if (data.cached) {
            error.textContent = '⚠️ Токен недействителен, обнови в настройках';
            error.classList.remove('d-none');
        }
        
        renderStats(data);

    } catch (e) {
        content.classList.remove('d-none');
        
        if (lastStatsData) {
            error.textContent = '⚠️ Не удалось обновить данные. Показаны последние данные.';
            error.classList.remove('d-none');
            renderStats(lastStatsData);
        } else {
            error.textContent = '❌ ' + e.message;
            error.classList.remove('d-none');
        }
    } finally {
        btn.classList.remove('loading');
        btn.textContent = '📊 ОБНОВИТЬ СТАТИСТИКУ';
        loader.classList.add('d-none');
    }
}

function renderStats(data) {
    const t = data.today;
    const y = data.yesterday;

    if (data.shift_open) {
        document.getElementById('shiftLabel').textContent = 'Текущая смена vs прошлая смена';
    } else {
        document.getElementById('shiftLabel').textContent = 'Нет открытой смены. Показана прошлая смена';
    }

    function compare(id, todayVal, yesterdayVal, unit) {
        document.getElementById(id).textContent = todayVal + ' ' + unit;
        const diffEl = document.getElementById(id + 'Diff');
        if (diffEl && yesterdayVal > 0) {
            const diff = todayVal - yesterdayVal;
            const sign = diff >= 0 ? '↑' : '↓';
            const color = diff >= 0 ? 'text-success' : 'text-danger';
            diffEl.innerHTML = '<span class="' + color + '">' + sign + ' ' + Math.abs(diff).toFixed(1) + ' ' + unit + '</span>';
        } else if (diffEl) {
            diffEl.innerHTML = '';
        }
    }

    compare('orders', t.orders, y.orders, 'зак.');
    document.getElementById('distance').textContent = (t.distance_km || 0).toFixed(1) + ' км';

    const distDiff = document.getElementById('distanceDiff');
    if (distDiff && y.distance_km > 0) {
        const d = (t.distance_km || 0) - (y.distance_km || 0);
        const sign = d >= 0 ? '↑' : '↓';
        const color = d >= 0 ? 'text-success' : 'text-danger';
        distDiff.innerHTML = '<span class="' + color + '">' + sign + ' ' + Math.abs(d).toFixed(1) + ' км</span>';
    } else if (distDiff) {
        distDiff.innerHTML = '';
    }

    compare('income', t.income, y.income, 'MDL');
    compare('commission', t.commission, y.commission, 'MDL');
    compare('netProfit', t.net_profit, y.net_profit, 'MDL');

    document.getElementById('lastUpdate').textContent = 'Последнее обновление: ' + (data.last_update || 'сейчас');
    document.getElementById('content').classList.remove('d-none');
}

function refreshAll() {
    loadBalance(true);
    loadQrBalance(true);
    loadStats(true);
}

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('balance').textContent = '... MDL';
    document.getElementById('qrBalance').textContent = '... MDL';
    document.getElementById('content').classList.remove('d-none');
    
    loadBalance().catch(function() {});
    loadQrBalance().catch(function() {});
    loadStats().catch(function() {});
});

// Тёмная тема
function toggleTheme() {
    const isDark = document.getElementById('themeToggle').checked;
    document.documentElement.setAttribute('data-bs-theme', isDark ? 'dark' : 'light');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}

// При загрузке страницы — применить сохранённую тему
(function() {
    const saved = localStorage.getItem('theme');
    if (saved === 'dark') {
        document.documentElement.setAttribute('data-bs-theme', 'dark');
        document.getElementById('themeToggle').checked = true;
    }
})();