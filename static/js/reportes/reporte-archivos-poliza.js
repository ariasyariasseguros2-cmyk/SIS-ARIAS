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
            tableBody.innerHTML = `<tr><td colspan="10" class="text-center py-4 text-muted">Cargando...</td></tr>`;
            hideBanner();
            const response = await fetch(`/api/reportes/archivos-poliza?search=${encodeURIComponent(query)}`);
            const json = await response.json();
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
            console.error('Error loading files:', error);
            tableBody.innerHTML = `<tr><td colspan="10" class="text-center text-danger">Error cargando datos</td></tr>`;
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
        const date = new Date(val);
        if (isNaN(date.getTime())) return val;
        const d  = String(date.getUTCDate()).padStart(2,'0');
        const m  = String(date.getUTCMonth()+1).padStart(2,'0');
        const y  = date.getUTCFullYear();
        const hh = String(date.getUTCHours()).padStart(2,'0');
        const mm = String(date.getUTCMinutes()).padStart(2,'0');
        return `${d}/${m}/${y} ${hh}:${mm}`;
    }

    // ── Render tabla ─────────────────────────────────────────────────────────
    function renderTable(data) {
        if (!data || data.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="10" class="text-center text-muted py-4">No se encontraron archivos</td></tr>`;
            return;
        }

        const polizas = data.filter(r => r.tipo_origen === 'POLIZA');
        const cuotas  = data.filter(r => r.tipo_origen === 'CUOTA');

        const cuotasByPoliza = {};
        cuotas.forEach(c => {
            const padre = c.poliza_padre_id || '__sin_padre__';
            if (!cuotasByPoliza[padre]) cuotasByPoliza[padre] = [];
            cuotasByPoliza[padre].push(c);
        });

        let html = '';

        polizas.forEach(row => {
            const hijos    = cuotasByPoliza[row.identificador] || [];
            const hasHijos = hijos.length > 0;
            const toggleId = `toggle-${row.identificador.replace(/[^a-z0-9]/gi,'_')}`;
            const polizaId = row.poliza_id || '';
            // hay hijos si tiene cuotas O tiene polizaId (puede tener archivos extra)
            const hasToggle = hasHijos || !!polizaId;

            html += `
            <tr class="poliza-row">
                <td class="text-center">
                    <div class="d-flex align-items-center justify-content-center gap-1">
                        ${hasToggle ? `
                        <button class="btn btn-sm btn-link p-0 text-secondary btn-toggle-children"
                                data-target="${toggleId}"
                                data-poliza-id="${polizaId}"
                                data-loaded="0"
                                title="Ver cuotas y archivos">
                            <i class="bi bi-chevron-right transition-icon"></i>
                        </button>` : '<span style="width:22px;display:inline-block;"></span>'}
                        <button class="btn btn-outline-primary btn-sm btn-zip-group"
                                data-id="${row.identificador}"
                                data-type="${row.tipo_origen}"
                                title="Descargar archivos ZIP">
                            <i class="bi-file-zip"></i>
                        </button>
                    </div>
                </td>
                <td><span class="badge bg-primary text-white">PÓLIZA</span></td>
                <td class="fw-bold">${row.identificador || '-'}</td>
                <td class="small text-truncate" style="max-width:260px;" title="${row.contratante||''}">${row.contratante||'-'}</td>
                <td class="small text-muted">${row.ramo||'-'}</td>
                <td class="small text-muted">${row.producto||'-'}</td>
                <td class="small text-muted">${row.compania||'-'}</td>
                <td class="small text-muted">${row.usuario||'-'}</td>
                <td class="text-center"><span class="badge bg-secondary">${row.cantidad_archivos||0}</span></td>
                <td class="small text-muted">${formatFecha(row.ultima_fecha)}</td>
            </tr>`;

            // Cuotas hijas — ocultas por defecto, marcadas con data-parent
            hijos.forEach(c => {
                html += `
                <tr class="cuota-child-row d-none" data-parent="${toggleId}">
                    <td class="text-center ps-4">
                        <div class="d-flex align-items-center justify-content-center gap-1 ps-3">
                            <i class="bi bi-arrow-return-right text-muted me-1"></i>
                            <button class="btn btn-outline-success btn-sm btn-zip-group"
                                    data-id="${c.cuota_id}"
                                    data-type="CUOTA"
                                    title="Descargar archivos ZIP de cuota">
                                <i class="bi-file-zip"></i>
                            </button>
                        </div>
                    </td>
                    <td><span class="badge bg-success text-white">CUOTA</span></td>
                    <td class="text-muted small fw-semibold">${c.cupon || ('ID: ' + c.cuota_id)}</td>
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
                    <td colspan="10" class="py-1 text-center text-muted fst-italic small">
                        <span class="spinner-border spinner-border-sm me-1"></span>Cargando archivos...
                    </td>
                </tr>`;
            }
        });

        // Cuotas sin póliza padre
        const cuotasHuerfanas = cuotasByPoliza['__sin_padre__'] || [];
        cuotasHuerfanas.forEach(c => {
            html += `
            <tr class="cuota-child-row">
                <td class="text-center">
                    <button class="btn btn-outline-success btn-sm btn-zip-group"
                            data-id="${c.cuota_id}"
                            data-type="CUOTA"
                            title="Descargar archivos ZIP de cuota">
                        <i class="bi-file-zip"></i>
                    </button>
                </td>
                <td><span class="badge bg-success text-white">CUOTA</span></td>
                <td class="small fw-semibold">${c.cupon || ('ID: ' + c.cuota_id)}</td>
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
                            <td class="text-center">
                                <div class="d-flex align-items-center justify-content-center gap-1">
                                    <i class="bi bi-arrow-return-right text-warning" style="font-size:.8rem;"></i>
                                    <a href="${url}" target="_blank" class="btn btn-outline-warning btn-sm" title="Ver archivo">
                                        <i class="bi-eye"></i>
                                    </a>
                                </div>
                            </td>
                            <td><span class="badge-arch-poliza-label">ARCHIVO</span></td>
                            <td class="small fw-semibold" colspan="2">
                                <i class="bi-file-earmark me-1 text-warning"></i>${escapeHtml(a.nombre_original||'-')}
                            </td>
                            <td colspan="3" class="small">${tipoBadge}</td>
                            <td colspan="3" class="small text-muted">${a.creado_en||''}</td>`;
                        insertRef.insertAdjacentElement('afterend', tr);
                        insertRef = tr;
                    });

                } catch(e) {
                    console.error('[arch-extra]', e);
                    if (phRow) phRow.remove();
                }
            });
        });

        // Botón ZIP — descarga directa
        document.querySelectorAll('.btn-zip-group').forEach(btn => {
            btn.addEventListener('click', function() {
                window.location.href = `/api/reportes/download-zip?identificador=${encodeURIComponent(this.dataset.id)}&tipo=${encodeURIComponent(this.dataset.type)}`;
            });
        });
    }

    function buildGroupsFromData(data) {
        const polizas = data.filter(r => r.tipo_origen === 'POLIZA');
        const cuotas  = data.filter(r => r.tipo_origen === 'CUOTA');
        const cuotasByPoliza = {};
        cuotas.forEach(c => {
            const padre = c.poliza_padre_id || '__sin_padre__';
            if (!cuotasByPoliza[padre]) cuotasByPoliza[padre] = [];
            cuotasByPoliza[padre].push(c);
        });
        const gs = [];
        polizas.forEach(p => {
            gs.push({ type: 'POLIZA', id: p.identificador });
        });
        (cuotasByPoliza['__sin_padre__'] || []).forEach(c => {
            gs.push({ type: 'CUOTA_ORPHAN', id: c.cuota_id });
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
        allData.forEach(r => {
            if (r.tipo_origen === 'POLIZA') {
                polizaMap[r.identificador] = r;
            } else if (r.tipo_origen === 'CUOTA') {
                const padre = r.poliza_padre_id || '__sin_padre__';
                if (!cuotasByPoliza[padre]) cuotasByPoliza[padre] = [];
                cuotasByPoliza[padre].push(r);
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
            } else {
                const orphan = (cuotasByPoliza['__sin_padre__'] || []).find(x => String(x.cuota_id) === String(g.id));
                if (orphan) pageRaw.push(orphan);
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
        let html = '';
        const prevDisabled = currentPage <= 1 ? ' disabled' : '';
        const nextDisabled = currentPage >= pages ? ' disabled' : '';
        html += `<li class="page-item${prevDisabled}"><a class="page-link" href="#" data-action="prev">&laquo;</a></li>`;
        for (let i = 1; i <= pages; i++) {
            const active = i === currentPage ? ' active' : '';
            html += `<li class="page-item${active}"><a class="page-link" href="#" data-page="${i}">${i}</a></li>`;
        }
        html += `<li class="page-item${nextDisabled}"><a class="page-link" href="#" data-action="next">&raquo;</a></li>`;
        paginationEl.innerHTML = html;
        paginationEl.querySelectorAll('a.page-link').forEach(a => {
            a.addEventListener('click', function(e) {
                e.preventDefault();
                const act = this.dataset.action;
                const num = parseInt(this.dataset.page || '0', 10);
                const pages = Math.max(1, Math.ceil(groups.length / pageSize));
                if (act === 'prev') {
                    currentPage = Math.max(1, currentPage - 1);
                } else if (act === 'next') {
                    currentPage = Math.min(pages, currentPage + 1);
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

