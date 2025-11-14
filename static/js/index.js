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
    const FIELD_KEYS = [
        'poliza',
        'ramo',
        'vigencia_desde',
        'vigencia_hasta',
        'sede',
        'contratante',
        'direccion',
        'codigo_sbs'
    ];

    // Modal de edición
    const editModalEl = document.getElementById('editModal');
    let editModal = null;
    if (editModalEl && window.bootstrap) {
        editModal = new bootstrap.Modal(editModalEl);
    }
    let currentEditRow = null;

    function addExcelRow(ex) {
        if (!excelBody) return;
        const tr = document.createElement('tr');

        // celdas de datos (8 columnas)
        FIELD_KEYS.forEach(key => {
            const td = document.createElement('td');
            const val = (ex[key] && String(ex[key]).trim()) ? ex[key] : '-';
            td.textContent = val;
            tr.appendChild(td);
        });

        // celda de acciones
        const actionTd = document.createElement('td');
        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-outline-primary btn-modern';
        editBtn.innerHTML = '<i class="bi bi-pencil-square me-1"></i>Editar';
        editBtn.addEventListener('click', () => startEditRow(tr));
        actionTd.appendChild(editBtn);
        tr.appendChild(actionTd);

        excelBody.appendChild(tr);
    }

    function startEditRow(tr) {
        currentEditRow = tr;
        FIELD_KEYS.forEach((key, i) => {
            const td = tr.cells[i];
            const value = td.textContent === '-' ? '' : td.textContent.trim();
            const input = document.getElementById(`edit_${key}`);
            if (input) input.value = value;
        });
        editModal?.show();
    }

    function saveEditModal() {
        if (!currentEditRow) return;
        FIELD_KEYS.forEach((key, i) => {
            const input = document.getElementById(`edit_${key}`);
            const newVal = (input?.value || '').trim();
            currentEditRow.cells[i].textContent = newVal.length ? newVal : '-';
        });
        editModal?.hide();
        currentEditRow = null;
    }
    document.getElementById('editSaveBtn')?.addEventListener('click', saveEditModal);

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