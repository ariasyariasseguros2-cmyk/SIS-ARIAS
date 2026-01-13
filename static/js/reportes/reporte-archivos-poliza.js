
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
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
            tableBody.innerHTML = `<tr><td colspan="8" class="text-center text-muted py-4">No se encontraron archivos</td></tr>`;
            return;
        }

        tableBody.innerHTML = data.map(row => {
            // Determine "Concepto" based on Tipo Doc or just mirror it as requested
            const concepto = (row.tipo_doc || '').toUpperCase();
            const avisoCob = row.aviso_cob || '-';
            
            // Build file url - assuming uploads are served from /uploads/
            // Note: row.ruta_archivo might be "uploads/file.pdf" or just "file.pdf"
            // We'll fix the path client side if needed, but backend usually stores relative path.
            let fileUrl = row.ruta_archivo;
            if (!fileUrl.startsWith('/') && !fileUrl.startsWith('http')) {
                fileUrl = '/' + fileUrl; 
            }

            return `
                <tr>
                    <td class="text-center">
                        <button class="btn btn-sm btn-outline-danger btn-pdf" 
                                data-url="${fileUrl}" 
                                data-name="${row.nombre_original || 'Documento'}">
                            <i class="bi-file-earmark-pdf-fill"></i>
                        </button>
                    </td>
                    <td>${avisoCob}</td>
                    <td>${row.vig_desde || '-'}</td>
                    <td>${row.vig_hasta || '-'}</td>
                    <td>${row.tipo_doc || '-'}</td>
                    <td>${concepto}</td>
                    <td class="small text-muted">${row.poliza || '-'}</td>
                    <td class="small text-truncate" style="max-width: 200px;" title="${row.contratante}">${row.contratante || '-'}</td>
                </tr>
            `;
        }).join('');

        // Attach event listeners to buttons
        document.querySelectorAll('.btn-pdf').forEach(btn => {
            btn.addEventListener('click', function() {
                const url = this.dataset.url;
                const name = this.dataset.name;
                
                pdfFrame.src = url;
                pdfModalTitle.textContent = name;
                pdfModal.show();
            });
        });
    }
});
