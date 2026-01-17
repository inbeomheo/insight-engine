/**
 * UsagePanelManager - 사용량 패널 UI 관리
 */
export class UsagePanelManager {
    constructor(storageManager, eventBus) {
        this.storageManager = storageManager;
        this.eventBus = eventBus;
        this.elements = {};
    }

    init() {
        this.cacheElements();
        this.bindEvents();
    }

    cacheElements() {
        this.elements = {
            current: document.getElementById('usage-current'),
            limit: document.getElementById('usage-limit'),
            progressBar: document.getElementById('usage-progress-bar'),
            remaining: document.getElementById('usage-remaining'),
            weeklyChart: document.getElementById('weekly-chart'),
            styleStats: document.getElementById('style-stats'),
            styleStatsEmpty: document.getElementById('style-stats-empty')
        };
    }

    bindEvents() {
        window.addEventListener('panel:usage-opened', () => this.render());
    }

    async render() {
        await this.renderTodayUsage();
        this.renderWeeklyChart();
        this.renderStyleStats();
    }

    async renderTodayUsage() {
        try {
            const response = await fetch('/api/user/usage');
            if (response.ok) {
                const data = await response.json();
                const used = data.used || 0;
                const limit = data.limit || 5;
                const remaining = Math.max(0, limit - used);
                const percent = Math.min(100, (used / limit) * 100);

                if (this.elements.current) this.elements.current.textContent = used;
                if (this.elements.limit) this.elements.limit.textContent = `/ ${limit}`;
                if (this.elements.progressBar) this.elements.progressBar.style.width = `${percent}%`;
                if (this.elements.remaining) this.elements.remaining.textContent = `남은 횟수: ${remaining}회`;
            }
        } catch (e) {
            console.warn('사용량 조회 실패:', e);
            // 기본값 유지
        }
    }

    renderWeeklyChart() {
        const chart = this.elements.weeklyChart;
        if (!chart) return;

        const history = this.storageManager.getHistory();
        const weekData = this.calculateWeeklyData(history);
        const maxValue = Math.max(...weekData.map(d => d.count), 1);

        const days = ['일', '월', '화', '수', '목', '금', '토'];
        const today = new Date().getDay();

        // 오늘부터 7일 전까지의 요일 배열 생성
        const orderedDays = [];
        for (let i = 6; i >= 0; i--) {
            const dayIndex = (today - i + 7) % 7;
            orderedDays.push({
                label: days[dayIndex],
                count: weekData[6 - i].count
            });
        }

        chart.innerHTML = orderedDays.map(day => {
            const heightPercent = (day.count / maxValue) * 100;
            return `
                <div class="weekly-bar">
                    <span class="weekly-bar-value">${day.count}</span>
                    <div class="weekly-bar-fill" style="height: ${Math.max(4, heightPercent)}%"></div>
                    <span class="weekly-bar-label">${day.label}</span>
                </div>
            `;
        }).join('');
    }

    calculateWeeklyData(history) {
        const now = new Date();
        const weekData = Array(7).fill(null).map(() => ({ count: 0 }));

        history.forEach(item => {
            const itemDate = new Date(item.createdAt || item.timestamp);
            const diffDays = Math.floor((now - itemDate) / 86400000);
            if (diffDays >= 0 && diffDays < 7) {
                weekData[6 - diffDays].count++;
            }
        });

        return weekData;
    }

    renderStyleStats() {
        const container = this.elements.styleStats;
        const emptyState = this.elements.styleStatsEmpty;
        if (!container) return;

        const history = this.storageManager.getHistory();
        const styleData = this.calculateStyleStats(history);

        if (styleData.length === 0) {
            container.innerHTML = '';
            emptyState?.classList.remove('hidden');
            return;
        }

        emptyState?.classList.add('hidden');
        const total = styleData.reduce((sum, s) => sum + s.count, 0);

        container.innerHTML = styleData.slice(0, 5).map(style => {
            const percent = Math.round((style.count / total) * 100);
            return `
                <div class="style-stat-row">
                    <span class="style-stat-label">${style.name}</span>
                    <div class="style-stat-bar-bg">
                        <div class="style-stat-bar-fill" style="width: ${percent}%"></div>
                    </div>
                    <span class="style-stat-value">${percent}% (${style.count}회)</span>
                </div>
            `;
        }).join('');
    }

    calculateStyleStats(history) {
        const styleCounts = {};

        history.forEach(item => {
            const style = item.style || 'Blog';
            styleCounts[style] = (styleCounts[style] || 0) + 1;
        });

        return Object.entries(styleCounts)
            .map(([name, count]) => ({ name, count }))
            .sort((a, b) => b.count - a.count);
    }
}
