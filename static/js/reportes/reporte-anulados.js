document.addEventListener('DOMContentLoaded', function () {
    const treeEl = document.getElementById('anuladosTree');
    const kpiRow = document.getElementById('kpiRow');
    const searchInput = document.getElementById('searchInput');
    const desdeInput = document.getElementById('desdeInput');
    const hastaInput = document.getElementById('hastaInput');
    const btnBuscar = document.getElementById('btnBuscar');
    const btnExpandirTodo = document.getElementById('btnExpandirTodo');
    const btnColapsarTodo = document.getElementById('btnColapsarTodo');
    const pageSizeSelect = document.getElementById('pageSizeSelect');
    const paginationEl = document.getElementById('pagination');
    const pageInfoEl = document.getElementById('pageInfo');

    let allData = [];
    let polizaIds = [];
    let currentPage = 1;
    let pageSize = pageSizeSelect ? parseInt(pageSizeSelect.value, 10) : 10;

    const ESTADOS = {
        'POLIZA ANULADA':      { clase: 'poliza',  icono: 'bi-x-octagon-fill' },
        'PRIMA ANULADA':       { clase: 'prima',   icono: 'bi-exclamation-triangle-fill' },
        'CUOTA ANULADA':       { clase: 'cuota',   icono: 'bi-dash-circle-fill' },
        'CON CUOTAS ANULADAS': { clase: 'parcial', icono: 'bi-info-circle-fill' }
    };

    fetchData();

    btnBuscar.addEventListener('click', () => fetchData());
    searchInput.addEventListener('keydown', e => { if (e.key === 'Enter') fetchData(); });
    btnExpandirTodo.addEventListener('click', () => toggleAll(true));
    btnColapsarTodo.addEventListener('click', () => toggleAll(false));

    async function fetchData() {
        treeEl.innerHTML = `<div class="anulados-estado"><i class="bi-hourglass-split"></i>Cargando...</div>`;
        const qs = new URLSearchParams({
            search: searchInput.value.trim(),
            desde: desdeInput.value,
            hasta: hastaInput.value
        });
        const url = `/api/reportes/anulados?${qs.toString()}`;

        console.group('%c[Reporte Anulados] diagnostico', 'color:#2a78d6;font-weight:bold;');
        console.log('URL llamada:', url);
        console.log('Filtros en pantalla -> search:', searchInput.value, '| desde:', desdeInput.value, '| hasta:', hastaInput.value);

        try {
            const resp = await fetch(url);
            const json = await resp.json();
            const d = json.debug || {};

            console.log('HTTP status:', resp.status, resp.ok ? '(OK)' : '(FALLO)');
            console.log('Parametros que recibio el backend:', d.params_recibidos);
            console.log('Conexion real de la BD (host/usuario/schema):', d.conexion);
            console.log('¿Existe el SP en esa BD?:', d.sp_existe);
            console.log('Conteo directo (sin pasar por el SP) polizas.anulado=1:', d.polizas_anulado_1);
            console.log('Conteo directo polizas.prima_anulada=1:', d.polizas_prima_anulada_1);
            console.log('Conteo directo cuotas.activo=0:', d.cuotas_activo_0);
            console.log('Result sets devueltos por el CALL:', d.result_sets, '| Filas:', d.row_count);
            if (json.db_error) {
                console.error('ERROR SQL/Python reportado por el backend:', json.db_error);
            } else {
                console.log('db_error: (ninguno)');
            }
            if (Array.isArray(json.data) && json.data.length) {
                console.table(json.data);
            } else {
                console.warn('json.data esta vacio. Compara los conteos directos de arriba: si son > 0 pero row_count del SP es 0, el problema esta en el WHERE del SP contra esos datos puntuales.');
            }
            console.groupEnd();

            if (!resp.ok) throw new Error((json && json.error) || `Error HTTP ${resp.status}`);
            allData = json.data || [];
            polizaIds = allData.filter(r => r.tipo === 'POLIZA').map(p => p.poliza_id);
            currentPage = 1;
            renderKpis();
            renderPage();
        } catch (err) {
            console.error('[Reporte Anulados] Error cargando reporte:', err);
            console.groupEnd();
            treeEl.innerHTML = `<div class="anulados-estado text-danger"><i class="bi-exclamation-octagon"></i>Error cargando datos (ver consola del navegador, F12)</div>`;
        }
    }

    function escapeHtml(str) {
        return (str || '').toString().replace(/[&<>"]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m]));
    }

    function fmtMoneda(row) {
        const val = row.importe;
        if (val === null || val === undefined || val === '') return '-';
        const num = Number(val);
        if (isNaN(num)) return val;
        return `${row.moneda || ''} ${num.toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    function estadoBadge(tipoAnulacion) {
        const info = ESTADOS[tipoAnulacion] || { clase: 'parcial', icono: 'bi-question-circle-fill' };
        return `<span class="estado-badge estado-badge--${info.clase}"><i class="bi ${info.icono}"></i>${escapeHtml(tipoAnulacion || '-')}</span>`;
    }

    // ── KPIs ─────────────────────────────────────────────────────────────────
    function renderKpis() {
        const polizas = allData.filter(r => r.tipo === 'POLIZA');
        const cuotas = allData.filter(r => r.tipo === 'CUOTA');
        const nPolizaAnulada = polizas.filter(p => p.tipo_anulacion === 'POLIZA ANULADA').length;
        const nPrimaAnulada = polizas.filter(p => p.tipo_anulacion === 'PRIMA ANULADA').length;
        const nCuotas = cuotas.length;
        const totalAnulado = polizas
            .filter(p => p.tipo_anulacion === 'POLIZA ANULADA' || p.tipo_anulacion === 'PRIMA ANULADA')
            .reduce((acc, p) => acc + (Number(p.importe) || 0), 0);

        kpiRow.innerHTML = `
            <div class="kpi-tile kpi-tile--critical">
                <div class="kpi-tile__label">Pólizas anuladas</div>
                <div class="kpi-tile__value">${nPolizaAnulada}</div>
            </div>
            <div class="kpi-tile kpi-tile--warning">
                <div class="kpi-tile__label">Primas anuladas</div>
                <div class="kpi-tile__value">${nPrimaAnulada}</div>
            </div>
            <div class="kpi-tile kpi-tile--serious">
                <div class="kpi-tile__label">Cuotas anuladas</div>
                <div class="kpi-tile__value">${nCuotas}</div>
            </div>
            <div class="kpi-tile">
                <div class="kpi-tile__label">Total anulado (pólizas + primas)</div>
                <div class="kpi-tile__value">${totalAnulado.toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
            </div>`;
    }

    // ── Paginación (por póliza, cada una con sus cuotas) ────────────────────
    function getPageData() {
        const total = polizaIds.length;
        const start = Math.max(0, (currentPage - 1) * pageSize);
        const end = Math.min(start + pageSize, total);
        const idsInPage = new Set(polizaIds.slice(start, end));
        return {
            polizas: allData.filter(r => r.tipo === 'POLIZA' && idsInPage.has(r.poliza_id)),
            cuotasByPadre: buildCuotasByPadre(idsInPage),
            total, start, end
        };
    }

    function buildCuotasByPadre(idsInPage) {
        const map = {};
        allData.forEach(r => {
            if (r.tipo !== 'CUOTA' || !idsInPage.has(r.poliza_padre_id)) return;
            (map[r.poliza_padre_id] = map[r.poliza_padre_id] || []).push(r);
        });
        return map;
    }

    function renderPage() {
        const { polizas, cuotasByPadre, total, start, end } = getPageData();
        renderTree(polizas, cuotasByPadre);
        renderPagination(total);
        pageInfoEl.textContent = total ? `Mostrando ${start + 1}–${end} de ${total} pólizas/recibos anulados` : '';
    }

    // ── Árbol de tarjetas ────────────────────────────────────────────────────
    function renderTree(polizas, cuotasByPadre) {
        if (!polizas.length) {
            treeEl.innerHTML = `<div class="anulados-estado"><i class="bi-inbox"></i>No se encontraron registros anulados</div>`;
            return;
        }

        treeEl.innerHTML = polizas.map(p => {
            const info = ESTADOS[p.tipo_anulacion] || { clase: 'parcial' };
            const hijos = cuotasByPadre[p.poliza_id] || [];

            const cuotasHtml = hijos.length
                ? hijos.map(c => `
                    <div class="anulado-cuota-item">
                        ${estadoBadge(c.tipo_anulacion)}
                        <span class="anulado-cuota-item__cupon">Cupón ${escapeHtml(c.recibo)}</span>
                        <span class="anulado-cuota-item__meta">${escapeHtml(c.motivo) || 'Sin motivo registrado'} · ${escapeHtml(c.usuario) || '-'} · ${escapeHtml(c.fecha_anulacion) || '-'}</span>
                        <span class="anulado-cuota-item__amount">${fmtMoneda(c)}</span>
                    </div>`).join('')
                : `<div class="anulados-cuotas-empty">Sin cuotas anuladas para este registro.</div>`;

            return `
            <div class="anulado-card" data-estado="${info.clase}">
                <button type="button" class="anulado-card__header" data-toggle-card>
                    <i class="bi bi-chevron-right anulado-card__chevron"></i>
                    <div class="anulado-card__main">
                        <div class="anulado-card__title-row">
                            ${estadoBadge(p.tipo_anulacion)}
                            <span class="anulado-card__poliza">Póliza ${escapeHtml(p.poliza)}</span>
                            <span class="anulado-card__recibo">Recibo ${escapeHtml(p.recibo)}</span>
                        </div>
                        <div class="anulado-card__meta">${escapeHtml(p.contratante) || '-'} · ${escapeHtml(p.compania) || '-'} · ${escapeHtml(p.ramo) || '-'}</div>
                    </div>
                    <span class="anulado-card__cuotas-count">${hijos.length} cuota${hijos.length === 1 ? '' : 's'} anulada${hijos.length === 1 ? '' : 's'}</span>
                    <div class="anulado-card__amount">${fmtMoneda(p)}<small>Importe de la prima</small></div>
                </button>
                <div class="anulado-card__body">
                    <dl class="anulado-card__detalle">
                        <div><dt>Motivo</dt><dd>${escapeHtml(p.motivo) || 'Sin motivo registrado'}</dd></div>
                        <div><dt>Usuario</dt><dd>${escapeHtml(p.usuario) || '-'}</dd></div>
                        <div><dt>Fecha de anulación</dt><dd>${escapeHtml(p.fecha_anulacion) || '-'}</dd></div>
                    </dl>
                    <div class="anulado-cuotas">${cuotasHtml}</div>
                </div>
            </div>`;
        }).join('');

        treeEl.querySelectorAll('[data-toggle-card]').forEach(btn => {
            btn.addEventListener('click', function () {
                this.closest('.anulado-card').classList.toggle('is-open');
            });
        });
    }

    function toggleAll(open) {
        treeEl.querySelectorAll('.anulado-card').forEach(card => card.classList.toggle('is-open', open));
    }

    // ── Paginación ───────────────────────────────────────────────────────────
    function renderPagination(total) {
        const pages = Math.max(1, Math.ceil(total / pageSize));
        let html = `<li class="page-item${currentPage <= 1 ? ' disabled' : ''}"><a class="page-link" href="#" data-action="prev">&laquo;</a></li>`;
        for (let i = 1; i <= pages; i++) {
            html += `<li class="page-item${i === currentPage ? ' active' : ''}"><a class="page-link" href="#" data-page="${i}">${i}</a></li>`;
        }
        html += `<li class="page-item${currentPage >= pages ? ' disabled' : ''}"><a class="page-link" href="#" data-action="next">&raquo;</a></li>`;
        paginationEl.innerHTML = html;

        paginationEl.querySelectorAll('a.page-link').forEach(a => {
            a.addEventListener('click', function (e) {
                e.preventDefault();
                const act = this.dataset.action;
                const num = parseInt(this.dataset.page || '0', 10);
                if (act === 'prev') currentPage = Math.max(1, currentPage - 1);
                else if (act === 'next') currentPage = Math.min(pages, currentPage + 1);
                else if (num) currentPage = num;
                renderPage();
            });
        });
    }

    pageSizeSelect.addEventListener('change', function () {
        pageSize = parseInt(this.value, 10) || 10;
        currentPage = 1;
        renderPage();
    });
});
