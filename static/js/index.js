document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const exportBtn = document.getElementById('exportPdfBtn');
    // usar celda de tabla si existe; si no, usa div anterior
    const statusEl = document.getElementById('tblStatus') || document.getElementById('uploadStatus');
    const section = document.getElementById('extractedDataSection');
    const tblFileNameEl = document.getElementById('tblFileName');
    const excelBody = document.getElementById('excelTableBody');

    let lastPdfUrl = null; // URL del último PDF subido

    function addExcelRow(ex) {
        if (!excelBody) return;
        const tr = document.createElement('tr');
        const cols = [
            ex.poliza,
            ex.ramo,
            ex.vigencia_desde,
            ex.vigencia_hasta,
            ex.sede,
            ex.contratante,
            ex.direccion,
            ex.codigo_sbs
        ];
        cols.forEach(val => {
            const td = document.createElement('td');
            td.textContent = (val && String(val).trim()) ? val : '-';
            tr.appendChild(td);
        });
        excelBody.appendChild(tr);
    }

    uploadBtn?.addEventListener('click', async () => {
        const file = fileInput?.files?.[0];
        if (!file) {
            statusEl.textContent = 'Selecciona un archivo.';
            statusEl.className = 'text-danger mt-2';
            return;
        }

        statusEl.textContent = 'Subiendo...';
        statusEl.className = 'text-muted mt-2';

        try {
            const formData = new FormData();
            formData.append('file', file);

            const resp = await fetch('/upload', { method: 'POST', body: formData });
            const data = await resp.json();

            if (resp.ok) {
                statusEl.textContent = `OK`;
                statusEl.className = 'text-success mt-2';
                fileInput.value = '';
                if (tblFileNameEl) tblFileNameEl.textContent = data.filename || file.name;

                // Construye la URL pública al PDF en static/uploads
                if (data.filename) {
                    lastPdfUrl = `/static/uploads/${data.filename}`;
                }

                // Tolerar ambos esquemas: 'extracted' y 'fields'
                const ex = (data.extracted ?? data.fields ?? {});

                addExcelRow(ex);

                const hasValue = Object.values(ex).some(v => typeof v === 'string' && v.trim().length > 0);
                if (hasValue) section?.classList.remove('d-none');
            } else {
                statusEl.textContent = `Error: ${data.error || 'Error al subir'}`;
                statusEl.className = 'text-danger mt-2';
            }
        } catch {
            statusEl.textContent = 'Error de red al subir.';
            statusEl.className = 'text-danger mt-2';
        }
    });

    exportBtn?.addEventListener('click', () => {
        if (lastPdfUrl) {
            window.open(lastPdfUrl, '_blank');
        } else {
            // feedback si no hay PDF aún
            const statusEl = document.getElementById('tblStatus') || document.getElementById('uploadStatus');
            if (statusEl) {
                statusEl.textContent = 'Primero sube un PDF para visualizar.';
                statusEl.className = 'text-warning mt-2';
            } else {
                alert('Primero sube un PDF para visualizar.');
            }
        }
    });
});