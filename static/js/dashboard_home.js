document.addEventListener('DOMContentLoaded', () => {
    const data = window.dashboardData || {};

    const ctxProduction = document.getElementById('productionChart');
    if (ctxProduction && data.months && data.totals) {
        const valueLabelPlugin = {
            id: 'valueLabel',
            afterDatasetsDraw(chart) {
                const {ctx} = chart;
                const dataset = chart.data.datasets[0];
                const meta = chart.getDatasetMeta(0);
                ctx.save();
                ctx.fillStyle = '#333';
                ctx.textAlign = 'center';
                ctx.font = '12px system-ui, -apple-system, Segoe UI, Roboto';
                meta.data.forEach((bar, i) => {
                    const val = dataset.data[i] || 0;
                    const text = new Intl.NumberFormat('es-PE', {maximumFractionDigits: 0}).format(val);
                    ctx.fillText(text, bar.x, bar.y - 6);
                });
                ctx.restore();
            }
        };

        new Chart(ctxProduction.getContext('2d'), {
            type: 'bar',
            data: {
                labels: data.months,
                datasets: [{
                    label: 'Producción',
                    data: data.totals,
                    backgroundColor: (function(){ const n = data.totals.length || 0; return Array.from({length:n}, (_,i)=>`hsl(${(i*360)/Math.max(n,1)},70%,65%)`); })(),
                    borderColor: (function(){ const n = data.totals.length || 0; return Array.from({length:n}, (_,i)=>`hsl(${(i*360)/Math.max(n,1)},70%,45%)`); })(),
                    borderWidth: 1,
                    borderRadius: 6
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
                                return new Intl.NumberFormat('es-PE', { style: 'decimal', maximumFractionDigits: 2 }).format(context.parsed.y);
                            }
                        }
                    }
                },
                scales: {
                    y: { 
                        beginAtZero: true, 
                        grid: { borderDash: [2, 4], color: '#f0f0f0' },
                        ticks: { font: { size: 11 }, callback: (val) => new Intl.NumberFormat('es-PE', {maximumFractionDigits: 0}).format(val) }
                    },
                    x: { 
                        grid: { display: false },
                        ticks: { font: { size: 11 } }
                    }
                }
            },
            plugins: [valueLabelPlugin]
        });
    }

    // Doughnut Chart: Distribución
    const ctxDistribution = document.getElementById('distributionChart');
    if (ctxDistribution) {
        const active = data.activePolicies || 0;
        const renewals = data.pendingRenewals || 0;
        // Safe fallback if data is weird
        const safeActive = active > 0 ? active : 1;
        
        new Chart(ctxDistribution.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Vigentes', 'Por Renovar'],
                datasets: [{
                    data: [safeActive, renewals],
                    backgroundColor: ['#399AD6', '#ffc107'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '75%',
                plugins: {
                    legend: { position: 'bottom', labels: { usePointStyle: true, padding: 20 } }
                }
            }
        });
    }
});
