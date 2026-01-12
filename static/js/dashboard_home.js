document.addEventListener('DOMContentLoaded', () => {
    const data = window.dashboardData || {};

    // Line Chart: Producción
    const ctxProduction = document.getElementById('productionChart');
    if (ctxProduction && data.months && data.totals) {
        new Chart(ctxProduction.getContext('2d'), {
            type: 'line',
            data: {
                labels: data.months,
                datasets: [{
                    label: 'Producción ($)',
                    data: data.totals,
                    borderColor: '#399AD6',
                    backgroundColor: 'rgba(57, 154, 214, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#FFFFFF',
                    pointBorderColor: '#399AD6',
                    pointBorderWidth: 2
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
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(context.parsed.y);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    y: { 
                        beginAtZero: true, 
                        grid: { borderDash: [2, 4], color: '#f0f0f0' },
                        ticks: { font: { size: 11 } }
                    },
                    x: { 
                        grid: { display: false },
                        ticks: { font: { size: 11 } }
                    }
                }
            }
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
