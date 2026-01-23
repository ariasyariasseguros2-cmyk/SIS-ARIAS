document.addEventListener('DOMContentLoaded', function() {
    const tableBody = document.querySelector('#filesClientTable tbody');
    const pdfModal = new bootstrap.Modal(document.getElementById('pdfModalClient'));
    const pdfFrame = document.getElementById('pdfFrameClient');

    const params = new URLSearchParams(window.location.search);
    const cliente_id = params.get('cliente_id') || window.clienteId || '';

    if (!cliente_id) {
        tableBody.innerHTML = `<tr><td colspan="3" class="text-center text-danger">Cliente no especificado</td></tr>`;
        return;
    }

    fetchFiles(cliente_id);

    async function fetchFiles(clienteId) {
        try {
            const url = `/api/reportes/archivos-cliente?cliente_id=${encodeURIComponent(clienteId)}`;
            const resp = await fetch(url);
            const data = await resp.json();
            renderTable(data);
        } catch (err) {
            console.error('Error cargando archivos cliente', err);
            tableBody.innerHTML = `<tr><td colspan="3" class="text-center text-danger">Error cargando datos</td></tr>`;
        }
    }

    function renderTable(data) {
        if (!data || data.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="3" class="text-center text-muted py-4">No se encontraron archivos</td></tr>`;
            return;
        }

        tableBody.innerHTML = data.map(row => {
            const nombre = row.nombre_original || (row.ruta_archivo ? row.ruta_archivo.split('/').pop() : 'Archivo');
            const fecha = row.creado_en || '';
            return `
                <tr>
                    <td class="text-center">
                        <div class="d-flex gap-2 justify-content-center">
                            <button class="btn btn-outline-secondary btn-sm btn-view-client-file" data-id="${row.idArchivo}" title="Ver archivo"><i class="bi-eye"></i></button>
                            <a class="btn btn-outline-primary btn-sm btn-download-client-file" href="/reportes/archivo-cliente/download?idArchivo=${row.idArchivo}" title="Descargar archivo"><i class="bi-download"></i></a>
                        </div>
                    </td>
                    <td class="small text-truncate" style="max-width: 500px;">${nombre}</td>
                    <td class="small text-muted">${fecha}</td>
                </tr>
            `;
        }).join('');

        document.querySelectorAll('.btn-view-client-file').forEach(btn => {
            btn.addEventListener('click', function() {
                const id = this.dataset.id;
                openFile(id);
            });
        });

        // download links are plain anchors, no JS handlers required
    }

    function openFile(idArchivo) {
        pdfFrame.src = `/reportes/archivo-cliente?id=${encodeURIComponent(idArchivo)}`;
        pdfModal.show();
    }

});
