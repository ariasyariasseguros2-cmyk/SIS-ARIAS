document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const tableBody = document.querySelector('#filesTable tbody');
    const pdfModal  = document.getElementById('pdfModal') ? new bootstrap.Modal(document.getElementById('pdfModal')) : null;
    const btnDownloadByContratante = document.getElementById('btnDownloadByContratante');
    const contratanteSelectModalEl = document.getElementById('contratanteSelectModal');
    const contratanteSelectModal = contratanteSelectModalEl ? new bootstrap.Modal(contratanteSelectModalEl) : null;
    const contratanteList = document.getElementById('contratanteList');
    const suggestionsEl = document.getElementById('contratanteSuggestions');
    const selectedClienteIdInput = document.getElementById('selectedClienteId');
    const pageSizeSelect = document.getElementById('pageSizeSelect');
    const paginationEl = document.getElementById('pagination');
    const pageInfoEl = document.getElementById('pageInfo');

    let debounceTimer;
    let suggestions = [];
    let activeSuggestion = -1;
    let lastSelectedName = '';
    let suggestTimer = null;
    let searchTimer = null;
    let fetchController = null;
    let allData = [];
    let groups = [];
    let currentPage = 1;
    let pageSize = pageSizeSelect ? parseInt(pageSizeSelect.value, 10) : 10;

    // ── Carga inicial ────────────────────────────────────────────────────────
    fetchFiles();

    // ── Búsqueda / autocomplete ──────────────────────────────────────────────
    searchInput.addEventListener('input', function() {
        const q = this.value;
        if (lastSelectedName && q !== lastSelectedName) {
            selectedClienteIdInput.value = '';
            lastSelectedName = '';
        }
        if (!q || q.trim().length < 1) {
            selectedClienteIdInput.value = '';
            lastSelectedName = '';
            hideSuggestions();
            hideBanner();
            fetchFiles('');
            return;
        }
        if (searchTimer) clearTimeout(searchTimer);
        searchTimer = setTimeout(() => fetchFiles(q.trim()), 250);
        if (suggestTimer) clearTimeout(suggestTimer);
        suggestTimer = setTimeout(() => handleAutocomplete(q), 200);
    });

    searchInput.addEventListener('keydown', function(e) {
        if (!suggestionsEl || suggestionsEl.classList.contains('d-none')) return;
        if (e.key === 'ArrowDown') {
            e.preventDefault(); activeSuggestion = Math.min(activeSuggestion + 1, suggestions.length - 1); updateSuggestionHighlight();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault(); activeSuggestion = Math.max(activeSuggestion - 1, 0); updateSuggestionHighlight();
        } else if (e.key === 'Enter') {
            if (activeSuggestion >= 0 && suggestions[activeSuggestion]) { e.preventDefault(); pickSuggestion(activeSuggestion); }
        } else if (e.key === 'Escape') {
            hideSuggestions();
        }
    });

    document.addEventListener('click', function(ev) {
        if (!ev.target.closest('.autocomplete-container')) hideSuggestions();
    });

    // ── Botón ZIP por contratante ────────────────────────────────────────────
    if (btnDownloadByContratante) {
        btnDownloadByContratante.addEventListener('click', async function() {
            const selectedId = selectedClienteIdInput.value;
            const q = (searchInput.value || '').trim();
            if (selectedId) {
                window.location.href = `/api/reportes/download-zip-contratante?cliente_id=${encodeURIComponent(selectedId)}`;
                return;
            }
            try {
                const resp = await fetch(`/api/reportes/search-contratantes?busqueda=${encodeURIComponent(q)}`, { credentials: 'same-origin' });
                if (!resp.ok) { alert('Error buscando contratantes'); return; }
                const items = await resp.json();
                if (!items || items.length === 0) { alert('No se encontraron contratantes'); return; }
                if (items.length === 1) {
                    window.location.href = `/api/reportes/download-zip-contratante?cliente_id=${encodeURIComponent(items[0].idCliente)}`;
                    return;
                }
                contratanteList.innerHTML = '';
                items.forEach(it => {
                    const div = document.createElement('div');
                    div.className = 'd-flex align-items-center justify-content-between py-2 border-bottom';
                    div.innerHTML = `<div><strong>${escapeHtml(it.razon_social||'')}</strong><div class="small text-muted">${escapeHtml(it.numero_documento||'')}</div></div>` +
                        `<div><button class="btn btn-sm btn-primary select-contratante" data-id="${it.idCliente}">Seleccionar</button></div>`;
                    contratanteList.appendChild(div);
                });
                contratanteList.querySelectorAll('.select-contratante').forEach(btn => {
                    btn.addEventListener('click', function() {
                        if (contratanteSelectModal) contratanteSelectModal.hide();
                        window.location.href = `/api/reportes/download-zip-contratante?cliente_id=${encodeURIComponent(this.dataset.id)}`;
                    });
                });
                if (contratanteSelectModal) contratanteSelectModal.show();
            } catch (err) {
                console.error('Error buscando contratantes', err);
                alert('Error buscando contratantes');
            }
        });
    }

    // ── Autocomplete ─────────────────────────────────────────────────────────
    async function handleAutocomplete(q) {
        if (!suggestionsEl) return;
        activeSuggestion = -1; suggestions = [];
        if (!q || q.trim().length < 1) { hideSuggestions(); return; }
        try {
            const resp = await fetch(`/api/reportes/search-contratantes?busqueda=${encodeURIComponent(q)}`, { credentials: 'same-origin' });
            if (resp.status === 401 || resp.status === 403) {
                suggestionsEl.innerHTML = `<div class="autocomplete-item text-muted">No autorizado (${resp.status})</div>`;
                suggestionsEl.classList.remove('d-none');
                return;
            }
            if (!resp.ok) { hideSuggestions(); return; }
            const items = await resp.json();
            if (!items || items.length === 0) {
                suggestionsEl.innerHTML = `<div class="autocomplete-item text-muted">Sin resultados</div>`;
                suggestionsEl.classList.remove('d-none');
                return;
            }
            suggestions = items; activeSuggestion = -1;
            renderSuggestions(items);
        } catch (err) {
            console.error('autocomplete error', err);
            hideSuggestions();
        }
    }

    function renderSuggestions(items) {
        if (!suggestionsEl) return;
        suggestionsEl.innerHTML = '';
        items.forEach((it, idx) => {
            const div = document.createElement('div');
            div.className = 'autocomplete-item';
            div.dataset.index = idx;
            div.innerHTML = `<div class="fw-semibold">${escapeHtml(it.razon_social||'')}</div><div class="small text-muted">${escapeHtml(it.numero_documento||'')}</div>`;
            div.addEventListener('click', function() { pickSuggestion(idx); });
            suggestionsEl.appendChild(div);
        });
        suggestionsEl.classList.remove('d-none');
    }

    function updateSuggestionHighlight() {
        const items = suggestionsEl.querySelectorAll('.autocomplete-item');
        items.forEach((it, i) => {
            it.classList.toggle('active', i === activeSuggestion);
            if (i === activeSuggestion) it.scrollIntoView({ block: 'nearest' });
        });
    }

    function pickSuggestion(idx) {
        const it = suggestions[idx];
        if (!it) return;
        searchInput.value = it.razon_social || '';
        selectedClienteIdInput.value = it.idCliente || '';
        lastSelectedName = it.razon_social || '';
        hideSuggestions();
        fetchFiles(it.razon_social || '');
    }

    function hideSuggestions() {
        if (!suggestionsEl) return;
        suggestionsEl.classList.add('d-none');
        suggestionsEl.innerHTML = '';
        suggestions = []; activeSuggestion = -1;
    }

    // ── Fetch principal ──────────────────────────────────────────────────────
    async function fetchFiles(query = '') {
        try {
            tableBody.innerHTML = `<tr><td colspan="12" class="text-center py-4 text-muted">Cargando...</td></tr>`;
            hideBanner();
            if (fetchController) {
                fetchController.abort();
            }
            fetchController = new AbortController();
            const response = await fetch(
                `/api/reportes/archivos-poliza?search=${encodeURIComponent(query)}`,
                { signal: fetchController.signal }
            );
            const json = await response.json();
            if (!response.ok) {
                const msg = (json && (json.error || json.message)) || `Error HTTP ${response.status}`;
                throw new Error(msg);
            }
            // El API devuelve { data: [...], has_more: bool }
            const data     = json.data     ?? json;   // fallback por si acaso
            const has_more = json.has_more ?? false;
            allData = Array.isArray(data) ? data : [];
            buildGroupsFromData(allData);
            currentPage = 1;
            renderPage();
            if (has_more && !query) {
                showBanner();
            }
        } catch (error) {
            if (error && error.name === 'AbortError') return;
            console.error('Error loading files:', error);
            tableBody.innerHTML = `<tr><td colspan="12" class="text-center text-danger">Error cargando datos</td></tr>`;
        }
    }

    // ── Banner "hay más registros" ────────────────────────────────────────────
    function showBanner() {
        let banner = document.getElementById('more-records-banner');
        if (!banner) return;
        banner.classList.remove('d-none');
    }
    function hideBanner() {
        let banner = document.getElementById('more-records-banner');
        if (!banner) return;
        banner.classList.add('d-none');
    }

    // ── Helpers ──────────────────────────────────────────────────────────────
    function escapeHtml(str) {
        return (str||'').replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));
    }

    function formatFecha(val) {
        if (!val) return '-';
        let dstr = typeof val === 'string' ? (val.includes('T') ? val : val.replace(' ', 'T')) : val;
        if (typeof dstr === 'string' && dstr.includes('T') && !/[zZ]$/.test(dstr)) {
            dstr += 'Z';
        }
        const date = new Date(dstr);
        if (isNaN(date.getTime())) return val;
        const parts = new Intl.DateTimeFormat('es-PE', {
            timeZone: 'America/Lima',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        }).formatToParts(date);
        const get = t => (parts.find(p => p.type === t) || { value: '' }).value;
        return `${get('day')}/${get('month')}/${get('year')} ${get('hour')}:${get('minute')}`;
    }

    function buildPolizaGroupKey(poliza, recibo, polizaId) {
        const p = (poliza || '').toString().trim();
        const r = (recibo || '').toString().trim();
        const id = (polizaId || '').toString().trim();
        return `${p}||${r}||${id}`;
    }

    function getTipoOrigen(row) {
        return ((row && row.tipo_origen) || '').toString().trim().toUpperCase();
    }

    function getCuotaStandaloneKey(row, index) {
        return `${buildPolizaGroupKey(row.poliza_padre_id || row.identificador, row.recibo, row.poliza_id)}||${row.cupon || row.cuota_id || ''}||${index}`;
    }

    function getRowGroupKey(row) {
        return buildPolizaGroupKey(row.identificador, row.recibo, row.poliza_id);
    }

    function formatIdentificador(row) {
        const poliza = row.identificador || '-';
        return poliza;
    }

    function formatRecibo(row) {
        const recibo = (row.recibo || '').toString().trim();
        return recibo ? recibo : '-';
    }

    function formatArchivo(row) {
        const archivo = (row.archivo || row.nombre_original || '').toString().trim();
        return archivo ? archivo : '-';
    }

    function formatPolizaCuota(row) {
        return (row.identificador || row.poliza_padre_id || '').toString().trim() || '-';
    }

    // ── Render tabla ─────────────────────────────────────────────────────────
    function renderTable(data) {
        if (!data || data.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="12" class="text-center text-muted py-4">No se encontraron archivos</td></tr>`;
            return;
        }

        const polizas = data.filter(r => getTipoOrigen(r) === 'POLIZA');
        const cuotas  = data.filter(r => getTipoOrigen(r) === 'CUOTA');
        const polizaKeys = new Set(polizas.map(p => getRowGroupKey(p)));

        const cuotasByPoliza = {};
        cuotas.forEach(c => {
            const padre = c.poliza_padre_id
                ? buildPolizaGroupKey(c.poliza_padre_id, c.recibo, c.poliza_id)
                : '__sin_padre__';
            if (!cuotasByPoliza[padre]) cuotasByPoliza[padre] = [];
            cuotasByPoliza[padre].push(c);
        });

        let html = '';

        polizas.forEach(row => {
            const rowKey   = getRowGroupKey(row);
            const hijos    = cuotasByPoliza[rowKey] || [];
            const hasHijos = hijos.length > 0;
            const toggleId = `toggle-${rowKey.replace(/[^a-z0-9]/gi,'_')}`;
            const polizaId = row.poliza_id || '';
            // hay hijos si tiene cuotas O tiene polizaId (puede tener archivos extra)
            const hasToggle = hasHijos || !!polizaId;

            const countChildren = hijos.reduce((a, c) => a + (c.cantidad_archivos || 0), 0);
            const countDisplay = countChildren > 0 ? countChildren : (row.cantidad_archivos || 0);
            html += `
            <tr class="poliza-row">
                <td class="text-start">
                    <div class="d-flex align-items-center justify-content-start gap-2 flex-nowrap">
                        ${hasToggle ? `
                        <button class="btn btn-sm btn-link p-0 text-secondary btn-toggle-children"
                                data-target="${toggleId}"
                                data-poliza-id="${polizaId}"
                                data-loaded="0"
                                title="Ver cuotas y archivos">
                            <i class="bi bi-chevron-right transition-icon" style="transform:rotate(0deg);"></i>
                        </button>` : '<span style="width:22px;display:inline-block;"></span>'}
                        <button class="btn btn-outline-secondary btn-sm btn-view-group"
                                data-id="${row.identificador || ''}"
                                data-type="POLIZA"
                                data-poliza-id="${polizaId}"
                                data-doc="${escapeHtml((formatArchivo(row) || '').split('|')[0].trim())}"
                                title="Ver archivo">
                            <i class="bi-eye"></i>
                        </button>
                        <button class="btn btn-outline-primary btn-sm btn-zip-group"
                                data-id="${row.identificador}"
                                data-type="${row.tipo_origen}"
                                data-poliza-id="${polizaId}"
                                title="Descargar archivos ZIP">
                            <i class="bi-file-zip"></i>
                        </button>
                    </div>
                </td>
                <td><span class="badge bg-primary text-white">Poliza</span></td>
                <td>
                    <div class="cell-main">${formatIdentificador(row)}</div>
                    <div class="cell-secondary">Poliza principal</div>
                </td>
                <td class="cell-doc" title="${escapeHtml(formatArchivo(row))}">${escapeHtml(formatArchivo(row))}</td>
                <td class="cell-recibo">${formatRecibo(row)}</td>
                <td class="small text-truncate" style="max-width:260px;" title="${row.contratante||''}">${row.contratante||'-'}</td>
                <td class="small text-muted">${row.ramo||'-'}</td>
                <td class="small text-muted">${row.producto||'-'}</td>
                <td class="small text-muted">${row.compania||'-'}</td>
                <td class="small text-muted">${row.usuario||'-'}</td>
                <td class="text-center"><span class="badge bg-secondary">${countDisplay}</span></td>
                <td class="small text-muted">${formatFecha(row.ultima_fecha)}</td>
            </tr>`;

            // Cuotas hijas — ocultas por defecto, marcadas con data-parent
            hijos.forEach(c => {
                html += `
                <tr class="cuota-child-row d-none" data-parent="${toggleId}">
                    <td class="text-start ps-4">
                        <div class="d-flex align-items-center justify-content-start gap-2 ps-3 flex-nowrap">
                            <i class="bi bi-arrow-return-right text-muted me-1"></i>
                            <button class="btn btn-outline-secondary btn-sm btn-view-group"
                                    data-id="${c.cupon || c.recibo || ''}"
                                    data-poliza-id="${c.poliza_id || ''}"
                                    data-type="CUOTA"
                                    data-doc="${escapeHtml((formatArchivo(c) || '').split('|')[0].trim())}"
                                    title="Ver archivo">
                                <i class="bi-eye"></i>
                            </button>
                            <button class="btn btn-outline-success btn-sm btn-zip-group"
                                    data-id="${c.cupon || c.recibo || ''}"
                                    data-policy="${c.poliza_padre_id || ''}"
                                    data-poliza-id="${c.poliza_id || ''}"
                                    data-type="CUOTA"
                                    title="Descargar archivos ZIP de cuota">
                                <i class="bi-file-zip"></i>
                            </button>
                        </div>
                    </td>
                    <td><span class="badge bg-success text-white">Cuota</span></td>
                    <td>
                        <div class="cell-main">${formatPolizaCuota(c)}</div>
                        <div class="cell-secondary">Cuota asociada</div>
                    </td>
                    <td class="cell-doc" title="${escapeHtml(formatArchivo(c))}">${escapeHtml(formatArchivo(c))}</td>
                    <td class="cell-recibo">${(c.recibo || '').toString().trim() ? c.recibo : '-'}</td>
                    <td class="small text-truncate" style="max-width:260px;" title="${c.contratante||''}">${c.contratante||'-'}</td>
                    <td class="small text-muted">${c.ramo||'-'}</td>
                    <td class="small text-muted">${c.producto||'-'}</td>
                    <td class="small text-muted">${c.compania||'-'}</td>
                    <td class="small text-muted">${c.usuario||'-'}</td>
                    <td class="text-center"><span class="badge bg-secondary">${c.cantidad_archivos||0}</span></td>
                    <td class="small text-muted">${formatFecha(c.ultima_fecha)}</td>
                </tr>`;
            });

            // Fila placeholder para archivos extra (lazy-load) — oculta
            if (polizaId) {
                html += `<tr class="arch-extra-placeholder d-none" data-parent="${toggleId}" id="arch-ph-${toggleId}">
                    <td colspan="12" class="py-1 text-center text-muted fst-italic small">
                        <span class="spinner-border spinner-border-sm me-1"></span>Cargando archivos...
                    </td>
                </tr>`;
            }
        });

        // Cuotas sin fila padre de póliza en el set actual (incluye huérfanas y faltantes)
        const cuotasSinPadreVisible = cuotas.filter(c => {
            const padre = c.poliza_padre_id
                ? buildPolizaGroupKey(c.poliza_padre_id, c.recibo, c.poliza_id)
                : '__sin_padre__';
            return padre === '__sin_padre__' || !polizaKeys.has(padre);
        });

        cuotasSinPadreVisible.forEach(c => {
            html += `
            <tr class="cuota-child-row">
                <td class="text-start">
                    <div class="d-flex align-items-center justify-content-start gap-2 flex-nowrap">
                        <button class="btn btn-outline-secondary btn-sm btn-view-group"
                                data-id="${c.cupon || c.recibo || ''}"
                                data-poliza-id="${c.poliza_id || ''}"
                                data-type="CUOTA"
                                data-doc="${escapeHtml((formatArchivo(c) || '').split('|')[0].trim())}"
                                title="Ver archivo">
                            <i class="bi-eye"></i>
                        </button>
                        <button class="btn btn-outline-success btn-sm btn-zip-group"
                                data-id="${c.cupon || c.recibo || ''}"
                                data-poliza-id="${c.poliza_id || ''}"
                                data-type="CUOTA"
                                title="Descargar archivos ZIP de cuota">
                            <i class="bi-file-zip"></i>
                        </button>
                    </div>
                </td>
                <td><span class="badge bg-success text-white">Cuota</span></td>
                <td>
                    <div class="cell-main">${formatPolizaCuota(c)}</div>
                    <div class="cell-secondary">Sin poliza padre visible</div>
                </td>
                <td class="cell-doc" title="${escapeHtml(formatArchivo(c))}">${escapeHtml(formatArchivo(c))}</td>
                <td class="cell-recibo">${(c.recibo || '').toString().trim() ? c.recibo : '-'}</td>
                <td class="small text-truncate" style="max-width:260px;" title="${c.contratante||''}">${c.contratante||'-'}</td>
                <td class="small text-muted">${c.ramo||'-'}</td>
                <td class="small text-muted">${c.producto||'-'}</td>
                <td class="small text-muted">${c.compania||'-'}</td>
                <td class="small text-muted">${c.usuario||'-'}</td>
                <td class="text-center"><span class="badge bg-secondary">${c.cantidad_archivos||0}</span></td>
                <td class="small text-muted">${formatFecha(c.ultima_fecha)}</td>
            </tr>`;
        });

        tableBody.innerHTML = html;

        try {
            document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
            document.body.style.overflow = '';
            document.body.style.pointerEvents = '';
        } catch (ignore) {}

        // Toggle chevron — expande cuotas hijas + carga archivos extra
        document.querySelectorAll('.btn-toggle-children').forEach(btn => {
            btn.addEventListener('click', async function() {
                const target   = this.dataset.target;
                const polizaId = this.dataset.polizaId;
                const icon     = this.querySelector('.transition-icon');
                const childs   = tableBody.querySelectorAll(`[data-parent="${target}"]`);
                const isOpen   = childs.length > 0 && !childs[0].classList.contains('d-none');

                if (isOpen) {
                    // Colapsar todo
                    childs.forEach(tr => tr.classList.add('d-none'));
                    if (icon) icon.style.transform = 'rotate(0deg)';
                    return;
                }

                // Expandir cuotas existentes
                childs.forEach(tr => tr.classList.remove('d-none'));
                if (icon) icon.style.transform = 'rotate(90deg)';

                // Cargar archivos extra si hay polizaId y aún no se cargaron
                if (!polizaId || this.dataset.loaded === '1') return;
                this.dataset.loaded = '1';

                const phRow = document.getElementById(`arch-ph-${target}`);

                try {
                    const resp = await fetch(`/api/polizas/archivos/${polizaId}`);
                    const res  = await resp.json();
                    const archivos = res.archivos || [];

                    // Quitar placeholder
                    if (phRow) phRow.remove();

                    if (archivos.length === 0) return;

                    const tipoMap = {
                        'PROFORMA':     '<span class="badge-arch-proforma">Proforma</span>',
                        'ARCHIVO_EXTRA':'<span class="badge-arch-extra">Archivo extra</span>',
                        'CARGA_MASIVA': '<span class="badge-arch-masiva">Carga masiva</span>',
                    };

                    // Insertar filas de archivos extra después de la última fila hija
                    const allChilds = tableBody.querySelectorAll(`[data-parent="${target}"]`);
                    let insertRef = allChilds.length > 0
                        ? allChilds[allChilds.length - 1]
                        : this.closest('tr');

                    archivos.forEach(a => {
                        const url       = `/uploads/${a.ruta_archivo}`;
                        const tipoBadge = tipoMap[a.origen] || `<span class="badge-arch-masiva">${escapeHtml(a.origen||'-')}</span>`;
                        const tr = document.createElement('tr');
                        tr.className = 'arch-extra-row';
                        tr.dataset.parent = target;
                        tr.innerHTML = `
                            <td class="text-start">
                                <div class="d-flex align-items-center justify-content-start gap-2 flex-nowrap">
                                    <i class="bi bi-arrow-return-right text-warning" style="font-size:.8rem;"></i>
                                    <a href="${url}" target="_blank" class="btn btn-outline-warning btn-sm" title="Ver archivo">
                                        <i class="bi-eye"></i>
                                    </a>
                                    <button class="btn btn-outline-primary btn-sm btn-zip-group"
                                            data-id="${a.identificador || ''}"
                                            data-poliza-id="${polizaId || ''}"
                                            data-type="POLIZA"
                                            title="Descargar archivos ZIP">
                                        <i class="bi-file-zip"></i>
                                    </button>
                                </div>
                            </td>
                            <td><span class="badge-arch-poliza-label">Archivo</span></td>
                            <td class="small fw-semibold" colspan="3">
                                <i class="bi-file-earmark me-1 text-warning"></i>${escapeHtml(a.nombre_original||'-')}
                            </td>
                            <td colspan="3" class="small">${tipoBadge}</td>
                            <td colspan="4" class="small text-muted">${a.creado_en||''}</td>`;
                        insertRef.insertAdjacentElement('afterend', tr);
                        insertRef = tr;
                    });

                } catch(e) {
                    console.error('[arch-extra]', e);
                    if (phRow) phRow.remove();
                }
            });
        });

        // Botón ver — abre el primer archivo disponible del grupo
        document.querySelectorAll('.btn-view-group').forEach(btn => {
            btn.addEventListener('click', async function() {
                const identificador = this.dataset.id || '';
                const tipo = this.dataset.type || '';
                const polizaId = this.dataset.polizaId || '';
                const docHintRaw = (this.dataset.doc || '').trim();
                const docHint = docHintRaw && docHintRaw !== '-' ? docHintRaw : '';
                const norm = (v) => (v || '').toString().trim().toLowerCase();
                const isImage = (name) => /\.(png|jpg|jpeg|webp|gif|bmp|svg)$/i.test((name || '').toString());
                const isPdf = (name) => /\.pdf$/i.test((name || '').toString());
                const isLogoLike = (path) => /(^|[\\/])img[\\/]logo-aasnet/i.test((path || '').toString());
                try {
                    const qs = new URLSearchParams({
                        identificador,
                        tipo,
                        poliza_id: polizaId
                    });
                    const resp = await fetch(`/api/reportes/archivos-detalle-completo?${qs.toString()}`);
                    const json = await resp.json();
                    const archivos = [
                        ...((json && json.archivos) || []),
                        ...((json && json.archivos_extra) || [])
                    ];
                    if (!archivos.length) {
                        alert('No hay archivos para visualizar en este registro');
                        return;
                    }

                    // En fila padre: abrir todos los archivos del grupo (sin duplicados por ruta).
                    if (tipo === 'POLIZA') {
                        const rutas = [...new Set(
                            archivos
                                .map(a => (a && a.ruta_archivo ? String(a.ruta_archivo).replace(/^[/\\]+/, '') : ''))
                                .filter(Boolean)
                        )];

                        if (!rutas.length) {
                            alert('No hay archivos para visualizar en este registro');
                            return;
                        }

                        const multiWin = window.open('', '_blank');
                        if (!multiWin) {
                            alert('El navegador bloqueó la ventana emergente. Habilítala para visualizar los archivos.');
                            return;
                        }

                        const safeTitle = escapeHtml(identificador || 'Poliza');
                        const itemsHtml = rutas.map((ruta, i) => {
                            const url = `/uploads/${ruta}`;
                            const label = escapeHtml((archivos.find(a => (a && String(a.ruta_archivo || '').replace(/^[/\\]+/, '') === ruta) || {}).nombre_original || `Archivo ${i + 1}`));
                            return `
                                <section style="border:1px solid #e5e7eb;border-radius:8px;padding:10px;margin:10px 0;background:#fff;">
                                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;gap:8px;">
                                        <strong style="font-family:Arial,sans-serif;font-size:14px;">${label}</strong>
                                        <a href="${url}" target="_blank" rel="noopener" style="font-family:Arial,sans-serif;font-size:12px;">Abrir en nueva pestaña</a>
                                    </div>
                                    <iframe src="${url}" style="width:100%;height:520px;border:1px solid #e5e7eb;border-radius:6px;"></iframe>
                                </section>
                            `;
                        }).join('');

                        multiWin.document.open();
                        multiWin.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Archivos de ${safeTitle}</title></head><body style="margin:16px;background:#f8fafc;">` +
                            `<h2 style="font-family:Arial,sans-serif;margin:0 0 8px 0;">Archivos de ${safeTitle}</h2>` +
                            `<p style="font-family:Arial,sans-serif;color:#475569;margin:0 0 14px 0;">Se encontraron ${rutas.length} archivo(s).</p>` +
                            itemsHtml +
                            `</body></html>`);
                        multiWin.document.close();
                        return;
                    }

                    const scoreFile = (a) => {
                        const nombre = (a && a.nombre_original) || '';
                        const ruta = (a && a.ruta_archivo) || '';
                        let score = 0;

                        if (docHint && norm(nombre) === norm(docHint)) score += 120;
                        else if (docHint && (norm(nombre).includes(norm(docHint)) || norm(docHint).includes(norm(nombre)))) score += 80;

                        if (isPdf(ruta)) score += 30;
                        if (isImage(ruta)) score -= 30;
                        if (isLogoLike(ruta)) score -= 120;

                        return score;
                    };

                    const selected = [...archivos].sort((a, b) => scoreFile(b) - scoreFile(a))[0];

                    const ruta = (selected && selected.ruta_archivo ? selected.ruta_archivo : '').toString().replace(/^[/\\]+/, '');
                    if (!ruta) {
                        alert('No se pudo obtener la ruta del archivo');
                        return;
                    }
                    window.open(`/uploads/${ruta}`, '_blank');
                } catch (e) {
                    console.error('Error abriendo vista de archivo', e);
                    alert('No se pudo abrir el archivo');
                }
            });
        });

        // Botón ZIP — descarga directa
        document.querySelectorAll('.btn-zip-group').forEach(btn => {
            btn.addEventListener('click', function() {
                const id = this.dataset.id || '';
                const type = this.dataset.type || '';
                const poliza = this.dataset.policy || '';
                const polizaId = this.dataset.polizaId || '';
                const extra = type === 'CUOTA' && poliza ? `&poliza=${encodeURIComponent(poliza)}` : '';
                const extraPolizaId = polizaId ? `&poliza_id=${encodeURIComponent(polizaId)}` : '';
                window.location.href = `/api/reportes/download-zip?identificador=${encodeURIComponent(id)}&tipo=${encodeURIComponent(type)}${extra}${extraPolizaId}`;
            });
        });
    }

    function buildGroupsFromData(data) {
        const polizas = data.filter(r => getTipoOrigen(r) === 'POLIZA');
        const cuotas  = data.filter(r => getTipoOrigen(r) === 'CUOTA');
        const polizaKeys = new Set(polizas.map(p => getRowGroupKey(p)));

        const gs = [];
        polizas.forEach(p => {
            gs.push({ type: 'POLIZA', id: getRowGroupKey(p) });
        });

        cuotas.forEach((c, idx) => {
            const padre = c.poliza_padre_id
                ? buildPolizaGroupKey(c.poliza_padre_id, c.recibo, c.poliza_id)
                : '__sin_padre__';
            if (padre === '__sin_padre__' || !polizaKeys.has(padre)) {
                gs.push({ type: 'CUOTA_ONLY', id: getCuotaStandaloneKey(c, idx) });
            }
        });

        groups = gs;
    }

    function getPageData() {
        const totalGroups = groups.length;
        const start = Math.max(0, (currentPage - 1) * pageSize);
        const end = Math.min(start + pageSize, totalGroups);
        const slice = groups.slice(start, end);
        const polizaMap = {};
        const cuotasByPoliza = {};
        const cuotaStandaloneMap = {};
        allData.forEach(r => {
            const tipo = getTipoOrigen(r);
            if (tipo === 'POLIZA') {
                polizaMap[getRowGroupKey(r)] = r;
            } else if (tipo === 'CUOTA') {
                const padre = r.poliza_padre_id
                    ? buildPolizaGroupKey(r.poliza_padre_id, r.recibo, r.poliza_id)
                    : '__sin_padre__';
                if (!cuotasByPoliza[padre]) cuotasByPoliza[padre] = [];
                cuotasByPoliza[padre].push(r);
            }
        });

        const polizaKeys = new Set(Object.keys(polizaMap));
        allData.forEach((r, idx) => {
            if (getTipoOrigen(r) !== 'CUOTA') return;
            const padre = r.poliza_padre_id
                ? buildPolizaGroupKey(r.poliza_padre_id, r.recibo, r.poliza_id)
                : '__sin_padre__';
            if (padre === '__sin_padre__' || !polizaKeys.has(padre)) {
                cuotaStandaloneMap[getCuotaStandaloneKey(r, idx)] = r;
            }
        });

        const pageRaw = [];
        slice.forEach(g => {
            if (g.type === 'POLIZA') {
                const p = polizaMap[g.id];
                if (p) {
                    pageRaw.push(p);
                    (cuotasByPoliza[g.id] || []).forEach(c => pageRaw.push(c));
                }
            } else if (g.type === 'CUOTA_ONLY') {
                const quota = cuotaStandaloneMap[g.id];
                if (quota) pageRaw.push(quota);
            }
        });
        return { pageRaw, totalGroups, start, end };
    }

    function renderPage() {
        const { pageRaw, totalGroups, start, end } = getPageData();
        renderTable(pageRaw);
        renderPagination(totalGroups);
        if (pageInfoEl) {
            pageInfoEl.textContent = `Mostrando ${start + 1}–${end} de ${totalGroups}`;
        }
    }

    function renderPagination(totalGroups) {
         if (!paginationEl) return;
         const pages = Math.max(1, Math.ceil(totalGroups / pageSize));
         const visible = new Set();
         
         // Agregar primeros 3 números de página
         for (let i = 1; i <= Math.min(3, pages); i++) {
             visible.add(i);
         }
         
         // Agregar últimos 3 números de página
         for (let i = Math.max(1, pages - 2); i <= pages; i++) {
             visible.add(i);
         }

         const ordered = Array.from(visible).sort((a, b) => a - b);
         const items = [];
         let previous = 0;
         ordered.forEach(num => {
             if (num - previous > 1) {
                 items.push('ellipsis');
             }
             items.push(num);
             previous = num;
         });

         let html = '';
         const prevDisabled = currentPage <= 1 ? ' disabled' : '';
         const nextDisabled = currentPage >= pages ? ' disabled' : '';
         html += `<li class="page-item${prevDisabled}"><a class="page-link" href="#" data-action="prev">&laquo;</a></li>`;
         items.forEach(item => {
             if (item === 'ellipsis') {
                 html += `<li class="page-item disabled"><span class="page-link">…</span></li>`;
                 return;
             }
             const active = item === currentPage ? ' active' : '';
             html += `<li class="page-item${active}"><a class="page-link" href="#" data-page="${item}">${item}</a></li>`;
         });
         html += `<li class="page-item${nextDisabled}"><a class="page-link" href="#" data-action="next">&raquo;</a></li>`;
         html += `<li class="page-item ms-2"><a class="page-link" href="#" data-action="last" title="Ir a última página">Última</a></li>`;
         paginationEl.innerHTML = html;
         paginationEl.querySelectorAll('a.page-link').forEach(a => {
             a.addEventListener('click', function(e) {
                 e.preventDefault();
                 const act = this.dataset.action;
                 const num = parseInt(this.dataset.page || '0', 10);
                 const pages = Math.max(1, Math.ceil(totalGroups / pageSize));
                 if (act === 'prev') {
                     currentPage = Math.max(1, currentPage - 1);
                 } else if (act === 'next') {
                     currentPage = Math.min(pages, currentPage + 1);
                 } else if (act === 'last') {
                     currentPage = pages;
                 } else if (num) {
                     currentPage = num;
                 }
                 renderPage();
             });
         });
     }

    if (pageSizeSelect) {
        pageSizeSelect.addEventListener('change', function() {
            const val = parseInt(this.value, 10);
            pageSize = isNaN(val) ? 10 : val;
            currentPage = 1;
            renderPage();
        });
    }

});

