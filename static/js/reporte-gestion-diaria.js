function reporteGestionDiariaInit() {
    const form = document.getElementById('formReporteGestionDiaria');
    const tbody = document.getElementById('tbodyReporteGestionDiaria');
    const info = document.getElementById('gestionDiariaInfo');
    const btnExcel = document.getElementById('btnExportGestionDiariaExcel');
    const btnPdf = document.getElementById('btnExportGestionDiariaPdf');
    const btnClear = document.getElementById('btnClearGestionDiaria');

    if (!form || !tbody) return;

    function fmtMoney(val) {
        const num = parseFloat(val);
        if (isNaN(num)) return val === null || val === undefined ? '–' : String(val);
        return num.toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function fmtFecha(val) {
        if (!val) return '–';
        return String(val).substring(0, 10);
    }

    function fmtHora(val) {
        if (!val) return '–';
        const t = String(val).replace('T', ' ');
        return t.length >= 19 ? t.substring(11, 19) : t;
    }

    function estadoBadge(estado) {
        const map = {
            'ACTIVO': 'success',
            'PENDIENTE': 'warning',
            'RENOVADA': 'info',
            'VENCIDA': 'secondary',
            'ANULADA': 'danger',
        };
        const color = map[String(estado || '').toUpperCase()] || 'secondary';
        return `<span class="badge bg-${color}">${estado || '–'}</span>`;
    }

    function buildPayload() {
        const fd = new FormData(form);
        const payload = {};
        for (const [k, v] of fd.entries()) {
            const val = (v || '').toString().trim();
            if (val) payload[k] = val;
        }
        return payload;
    }

    function buildQuery() {
        const payload = buildPayload();
        const params = new URLSearchParams();
        Object.keys(payload).forEach((k) => params.append(k, payload[k]));
        return params.toString();
    }

    function renderRows(rows) {
        if (!rows || rows.length === 0) {
            tbody.innerHTML = `<tr><td colspan="14" class="text-center py-4 text-muted">No se encontraron resultados</td></tr>`;
            if (info) info.textContent = 'Mostrando 0 de 0';
            return;
        }

        const html = rows.map((r, idx) => {
            return `<tr>
                <td class="text-muted small">${idx + 1}</td>
                <td><strong>${r.poliza || r.contrato_nro || r.nro || '–'}</strong></td>
                <td><span class="badge bg-light text-dark border">${r.recibo || '–'}</span></td>
                <td>${r.cliente || '–'}</td>
                <td>${r.cia || '–'}</td>
                <td><span class="badge bg-light text-dark border">${r.ramo || '–'}</span></td>
                <td>${r.moneda || '–'}</td>
                <td class="text-end">${r.prima_total != null && r.prima_total !== '' ? fmtMoney(r.prima_total) : '–'}</td>
                <td>${fmtFecha(r.vig_desde)}</td>
                <td>${fmtFecha(r.vig_hasta)}</td>
                <td>${r.ejecutivo || '–'}</td>
                <td>${estadoBadge(r.estado)}</td>
                <td class="small">${r.usuario_registro || '–'}</td>
                <td class="small text-muted">${fmtHora(r.creado_en)}</td>
            </tr>`;
        }).join('');

        tbody.innerHTML = html;
        if (info) info.textContent = `Mostrando ${rows.length} registro(s)`;
    }

    function loadReporte() {
        tbody.innerHTML = `<tr><td colspan="14" class="text-center py-4 text-muted">Cargando...</td></tr>`;
        if (info) info.textContent = '';
        fetch('/api/reporte-gestion-diaria', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify(buildPayload()),
        })
            .then(r => r.json())
            .then(data => {
                if (!data.ok) {
                    tbody.innerHTML = `<tr><td colspan="14" class="text-center py-4 text-danger">${data.error || 'Error al cargar'}</td></tr>`;
                    return;
                }
                renderRows(data.rows || []);
            })
            .catch(() => {
                tbody.innerHTML = `<tr><td colspan="14" class="text-center py-4 text-danger">Error de conexión</td></tr>`;
            });
    }

    function descargar(url, btn) {
        const orig = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Generando...';
        fetch(url)
            .then(res => {
                if (!res.ok) throw new Error('Error al generar el archivo');
                const cd = res.headers.get('Content-Disposition') || '';
                const match = cd.match(/filename[^;=\n]*=["']?([^"';\n]+)["']?/i);
                const filename = match ? decodeURIComponent(match[1].trim()) : 'reporte';
                return res.blob().then(blob => ({ blob, filename }));
            })
            .then(({ blob, filename }) => {
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(a.href);
            })
            .finally(() => {
                btn.disabled = false;
                btn.innerHTML = orig;
            });
    }

    form.addEventListener('submit', function (ev) {
        ev.preventDefault();
        loadReporte();
    });

    if (btnExcel) {
        btnExcel.addEventListener('click', function () {
            const q = buildQuery();
            const url = '/api/reporte-gestion-diaria/export/excel' + (q ? `?${q}` : '');
            descargar(url, btnExcel);
        });
    }

    if (btnPdf) {
        btnPdf.addEventListener('click', function () {
            const q = buildQuery();
            const url = '/api/reporte-gestion-diaria/export/pdf' + (q ? `?${q}` : '');
            descargar(url, btnPdf);
        });
    }

    if (btnClear) {
        btnClear.addEventListener('click', function () {
            form.reset();
            tbody.innerHTML = `<tr><td colspan="14" class="text-center py-4 text-muted">Use los filtros y pulse Buscar.</td></tr>`;
            if (info) info.textContent = '';
        });
    }
}

document.addEventListener('DOMContentLoaded', reporteGestionDiariaInit);
