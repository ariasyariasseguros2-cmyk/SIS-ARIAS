document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const tableBody = document.querySelector('#filesTable tbody');
    const pdfModal  = document.getElementById('pdfModal') ? new bootstrap.Modal(document.getElementById('pdfModal')) : null;

    let debounceTimer;

    // Initial Load
    fetchFiles();

    // Search Handler
    searchInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => fetchFiles(this.value), 300);
    });

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
