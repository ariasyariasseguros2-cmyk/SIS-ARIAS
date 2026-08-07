document.addEventListener('DOMContentLoaded', () => {
    const data = window.dashboardData || {};

    const chartErrorText = document.getElementById('chartErrorText');
    if (chartErrorText && data.error) {
        chartErrorText.innerText = `Error cargando gráfico: ${data.error}`;
        chartErrorText.style.display = 'block';
    }

    const getThemeColors = () => {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        return {
            isDark: isDark,
            grid: isDark ? 'rgba(148, 163, 184, 0.12)' : '#e5e7eb',
            text: isDark ? '#94a3b8' : '#6b7280',
            accent: '#2563eb',
            accentGlow: 'rgba(59, 130, 246, 0.5)'
        };
    };

    let colors = getThemeColors();

    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.attributeName === 'data-theme') {
                colors = getThemeColors();
                initIncomeDayChart();
            }
        });
    });
    observer.observe(document.documentElement, { attributes: true });

    let incomeDayChart;

    const formatCurrency = (value, currency) => {
        const symbol = currency === 'soles' ? 'S/. ' : 'US$ ';
        return symbol + new Intl.NumberFormat('es-PE', { style: 'decimal', maximumFractionDigits: 2 }).format(value || 0);
    };

    const formatShort = (value) => {
        if (value >= 1000) {
            return (value / 1000).toFixed(0) + 'k';
        }
        return String(value);
    };

    function initIncomeDayChart(currency = 'soles') {
        const ctxIncome = document.getElementById('incomeDayChart');
        if (!ctxIncome) return;

        const dailyLabels = (data.months && data.months.length) ? data.months : [];

        const chartDataPrima = currency === 'soles'
            ? (data.totals_prima_soles || [])
            : (data.totals_prima_usd || []);

        const chartDataComision = currency === 'soles'
            ? (data.totals_comision_soles || [])
            : (data.totals_comision_usd || []);

        const chartDataPrimaTotal = currency === 'soles'
            ? (data.totals_prima_total_soles || [])
            : (data.totals_prima_total_usd || []);

        while (chartDataPrimaTotal.length < dailyLabels.length) {
            chartDataPrimaTotal.push(0);
        }

        const totalPrimaNetaValue = chartDataPrima.reduce((acc, curr) => acc + (Number(curr) || 0), 0);
        const totalPrimaTotalValue = chartDataPrimaTotal.reduce((acc, curr) => acc + (Number(curr) || 0), 0);
        const totalComisionValue = chartDataComision.reduce((acc, curr) => acc + (Number(curr) || 0), 0);

        const fallbackPrimaTotal = totalPrimaNetaValue + (totalPrimaNetaValue * 0.215);
        const displayPrimaTotal = totalPrimaTotalValue > 0 ? totalPrimaTotalValue : fallbackPrimaTotal;

        const blueGradient = ctxIncome.getContext('2d').createLinearGradient(0, 0, 0, 400);
        if (colors.isDark) {
            blueGradient.addColorStop(0, '#3b82f6');
            blueGradient.addColorStop(0.5, '#2563eb');
            blueGradient.addColorStop(1, '#1d4ed8');
        } else {
            blueGradient.addColorStop(0, '#3b82f6');
            blueGradient.addColorStop(0.6, '#2563eb');
            blueGradient.addColorStop(1, '#1e40af');
        }

        const purpleGradient = ctxIncome.getContext('2d').createLinearGradient(0, 0, 0, 400);
        purpleGradient.addColorStop(0, '#8b5cf6');
        purpleGradient.addColorStop(1, '#7c3aed');

        if (incomeDayChart) incomeDayChart.destroy();

        incomeDayChart = new Chart(ctxIncome, {
            type: 'bar',
            data: {
                labels: dailyLabels,
                datasets: [
                    {
                        label: 'Prima Neta',
                        data: chartDataPrima,
                        backgroundColor: blueGradient,
                        borderColor: colors.isDark ? 'transparent' : '#1d4ed8',
                        borderWidth: 0,
                        borderRadius: 4,
                        borderSkipped: false,
                        barPercentage: 0.72,
                        categoryPercentage: 0.72,
                        order: 1
                    },
                    {
                        label: 'Comisión',
                        data: chartDataComision,
                        backgroundColor: purpleGradient,
                        borderColor: colors.isDark ? 'transparent' : '#7c3aed',
                        borderWidth: 0,
                        borderRadius: 4,
                        borderSkipped: false,
                        barPercentage: 0.72,
                        categoryPercentage: 0.72,
                        order: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: { top: 8, right: 16, left: 4, bottom: 0 }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: colors.isDark ? '#1e293b' : '#ffffff',
                        titleColor: colors.isDark ? '#f8fafc' : '#111827',
                        bodyColor: colors.isDark ? '#cbd5e1' : '#6b7280',
                        borderColor: colors.isDark ? 'rgba(148, 163, 184, 0.2)' : 'rgba(0,0,0,0.08)',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 10,
                        titleFont: { size: 13, weight: '700' },
                        bodyFont: { size: 12 },
                        callbacks: {
                            label: function(context) {
                                const symbol = currency === 'soles' ? 'S/. ' : 'US$ ';
                                return ` ${context.dataset.label}: ${symbol}${new Intl.NumberFormat('es-PE', { style: 'decimal', maximumFractionDigits: 2 }).format(context.parsed.y)}`;
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
                            drawBorder: false,
                            borderDash: [3, 5],
                            lineWidth: 1
                        },
                        ticks: {
                            color: colors.text,
                            font: { size: 11, weight: '500' },
                            padding: 10,
                            callback: (val) => formatShort(val)
                        }
                    },
                    x: {
                        display: true,
                        grid: { display: false, drawBorder: false },
                        ticks: {
                            color: colors.text,
                            font: { size: 11, weight: '500' },
                            padding: 10
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
            primaTotalLabel.innerText = `Prima Comercial c/IGV: ${formatCurrency(displayPrimaTotal, currency)}`;
        }

        const comisionLabel = document.getElementById('totalComisionLabel');
        if (comisionLabel) {
            comisionLabel.innerText = `Comisión: ${formatCurrency(totalComisionValue, currency)}`;
        }
    }

    document.querySelectorAll('.currency-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const currency = e.target.getAttribute('data-currency');
            document.querySelectorAll('.currency-btn').forEach(b => {
                b.classList.remove('active');
            });
            e.target.classList.add('active');
            initIncomeDayChart(currency);
        });
    });

    initIncomeDayChart();

    const dist = data.distribution || {
        generales: { vigentes: 0, renovar: 0 },
        soat:      { vigentes: 0, renovar: 0 },
        personales:{ vigentes: 0, renovar: 0 }
    };

    function makeGroupDonut(canvasId, bucket, color) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        const b   = dist[bucket] || {};
        const vig = b.vigentes || 0;
        const ren = b.renovar  || 0;
        const total = vig + ren;
        const hasData = total > 0;

        const dataVig = hasData ? vig : 1;
        const dataRen = hasData ? ren : 0;

        const ring = hasData ? color : '#e5e7eb';
        const ringRen = hasData ? '#f59e0b' : '#e5e7eb';

        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Vigentes', 'Por renovar'],
                datasets: [{
                    data: hasData ? [dataVig, dataRen] : [1, 0],
                    backgroundColor: hasData ? [ring, ringRen] : ['#e5e7eb', '#e5e7eb'],
                    borderWidth: 0,
                    hoverOffset: 6,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '78%',
                circumference: 360,
                animation: {
                    animateRotate: true,
                    animateScale: true,
                    duration: 800,
                    easing: 'easeOutQuart'
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: colors.isDark ? '#1e293b' : '#ffffff',
                        titleColor: colors.isDark ? '#f8fafc' : '#111827',
                        bodyColor: colors.isDark ? '#cbd5e1' : '#6b7280',
                        borderColor: colors.isDark ? 'rgba(148, 163, 184, 0.2)' : 'rgba(0,0,0,0.08)',
                        borderWidth: 1,
                        padding: 10,
                        cornerRadius: 8,
                        callbacks: {
                            label: c => hasData ? ` ${c.label}: ${c.parsed}` : ' Sin datos'
                        }
                    }
                }
            }
        });
    }
    makeGroupDonut('chartGenerales', 'generales', '#3b82f6');
    makeGroupDonut('chartSoat',      'soat',       '#f59e0b');
    makeGroupDonut('chartPersonales','personales', '#10b981');

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
                        <tr class="renovar-row" data-poliza-id="${r.idPoliza}" title="Ver esta póliza">
                            <td>${escapeHtml(r.poliza)}</td>
                            <td>${escapeHtml(r.recibo)}</td>
                            <td>${escapeHtml(r.vig_desde)}</td>
                            <td>${escapeHtml(r.vig_hasta)}</td>
                            <td class="renovar-row-action text-end"><i class="bi-box-arrow-up-right me-1"></i>Ver</td>
                        </tr>
                    `).join('');
                    modalTbody.querySelectorAll('.renovar-row').forEach(tr => {
                        tr.addEventListener('click', () => {
                            window.location.href = `/notificaciones/poliza/${tr.dataset.polizaId}/abrir`;
                        });
                    });
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

    document.querySelectorAll('.group-toggle').forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            if (window.innerWidth <= 991) {
                e.preventDefault();
                e.stopPropagation();
                const group = this.closest('.nav-group');
                if (group) {
                    group.classList.toggle('open');
                }
            }
        });
    });
});
