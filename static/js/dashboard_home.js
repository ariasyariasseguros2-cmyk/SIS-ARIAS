document.addEventListener('DOMContentLoaded', () => {
    const data = window.dashboardData || {};

    // Helper to get theme colors
    const getThemeColors = () => {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        return {
            isDark: isDark,
            grid: isDark ? 'rgba(255, 255, 255, 0.15)' : '#e2e8f0', 
            text: isDark ? '#94a3b8' : '#64748b',
            accent: '#3b82f6',
            accentGlow: 'rgba(59, 130, 246, 0.5)'
        };
    };

    let colors = getThemeColors();

    // Re-initialize charts on theme change
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.attributeName === 'data-theme') {
                colors = getThemeColors();
                initProductionChart();
                initIncomeDayChart();
            }
        });
    });
    observer.observe(document.documentElement, { attributes: true });

    // Store chart instances to update them
    let productionChart, incomeDayChart;

    // 1. Production Chart (Rounded Bars with Gradients)
    function initProductionChart(currency = 'soles') {
        const ctxProduction = document.getElementById('productionChart');
        if (!ctxProduction) return;

        // Ensure data exists or use defaults
        const months = data.months || ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
        const totals = data.totals || new Array(months.length).fill(0);

        const chartData = currency === 'soles' ? totals : totals.map(v => v / 3.7);
        
        const prodGradient = ctxProduction.getContext('2d').createLinearGradient(0, 0, 0, 400);
        if (colors.isDark) {
            prodGradient.addColorStop(0, '#3b82f6');
            prodGradient.addColorStop(1, '#06b6d4');
        } else {
            prodGradient.addColorStop(0, '#399AD6');
            prodGradient.addColorStop(1, '#1F59A3');
        }

        if (productionChart) productionChart.destroy();

        productionChart = new Chart(ctxProduction, {
            type: 'bar',
            data: {
                labels: months,
                datasets: [{
                    label: 'Producción',
                    data: chartData,
                    backgroundColor: prodGradient,
                    borderColor: colors.isDark ? 'transparent' : '#1F59A3',
                    borderWidth: 1,
                    borderRadius: 12,
                    barThickness: 20
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const symbol = currency === 'soles' ? 'S/ ' : 'US$ ';
                                return symbol + new Intl.NumberFormat('es-PE', { style: 'decimal', maximumFractionDigits: 2 }).format(context.parsed.y);
                            }
                        }
                    }
                },
                scales: {
                    y: { 
                        beginAtZero: true,
                        display: true, // Always show Y axis
                        grid: { 
                            borderDash: [2, 4], 
                            color: colors.grid,
                            drawBorder: true
                        },
                        ticks: { color: colors.text, font: { size: 11 }, callback: (val) => new Intl.NumberFormat('es-PE', {maximumFractionDigits: 0}).format(val) }
                    },
                    x: { 
                        display: true, // Always show X axis
                        grid: { 
                            display: true, // Force grid display for consistency
                            color: colors.grid,
                            drawBorder: true
                        },
                        ticks: { color: colors.text, font: { size: 11 } }
                    }
                }
            },
            plugins: [{
                id: 'valueLabel',
                afterDatasetsDraw(chart) {
                    const {ctx} = chart;
                    const dataset = chart.data.datasets[0];
                    const meta = chart.getDatasetMeta(0);
                    ctx.save();
                    ctx.fillStyle = colors.text;
                    ctx.textAlign = 'center';
                    ctx.font = '10px system-ui';
                    meta.data.forEach((bar, i) => {
                        const val = dataset.data[i] || 0;
                        if (val > 0) {
                            const text = new Intl.NumberFormat('es-PE', {maximumFractionDigits: 0}).format(val);
                            ctx.fillText(text, bar.x, bar.y - 6);
                        }
                    });
                    ctx.restore();
                }
            }]
        });
    }

    const formatCurrency = (value, currency) => {
        const symbol = currency === 'soles' ? 'S/ ' : 'US$ ';
        return symbol + new Intl.NumberFormat('es-PE', { style: 'decimal', maximumFractionDigits: 2 }).format(value || 0);
    };

    // 2. Prima Neta Mensual (line chart)
    function initIncomeDayChart(currency = 'soles') {
        const ctxIncome = document.getElementById('incomeDayChart');
        if (!ctxIncome) return;

        const dailyLabels = data.dailyLabels || data.months || ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
        const dailyIncome = data.dailyIncome || data.totals || new Array(dailyLabels.length).fill(0);

        const chartData = currency === 'soles' ? dailyIncome : dailyIncome.map(v => v / 3.7);
        const totalValue = chartData.reduce((acc, curr) => acc + (Number(curr) || 0), 0);
        
        const gradient = ctxIncome.getContext('2d').createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(59, 130, 246, 0.4)');
        gradient.addColorStop(1, 'rgba(59, 130, 246, 0)');

        if (incomeDayChart) incomeDayChart.destroy();

        incomeDayChart = new Chart(ctxIncome, {
            type: 'line',
            data: {
                labels: dailyLabels,
                datasets: [{
                    label: 'Prima Neta',
                    data: chartData,
                    borderColor: '#3b82f6',
                    borderWidth: 3,
                    fill: true,
                    backgroundColor: gradient,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: '#3b82f6',
                    pointHoverBorderColor: '#fff',
                    pointHoverBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: colors.isDark ? '#1e293b' : '#fff',
                        titleColor: colors.isDark ? '#f8fafc' : '#1e293b',
                        bodyColor: colors.isDark ? '#cbd5e1' : '#64748b',
                        borderColor: 'rgba(59, 130, 246, 0.3)',
                        borderWidth: 1,
                        callbacks: {
                            label: function(context) {
                                const symbol = currency === 'soles' ? 'S/ ' : 'US$ ';
                                return symbol + new Intl.NumberFormat('es-PE', { style: 'decimal', maximumFractionDigits: 2 }).format(context.parsed.y);
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        display: true, // Always show Y axis
                        grid: { 
                            color: colors.grid, 
                            drawBorder: true,
                            borderDash: [2, 4] 
                        },
                        ticks: { 
                            color: colors.text, 
                            font: { size: 10 },
                            callback: (val) => new Intl.NumberFormat('es-PE', {maximumFractionDigits: 0}).format(val)
                        }
                    },
                    x: {
                        display: true, // Always show X axis
                        grid: { 
                            color: colors.grid,
                            drawBorder: true
                        },
                        ticks: { 
                            color: colors.text, 
                            font: { size: 10 }, 
                            maxRotation: 0,
                            autoSkip: true,
                            maxTicksLimit: 10
                        }
                    }
                }
            }
        });

        const totalLabel = document.getElementById('dailyTotalLabel');
        if (totalLabel) {
            totalLabel.innerText = formatCurrency(totalValue, currency);
        }
    }

    // Currency Switcher Logic
    document.querySelectorAll('.currency-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const currency = e.target.getAttribute('data-currency');
            document.querySelectorAll('.currency-btn').forEach(b => {
                b.classList.remove('active');
                b.classList.add('text-muted');
            });
            e.target.classList.add('active');
            e.target.classList.remove('text-muted');
            
            // Update monthly premium chart
            initIncomeDayChart(currency);
        });
    });

    document.querySelectorAll('.prod-currency-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const currency = e.target.getAttribute('data-currency');
            document.querySelectorAll('.prod-currency-btn').forEach(b => {
                b.classList.remove('active');
                b.classList.add('text-muted');
            });
            e.target.classList.add('active');
            e.target.classList.remove('text-muted');
            
            // Update Production Chart
            initProductionChart(currency);
        });
    });

    // Initial load
    initProductionChart();
    initIncomeDayChart();

    // 3. Doughnut Chart: Distribución
    const ctxDistribution = document.getElementById('distributionChart');
    if (ctxDistribution) {
        new Chart(ctxDistribution, {
            type: 'doughnut',
            data: {
                labels: ['Vigentes', 'Por Renovar'],
                datasets: [{
                    data: [data.activePolicies || 1, data.pendingRenewals || 0],
                    backgroundColor: ['#3b82f6', '#f59e0b'],
                    borderWidth: 0,
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '80%',
                plugins: {
                    legend: { 
                        position: 'bottom', 
                        labels: { 
                            color: colors.text,
                            usePointStyle: true, 
                            padding: 20,
                            font: { size: 11 }
                        } 
                    }
                }
            }
        });
    }
});
