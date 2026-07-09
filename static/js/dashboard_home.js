document.addEventListener('DOMContentLoaded', () => {
    const data = window.dashboardData || {};

    const chartErrorText = document.getElementById('chartErrorText');
    if (chartErrorText && data.error) {
        chartErrorText.innerText = `Error cargando gráfico: ${data.error}`;
        chartErrorText.style.display = 'block';
    }

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
                initIncomeDayChart();
            }
        });
    });
    observer.observe(document.documentElement, { attributes: true });

    // Store chart instances to update them
    let incomeDayChart;

    const formatCurrency = (value, currency) => {
        const symbol = currency === 'soles' ? 'S/. ' : 'US$ ';
        return symbol + new Intl.NumberFormat('es-PE', { style: 'decimal', maximumFractionDigits: 2 }).format(value || 0);
    };

    // Prima Neta + Comisiones Mensuales (barras agrupadas por color)
    function initIncomeDayChart(currency = 'soles') {
        const ctxIncome = document.getElementById('incomeDayChart');
        if (!ctxIncome) return;

        const dailyLabels = data.months || ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
        
        // Use data from DB instead of client-side conversion
        const chartDataPrima = currency === 'soles' 
            ? (data.totals_prima_soles || new Array(dailyLabels.length).fill(0))
            : (data.totals_prima_usd || new Array(dailyLabels.length).fill(0));

        const chartDataComision = currency === 'soles'
            ? (data.totals_comision_soles || new Array(dailyLabels.length).fill(0))
            : (data.totals_comision_usd || new Array(dailyLabels.length).fill(0));

        const chartDataPrimaTotal = currency === 'soles'
            ? (data.totals_prima_total_soles || new Array(dailyLabels.length).fill(0))
            : (data.totals_prima_total_usd || new Array(dailyLabels.length).fill(0));
            
        const totalPrimaNetaValue = chartDataPrima.reduce((acc, curr) => acc + (Number(curr) || 0), 0);
        const totalPrimaTotalValue = chartDataPrimaTotal.reduce((acc, curr) => acc + (Number(curr) || 0), 0);
        const totalComisionValue = chartDataComision.reduce((acc, curr) => acc + (Number(curr) || 0), 0);
        
        const gradient = ctxIncome.getContext('2d').createLinearGradient(0, 0, 0, 400);
        if (colors.isDark) {
            gradient.addColorStop(0, '#3b82f6');
            gradient.addColorStop(1, 'rgba(59, 130, 246, 0.1)');
        } else {
            gradient.addColorStop(0, '#399AD6');
            gradient.addColorStop(1, 'rgba(57, 154, 214, 0.1)');
        }

        const comisionGradient = ctxIncome.getContext('2d').createLinearGradient(0, 0, 0, 400);
        if (colors.isDark) {
            comisionGradient.addColorStop(0, '#10b981');
            comisionGradient.addColorStop(1, '#34d399');
        } else {
            comisionGradient.addColorStop(0, '#28a745');
            comisionGradient.addColorStop(1, '#5dd39e');
        }

        if (incomeDayChart) incomeDayChart.destroy();

        incomeDayChart = new Chart(ctxIncome, {
            type: 'bar',
            data: {
                labels: dailyLabels,
                datasets: [
                    {
                        label: 'Prima Neta',
                        data: chartDataPrima,
                        backgroundColor: gradient,
                        borderColor: colors.isDark ? 'transparent' : '#1F59A3',
                        borderWidth: 1,
                        borderRadius: 6,
                        barThickness: 16
                    },
                    {
                        label: 'Comisión',
                        data: chartDataComision,
                        backgroundColor: comisionGradient,
                        borderColor: colors.isDark ? 'transparent' : '#28a745',
                        borderWidth: 1,
                        borderRadius: 6,
                        barThickness: 16
                    }
                ]
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
                                const symbol = currency === 'soles' ? 'S/. ' : 'US$ ';
                                return `${context.dataset.label}: ${symbol}${new Intl.NumberFormat('es-PE', { style: 'decimal', maximumFractionDigits: 2 }).format(context.parsed.y)}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        display: true,
                        grid: {
                            color: colors.grid,
                            drawBorder: true,
                            borderDash: [2, 4]
                        },
                        ticks: {
                            color: colors.text,
                            font: { size: 11 },
                            callback: (val) => new Intl.NumberFormat('es-PE', {maximumFractionDigits: 0}).format(val)
                        }
                    },
                    x: {
                        display: true,
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: colors.text,
                            font: { size: 11 }
                        }
                    }
                }
            }
        });

        const primaNetaLabel = document.getElementById('totalPrimaNetaLabel');
        if (primaNetaLabel) {
            primaNetaLabel.innerText = `Prima Neta: ${formatCurrency(totalPrimaNetaValue, currency)}`;
        }

        const primaTotalLabel = document.getElementById('totalPrimaTotalLabel');
        if (primaTotalLabel) {
            primaTotalLabel.innerText = `Prima Comercial IGV: ${formatCurrency(totalPrimaTotalValue, currency)}`;
        }

        const comisionLabel = document.getElementById('totalComisionLabel');
        if (comisionLabel) {
            comisionLabel.innerText = `Comisión: ${formatCurrency(totalComisionValue, currency)}`;
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

    // Initial load
    initIncomeDayChart();

    // 3. Doughnut Charts: uno por grupo
    const dist = data.distribution || {};
    function makeGroupDonut(canvasId, bucket, color) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        const b   = dist[bucket] || {};
        const vig = b.vigentes || 0;
        const ren = b.renovar  || 0;
        const hasData = (vig + ren) > 0;
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Vigentes', 'Por renovar'],
                datasets: [{
                    data: hasData ? [vig, ren] : [1, 0],
                    backgroundColor: hasData ? [color, '#f59e0b'] : ['#e2e8f0', '#e2e8f0'],
                    borderWidth: 0,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '80%',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: c => hasData ? `${c.label}: ${c.parsed}` : 'Sin datos'
                        }
                    }
                }
            }
        });
    }
    makeGroupDonut('chartGenerales', 'generales', '#3b82f6');
    makeGroupDonut('chartSoat',      'soat',       '#f59e0b');
    makeGroupDonut('chartPersonales','personales', '#10b981');

    // 4. Modal: pólizas pendientes de renovación por grupo
    const modalRenovacionesEl = document.getElementById('modalRenovaciones');
    const modalRenovaciones = modalRenovacionesEl ? new bootstrap.Modal(modalRenovacionesEl) : null;
    const modalLoading = document.getElementById('modalRenovacionesLoading');
    const modalEmpty = document.getElementById('modalRenovacionesEmpty');
    const modalTabla = document.getElementById('modalRenovacionesTabla');
    const modalTbody = modalTabla ? modalTabla.querySelector('tbody') : null;
    const modalLabel = document.getElementById('modalRenovacionesLabel');

    document.querySelectorAll('.renovar-trigger').forEach(el => {
        el.addEventListener('click', () => {
            const bucket = el.getAttribute('data-bucket');
            if (!bucket || !modalRenovaciones) return;

            modalLabel.textContent = el.getAttribute('data-label') || '';
            modalLoading.classList.remove('d-none');
            modalEmpty.classList.add('d-none');
            modalTabla.classList.add('d-none');
            modalTbody.innerHTML = '';
            modalRenovaciones.show();

            fetch(`/dashboard/renovaciones/${encodeURIComponent(bucket)}`)
                .then(r => r.json())
                .then(res => {
                    modalLoading.classList.add('d-none');
                    const rows = (res && res.ok) ? (res.rows || []) : [];
                    if (rows.length === 0) {
                        modalEmpty.classList.remove('d-none');
                        return;
                    }
                    modalTbody.innerHTML = rows.map(r => `
                        <tr>
                            <td>${escapeHtml(r.poliza)}</td>
                            <td>${escapeHtml(r.recibo)}</td>
                            <td>${escapeHtml(r.vig_desde)}</td>
                            <td>${escapeHtml(r.vig_hasta)}</td>
                        </tr>
                    `).join('');
                    modalTabla.classList.remove('d-none');
                })
                .catch(() => {
                    modalLoading.classList.add('d-none');
                    modalEmpty.textContent = 'Error al cargar las pólizas pendientes.';
                    modalEmpty.classList.remove('d-none');
                });
        });
    });

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }
});
