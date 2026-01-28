
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const btnDownloadAll = document.getElementById('btnDownloadAll');
    const tableBody = document.querySelector('#filesTable tbody');
    const pdfModal = new bootstrap.Modal(document.getElementById('pdfModal'));
    const pdfFrame = document.getElementById('pdfFrame');
    const pdfModalTitle = document.getElementById('pdfModalTitle');

    let debounceTimer;

    // Initial Load
    fetchFiles();

    // Search Handler
    searchInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            fetchFiles(this.value);
        }, 300);
    });

    // Download All Handler
    if (btnDownloadAll) {
        btnDownloadAll.addEventListener('click', function() {
            const query = searchInput.value;
            window.location.href = `/api/reportes/download-zip?search=${encodeURIComponent(query)}`;
        });
    }

    async function fetchFiles(query = '') {
        try {
            const url = `/api/reportes/archivos-poliza?search=${encodeURIComponent(query)}`;
            const response = await fetch(url);
            const data = await response.json();
            renderTable(data);
        } catch (error) {
            console.error('Error loading files:', error);
            tableBody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Error cargando datos</td></tr>`;
        }
    }

    function renderTable(data) {
        if (!data || data.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="10" class="text-center text-muted py-4">No se encontraron archivos</td></tr>`;
            return;
        }

        tableBody.innerHTML = data.map(row => {
            const contratante = row.contratante || '-';
            const ramo = row.ramo || '-';
            const producto = row.producto || '-';
            const compania = row.compania || '-';
            const usuario = row.usuario || '-';
            
            // Format date
            let fecha = '-';
            if (row.ultima_fecha) {
                const date = new Date(row.ultima_fecha);
                if (!isNaN(date.getTime())) {
                    const day = String(date.getUTCDate()).padStart(2, '0');
                    const month = String(date.getUTCMonth() + 1).padStart(2, '0');
                    const year = date.getUTCFullYear();
                    const hours = String(date.getUTCHours()).padStart(2, '0');
                    const minutes = String(date.getUTCMinutes()).padStart(2, '0');
                    fecha = `${day}/${month}/${year} ${hours}:${minutes}`;
                } else {
                    fecha = row.ultima_fecha;
                }
            }
            
            return `
                <tr>
                    <td class="text-center">
                        <button class="btn btn-outline-primary btn-sm btn-zip-group" 
                                data-id="${row.identificador}" 
                                data-type="${row.tipo_origen}"
                                title="Descargar todos los archivos">
                            <i class="bi-file-zip"></i>
                        </button>
                    </td>
                    <td><span class="badge bg-light text-dark border">${row.tipo_origen || '-'}</span></td>
                    <td class="fw-bold">${row.identificador || '-'}</td>
                    <td class="small text-truncate" style="max-width: 300px;" title="${contratante}">${contratante}</td>
                    <td class="small text-muted">${ramo}</td>
                    <td class="small text-muted">${producto}</td>
                    <td class="small text-muted">${compania}</td>
                    <td class="small text-muted">${usuario}</td>
                    <td class="text-center"><span class="badge bg-secondary">${row.cantidad_archivos || 0}</span></td>
                    <td class="small text-muted">${fecha}</td>
                </tr>
            `;
        }).join('');

        // Attach event listeners to buttons
        document.querySelectorAll('.btn-zip-group').forEach(btn => {
            btn.addEventListener('click', function() {
                const id = this.dataset.id;
                const type = this.dataset.type;
                window.location.href = `/api/reportes/download-zip?identificador=${encodeURIComponent(id)}&tipo=${encodeURIComponent(type)}`;
            });
        });
    }
});
