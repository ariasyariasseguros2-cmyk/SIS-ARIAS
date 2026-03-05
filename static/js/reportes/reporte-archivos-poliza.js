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

    let debounceTimer;
    let suggestions = [];
    let activeSuggestion = -1;
    let lastSelectedName = '';
    let suggestTimer = null;

    // Initial Load
    fetchFiles();

    // Search Handler (no actualizar tabla mientras se escribe; solo sugerencias)
    searchInput.addEventListener('input', function(e) {
        clearTimeout(debounceTimer);
        const q = this.value;
        // Si el usuario editó el texto después de seleccionar un cliente, limpiar la selección
        if (lastSelectedName && q !== lastSelectedName) {
            selectedClienteIdInput.value = '';
            lastSelectedName = '';
        }
        // Si el campo quedó vacío, ocultar sugerencias y restaurar listado completo
        if (!q || q.trim().length < 1) {
            // limpiar selección
            selectedClienteIdInput.value = '';
            lastSelectedName = '';
            hideSuggestions();
            // restaurar tabla al estado original (sin filtro)
            fetchFiles('');
            return;
        }
        // Mostrar sugerencias mientras escribe; NO actualizar la tabla hasta que se seleccione
        // Debounce para sugerencias
        if (suggestTimer) clearTimeout(suggestTimer);
        suggestTimer = setTimeout(() => handleAutocomplete(q), 200);
    });

    // Manejo de teclas para autocomplete
    searchInput.addEventListener('keydown', function(e) {
        if (!suggestionsEl || suggestionsEl.classList.contains('d-none')) return;
        if (e.key === 'ArrowDown') {
            e.preventDefault(); activeSuggestion = Math.min(activeSuggestion + 1, suggestions.length - 1); updateSuggestionHighlight();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault(); activeSuggestion = Math.max(activeSuggestion - 1, 0); updateSuggestionHighlight();
        } else if (e.key === 'Enter') {
            if (activeSuggestion >= 0 && suggestions[activeSuggestion]) {
                e.preventDefault(); pickSuggestion(activeSuggestion);
            }
        } else if (e.key === 'Escape') {
            hideSuggestions();
        }
    });

    // Click fuera cierra sugerencias
    document.addEventListener('click', function(ev){
        if (!ev.target.closest('.autocomplete-container')) hideSuggestions();
    });

    // Botón ZIP: si hay cliente seleccionado usa cliente_id; si no, abre flujo de búsqueda/selección
    if (btnDownloadByContratante) {
        btnDownloadByContratante.addEventListener('click', async function() {
            const selectedId = selectedClienteIdInput.value;
            const q = (searchInput.value || '').trim();
            if (selectedId) {
                window.location.href = `/api/reportes/download-zip-contratante?cliente_id=${encodeURIComponent(selectedId)}`;
                return;
            }

            // Si no hay cliente seleccionado, buscar coincidencias y manejar 0/1/múltiples
            try {
                const resp = await fetch(`/api/reportes/search-contratantes?busqueda=${encodeURIComponent(q)}`, { credentials: 'same-origin' });
                if (!resp.ok) {
                    alert('Error buscando contratantes');
                    return;
                }
                const items = await resp.json();
                if (!items || items.length === 0) {
                    alert('No se encontraron contratantes para la búsqueda');
                    return;
                }
                if (items.length === 1) {
                    const id = items[0].idCliente;
                    window.location.href = `/api/reportes/download-zip-contratante?cliente_id=${encodeURIComponent(id)}`;
                    return;
                }

                // Múltiples: mostrar modal para selección
                contratanteList.innerHTML = '';
                items.forEach(it => {
                    const div = document.createElement('div');
                    div.className = 'd-flex align-items-center justify-content-between py-2 border-bottom';
                    div.innerHTML = `<div><strong>${escapeHtml(it.razon_social || '')}</strong><div class="small text-muted">${escapeHtml(it.numero_documento || '')}</div></div><div><button class="btn btn-sm btn-primary select-contratante" data-id="${it.idCliente}">Seleccionar</button></div>`;
                    contratanteList.appendChild(div);
                });

                contratanteList.querySelectorAll('.select-contratante').forEach(btn => {
                    btn.addEventListener('click', function() {
                        const id = this.dataset.id;
                        if (contratanteSelectModal) contratanteSelectModal.hide();
                        window.location.href = `/api/reportes/download-zip-contratante?cliente_id=${encodeURIComponent(id)}`;
                    });
                });

                if (contratanteSelectModal) contratanteSelectModal.show();

            } catch (err) {
                console.error('Error buscando contratantes', err);
                alert('Error buscando contratantes');
            }
        });
    }

    // Autocomplete: petición de sugerencias
    async function handleAutocomplete(q) {
        if (!suggestionsEl) return;
        activeSuggestion = -1;
        suggestions = [];
        if (!q || q.trim().length < 1) { hideSuggestions(); return; }
        try {
            console.log('[autocomplete] buscando:', q);
            const resp = await fetch(`/api/reportes/search-contratantes?busqueda=${encodeURIComponent(q)}`, { credentials: 'same-origin' });
            if (resp.status === 401 || resp.status === 403) {
                console.warn('[autocomplete] no autenticado o sin permisos:', resp.status);
                // Mostrar mensaje en la lista para indicar el estado
                suggestionsEl.innerHTML = `<div class="autocomplete-item text-muted">No autorizado o no autenticado (status ${resp.status})</div>`;
                suggestionsEl.classList.remove('d-none');
                return;
            }
             if (!resp.ok) { hideSuggestions(); return; }
             const items = await resp.json();
             console.log('[autocomplete] resultados:', items && items.length);
             if (!items || items.length === 0) {
                suggestionsEl.innerHTML = `<div class="autocomplete-item text-muted">Sin resultados</div>`;
                suggestionsEl.classList.remove('d-none');
                return; }
             suggestions = items;
             activeSuggestion = -1;
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
            div.addEventListener('click', function(){ pickSuggestion(idx); });
            suggestionsEl.appendChild(div);
        });
        suggestionsEl.classList.remove('d-none');
    }

    function updateSuggestionHighlight(){
        const items = suggestionsEl.querySelectorAll('.autocomplete-item');
        items.forEach((it, i) => {
            it.classList.toggle('active', i === activeSuggestion);
            if (i === activeSuggestion) {
                // ensure visible
                it.scrollIntoView({block: 'nearest'});
            }
        });
    }

    function pickSuggestion(idx){
        const it = suggestions[idx];
        if (!it) return;
        searchInput.value = it.razon_social || '';
        selectedClienteIdInput.value = it.idCliente || '';
        lastSelectedName = it.razon_social || '';
        hideSuggestions();
        // actualizar tabla con el cliente seleccionado
        fetchFiles(it.razon_social || '');
    }

    function hideSuggestions(){
        if (!suggestionsEl) return;
        suggestionsEl.classList.add('d-none');
        suggestionsEl.innerHTML = '';
        suggestions = [];
        activeSuggestion = -1;
    }

    async function fetchFiles(query = '') {
        try {
            tableBody.innerHTML = `<tr><td colspan="10" class="text-center py-4 text-muted">Cargando...</td></tr>`;
            const url = `/api/reportes/archivos-poliza?search=${encodeURIComponent(query)}`;
            const response = await fetch(url);
            const data = await response.json();
            renderTable(data);
        } catch (error) {
            console.error('Error loading files:', error);
            tableBody.innerHTML = `<tr><td colspan="10" class="text-center text-danger">Error cargando datos</td></tr>`;
        }
    }

    function escapeHtml(str) {
        return (str||'').replace(/[&<>\"]/g, function(m){ return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]); });
    }

    function formatFecha(val) {
        if (!val) return '-';
        const date = new Date(val);
        if (isNaN(date.getTime())) return val;
        const d = String(date.getUTCDate()).padStart(2,'0');
        const m = String(date.getUTCMonth()+1).padStart(2,'0');
        const y = date.getUTCFullYear();
        const hh = String(date.getUTCHours()).padStart(2,'0');
        const mm = String(date.getUTCMinutes()).padStart(2,'0');
        return `${d}/${m}/${y} ${hh}:${mm}`;
    }

    function renderTable(data) {
        if (!data || data.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="10" class="text-center text-muted py-4">No se encontraron archivos</td></tr>`;
            return;
        }

        // Separar pólizas y cuotas
        const polizas = data.filter(r => r.tipo_origen === 'POLIZA');
        const cuotas  = data.filter(r => r.tipo_origen === 'CUOTA');

        // Indexar cuotas por póliza padre
        const cuotasByPoliza = {};
        cuotas.forEach(c => {
            const padre = c.poliza_padre_id || '__sin_padre__';
            if (!cuotasByPoliza[padre]) cuotasByPoliza[padre] = [];
            cuotasByPoliza[padre].push(c);
        });

        let html = '';

        polizas.forEach(row => {
            const hijos = cuotasByPoliza[row.identificador] || [];
            const hasHijos = hijos.length > 0;
            const toggleId = `toggle-${row.identificador.replace(/[^a-z0-9]/gi,'_')}`;

            html += `
            <tr class="poliza-row ${hasHijos ? 'has-children' : ''}" data-toggle="${toggleId}">
                <td class="text-center">
                    <div class="d-flex align-items-center justify-content-center gap-1">
                        ${hasHijos ? `
                        <button class="btn btn-sm btn-link p-0 text-secondary btn-toggle-children"
                                data-target="${toggleId}" title="Ver cuotas con archivos">
                            <i class="bi bi-chevron-right transition-icon"></i>
                        </button>` : '<span style="width:22px;display:inline-block;"></span>'}
                        <button class="btn btn-outline-primary btn-sm btn-zip-group"
                                data-id="${row.identificador}"
                                data-type="${row.tipo_origen}"
                                title="Descargar archivos de póliza">
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

            // Filas hijas (cuotas) — ocultas por defecto
            hijos.forEach(c => {
                html += `
                <tr class="cuota-child-row d-none" data-parent="${toggleId}">
                    <td class="text-center ps-4">
                        <div class="d-flex align-items-center justify-content-center gap-1 ps-3">
                            <i class="bi bi-arrow-return-right text-muted me-1"></i>
                            <button class="btn btn-outline-success btn-sm btn-zip-group"
                                    data-id="${c.cuota_id}"
                                    data-type="CUOTA"
                                    title="Descargar archivos de cuota">
                                <i class="bi-file-zip"></i>
                            </button>
                        </div>
                    </td>
                    <td><span class="badge bg-success text-white">CUOTA</span></td>
                    <td class="text-muted small">
                        <span class="fw-semibold">${c.cupon || ('ID: ' + c.cuota_id)}</span>
                    </td>
                    <td class="small text-truncate" style="max-width:260px;" title="${c.contratante||''}">${c.contratante||'-'}</td>
                    <td class="small text-muted">${c.ramo||'-'}</td>
                    <td class="small text-muted">${c.producto||'-'}</td>
                    <td class="small text-muted">${c.compania||'-'}</td>
                    <td class="small text-muted">${c.usuario||'-'}</td>
                    <td class="text-center"><span class="badge bg-secondary">${c.cantidad_archivos||0}</span></td>
                    <td class="small text-muted">${formatFecha(c.ultima_fecha)}</td>
                </tr>`;
            });
        });

        // Cuotas sin póliza padre en el resultado (por si el padre no tiene archivos)
        const cuotasHuerfanas = cuotasByPoliza['__sin_padre__'] || [];
        cuotasHuerfanas.forEach(c => {
            html += `
            <tr class="cuota-child-row">
                <td class="text-center">
                    <button class="btn btn-outline-success btn-sm btn-zip-group"
                            data-id="${c.cuota_id}"
                            data-type="CUOTA"
                            title="Descargar archivos de cuota">
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

        // Remove any stray modal backdrops that might block interactions
        try {
            document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
            // Ensure body scroll / pointer-events restored
            document.body.style.overflow = '';
            document.body.style.pointerEvents = '';
        } catch (ignore) {}

        // ---- Toggle expandir/colapsar filas hijas ----
        document.querySelectorAll('.btn-toggle-children').forEach(btn => {
            btn.addEventListener('click', function() {
                const target = this.dataset.target;
                const icon   = this.querySelector('.transition-icon');
                const childs = tableBody.querySelectorAll(`[data-parent="${target}"]`);
                const isOpen = !childs[0].classList.contains('d-none');
                childs.forEach(tr => tr.classList.toggle('d-none', isOpen));
                if (icon) {
                    icon.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(90deg)';
                }
            });
        });

        // ---- Descarga ZIP ----
        document.querySelectorAll('.btn-zip-group').forEach(btn => {
            btn.addEventListener('click', function() {
                const id   = this.dataset.id;
                const type = this.dataset.type;
                window.location.href = `/api/reportes/download-zip?identificador=${encodeURIComponent(id)}&tipo=${encodeURIComponent(type)}`;
            });
        });
    }
});
