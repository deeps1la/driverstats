let currentBalance = 0;

async function loadBalance() {
    try {
        const resp = await fetch('/api/balance');
        const data = await resp.json();
        currentBalance = data.balance || 0;
        document.getElementById('balance').textContent = (currentBalance - 1000).toFixed(2) + ' MDL';
    } catch (e) {
        console.error('Ошибка баланса:', e);
    }
}

async function loadQrBalance() {
    try {
        const resp = await fetch('/api/qr-balance');
        const data = await resp.json();
        document.getElementById('qrBalance').textContent = (data.qr_balance || '0') + ' MDL';
    } catch (e) {
        console.error('Ошибка QR-баланса:', e);
    }
}

async function loadStats() {
    const btn = document.getElementById('refreshBtn');
    const loader = document.getElementById('loader');
    const error = document.getElementById('error');
    const content = document.getElementById('content');
    const lastUpdate = document.getElementById('lastUpdate');

    btn.classList.add('loading');
    btn.textContent = '⏳ Загрузка...';
    loader.classList.remove('d-none');
    error.classList.add('d-none');
    content.classList.add('d-none');

    try {
        const response = await fetch('/api/stats');
        if (!response.ok) throw new Error(`Ошибка сервера: ${response.status}`);

        const data = await response.json();
        if (data.error) throw new Error(data.error);

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
                diffEl.innerHTML = `<span class="${color}">${sign} ${Math.abs(diff).toFixed(1)} ${unit}</span>`;
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
            distDiff.innerHTML = `<span class="${color}">${sign} ${Math.abs(d).toFixed(1)} км</span>`;
        } else if (distDiff) {
            distDiff.innerHTML = '';
        }

        compare('income', t.income, y.income, 'MDL');
        compare('commission', t.commission, y.commission, 'MDL');
        compare('netProfit', t.net_profit, y.net_profit, 'MDL');

        const percentZ = t.income > 0 ? ((t.commission / t.income) * 100).toFixed(1) : 0;
        document.getElementById('percentZ').textContent = percentZ + '%';
        document.getElementById('plan').textContent = '0 MDL';
        document.getElementById('fuel').textContent = '0 MDL';

        lastUpdate.textContent = 'Последнее обновление: ' + (data.last_update || 'сейчас');
        content.classList.remove('d-none');

    } catch (e) {
        error.textContent = '❌ ' + e.message;
        error.classList.remove('d-none');
    } finally {
        btn.classList.remove('loading');
        btn.textContent = '📊 ОБНОВИТЬ СТАТИСТИКУ';
        loader.classList.add('d-none');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadBalance();
    loadQrBalance();
    loadStats();
});