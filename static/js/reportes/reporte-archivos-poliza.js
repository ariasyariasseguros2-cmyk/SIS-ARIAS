
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
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-4">No se encontraron archivos</td></tr>`;
            return;
        }

        tableBody.innerHTML = data.map(row => {
            const contratante = row.contratante || '-';
            
            // Format date (assuming backend sends 'YYYY-MM-DD HH:MM:SS' or similar)
            let fecha = row.ultima_fecha || '-';
            
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
