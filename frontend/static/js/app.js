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

async function loadStats() {
    const btn = document.getElementById('refreshBtn');
    const loader = document.getElementById('loader');
    const error = document.getElementById('error');
    const content = document.getElementById('content');
    const lastUpdate = document.getElementById('lastUpdate');
    const stepProgress = document.getElementById('stepProgress');

    btn.classList.add('loading');
    btn.textContent = '⏳ Загрузка...';
    loader.classList.remove('d-none');
    error.classList.add('d-none');
    content.classList.add('d-none');

    // Показываем шагомер
    stepProgress.classList.remove('d-none');

    // Сброс шагов
    document.querySelectorAll('#steps > div').forEach(el => {
        el.querySelector('.step-icon').textContent = '⚪';
        el.querySelector('.step-icon').classList.remove('text-success', 'text-primary');
        el.querySelector('span:last-child').classList.add('text-muted');
    });

    // Шаг 1: Авторизация
    const stepAuth = document.getElementById('step-auth');
    stepAuth.querySelector('.step-icon').textContent = '⏳';
    stepAuth.querySelector('span:last-child').classList.remove('text-muted');

    try {
        const response = await fetch('/api/stats');
        if (!response.ok) throw new Error(`Ошибка сервера: ${response.status}`);

        const data = await response.json();
        if (data.error) throw new Error(data.error);

        const t = data.today;
        const y = data.yesterday;

        // Шаг 1: Авторизация завершена
        stepAuth.querySelector('.step-icon').textContent = '✅';
        stepAuth.querySelector('.step-icon').classList.add('text-success');
        stepAuth.querySelector('span:last-child').classList.add('text-muted');

        // Шаг 2: Транзакции загружены
        const stepTransactions = document.getElementById('step-transactions');
        stepTransactions.querySelector('.step-icon').textContent = '✅';
        stepTransactions.querySelector('.step-icon').classList.add('text-success');
        stepTransactions.querySelector('span:last-child').classList.remove('text-muted');

        // Шаг 3: Детали
        const stepDetails = document.getElementById('step-details');
        stepDetails.querySelector('.step-icon').textContent = '✅';
        stepDetails.querySelector('.step-icon').classList.add('text-success');
        stepDetails.querySelector('span:last-child').classList.remove('text-muted');

        // Шаг 4: Готово
        const stepDone = document.getElementById('step-done');
        stepDone.querySelector('.step-icon').textContent = '✅';
        stepDone.querySelector('.step-icon').classList.add('text-success');
        stepDone.querySelector('span:last-child').classList.remove('text-muted');

        // Функция сравнения
        function compare(id, todayVal, yesterdayVal, unit) {
            document.getElementById(id).textContent = todayVal + ' ' + unit;
            const diffEl = document.getElementById(id + 'Diff');
            if (diffEl && yesterdayVal > 0) {
                const diff = todayVal - yesterdayVal;
                const sign = diff >= 0 ? '↑' : '↓';
                const color = diff >= 0 ? 'text-success' : 'text-danger';
                diffEl.innerHTML = `<span class="${color}">${sign} ${Math.abs(diff).toFixed(1)} ${unit}</span>`;
            }
        }

        compare('orders', t.orders, y.orders, '');
        document.getElementById('distance').textContent = (t.distance_km || 0) + ' км';
        compare('income', t.income, y.income, 'MDL');
        compare('commission', t.commission, y.commission, 'MDL');
        compare('netProfit', t.net_profit, y.net_profit, 'MDL');

        document.getElementById('percentZ').textContent = '0%';
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
        setTimeout(() => {
            stepProgress.classList.add('d-none');
        }, 1500);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadBalance();
    loadStats();
});