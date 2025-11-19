document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const exportBtn = document.getElementById('exportPdfBtn');
    // usar celda de tabla si existe; si no, usa div anterior
    const statusEl = document.getElementById('tblStatus') || document.getElementById('uploadStatus');
    const section = document.getElementById('extractedDataSection');
    const tblFileNameEl = document.getElementById('tblFileName');
    const excelBody = document.getElementById('excelTableBody');
    const folioHeaderEl = document.getElementById('folioHeader');
    const docSourceSelect = document.getElementById('docSource');

    let lastPdfUrl = null; // URL del último PDF subido
    const FIELD_KEYS = [
        'numero_proforma',
        // Eliminado: 'ruc',
        'emision',
        'nro_tramite',
        'vigencia_desde',
        'hasta',
        // Mostrar columnas separadas
        'poliza',
        'contrato_nro',
        'contratante',
        // NUEVO: asegurado
        'asegurado',
        'direccion',
        // Eliminiado 'departamento',
        // Eliminiado 'provincia',
        //Eliminiado 'distrito',
        // Eliminiado 'telefonos',
        'ramo',
        'moneda',
        'prima_neta',
        'prima_total',
        'monto',
        'porc_subagente',
        'porc_compania'
    ];
    // Campos que se marcarán en rojo dentro del modal si están vacíos
    const REQUIRED_KEYS = [
        'departamento',
        'provincia',
        'distrito',
        'ramo',
        'prima_total',
        'prima_neta',
        'monto'
    ];

    // Modal de edición
    const editModalEl = document.getElementById('editModal');
    let editModal = null;
    if (editModalEl && window.bootstrap) {
        editModal = new bootstrap.Modal(editModalEl);
    }
    let currentEditRow = null;

    // Marca en rojo (is-invalid) los campos requeridos que estén vacíos en el modal
    function markMissingInEditModal() {
        REQUIRED_KEYS.forEach(key => {
            const input = document.getElementById(`edit_${key}`);
            if (!input) return;
            const isEmpty = (input.value || '').trim() === '';
            input.classList.toggle('is-invalid', isEmpty);
        });
    }

    // Actualiza la marca mientras el usuario escribe (solo dentro del modal)
    function bindEditFieldValidation() {
        REQUIRED_KEYS.forEach(key => {
            const input = document.getElementById(`edit_${key}`);
            if (!input) return;
            input.addEventListener('input', () => {
                const isEmpty = (input.value || '').trim() === '';
                input.classList.toggle('is-invalid', isEmpty);
            });
        });
    }
    bindEditFieldValidation();

    function addExcelRow(ex) {
        if (!excelBody) return;
        const tr = document.createElement('tr');

        // Guardar la URL del PDF asociada a esta fila
        tr.dataset.pdfUrl = lastPdfUrl || '';

        FIELD_KEYS.forEach(key => {
            const td = document.createElement('td');
            const raw = ex[key];
            // Limpia “:” inicial y trim; convierte valores tipo ":" a vacío
            const base = (typeof raw === 'string') ? raw : (raw ?? '');
            const val = (typeof base === 'string') ? base.replace(/^\s*:\s*/, '').trim() : base;
            td.textContent = val || '';
            tr.appendChild(td);
        });

        // celda de acciones
        const actionTd = document.createElement('td');
        const actionWrap = document.createElement('div');
        actionWrap.className = 'actions-stack';
    
        // Ver PDF
        const viewBtn = document.createElement('button');
        viewBtn.className = 'btn action-btn btn-view';
        viewBtn.innerHTML = '<i class="bi bi-file-earmark-pdf"></i><span>Ver PDF</span>';
        viewBtn.addEventListener('click', () => {
            const url = tr.dataset.pdfUrl || lastPdfUrl;
            if (url) {
                window.open(url, '_blank');
            } else {
                const s = document.getElementById('tblStatus') || document.getElementById('uploadStatus');
                if (s) {
                    s.textContent = 'Primero sube un PDF para visualizar.';
                    s.className = 'text-warning mt-2';
                } else {
                    alert('Primero sube un PDF para visualizar.');
                }
            }
        });
        actionWrap.appendChild(viewBtn);
    
        // Editar
        const editBtn = document.createElement('button');
        editBtn.className = 'btn action-btn btn-edit';
        editBtn.innerHTML = '<i class="bi bi-pencil-square"></i><span>Editar</span>';
        editBtn.addEventListener('click', () => startEditRow(tr));
        actionWrap.appendChild(editBtn);
    
        // Eliminar
        const delBtn = document.createElement('button');
        delBtn.className = 'btn action-btn btn-del';
        delBtn.innerHTML = '<i class="bi bi-trash3"></i><span>Eliminar</span>';
        delBtn.addEventListener('click', () => {
            if (confirm('¿Eliminar esta fila?')) {
                tr.remove();
                if (excelBody.querySelectorAll('tr').length === 0) {
                    section?.classList.add('d-none');
                }
            }
        });
        actionWrap.appendChild(delBtn);
    
        actionTd.appendChild(actionWrap);
        tr.appendChild(actionTd);

        excelBody.appendChild(tr);
    }

    function startEditRow(tr) {
        currentEditRow = tr;
        FIELD_KEYS.forEach((key, i) => {
            const td = tr.cells[i];
            const value = td.textContent.trim();
            const input = document.getElementById(`edit_${key}`);
            if (input) input.value = value;
        });
        // Solo al abrir el modal, marcar los faltantes en rojo
        markMissingInEditModal();
        editModal?.show();
    }

    function saveEditModal() {
        if (!currentEditRow) return;
        FIELD_KEYS.forEach((key, i) => {
            const input = document.getElementById(`edit_${key}`);
            const newVal = (input?.value || '').trim();
            currentEditRow.cells[i].textContent = newVal;
        });
        // Limpiar marcas al cerrar para que no queden persistentes
        REQUIRED_KEYS.forEach(key => {
            const input = document.getElementById(`edit_${key}`);
            input?.classList.remove('is-invalid');
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
            if (docSourceSelect) {
                formData.append('issuer', (docSourceSelect.value || '').trim());
            }

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

                // NUEVO: soportar múltiples ítems
                let items = [];
                if (Array.isArray(data.items)) {
                    items = data.items;
                } else if (Array.isArray(data.fields)) {
                    items = data.fields;
                } else if (Array.isArray(data.extracted)) {
                    items = data.extracted;
                } else {
                    const exObj = (data.extracted ?? data.fields ?? {});
                    items = [exObj];
                }

                // Renderizar cada ítem como fila
                let anyShown = false;
                for (const ex of items) {
                    const uiEx = { ...ex, hasta: ex.hasta ?? ex.vigencia_hasta ?? '' };

                    // Si solo se envía folio combinado, mapear a columnas separadas
                    if (!uiEx.poliza && !uiEx.contrato_nro && uiEx.folio_id) {
                        if ((uiEx.folio_label || '').toLowerCase().includes('contrato')) {
                            uiEx.contrato_nro = uiEx.folio_id;
                        } else {
                            uiEx.poliza = uiEx.folio_id;
                        }
                    }
                    uiEx.poliza = uiEx.poliza ?? '';
                    uiEx.contrato_nro = uiEx.contrato_nro ?? '';

                    const hasFolio = ((uiEx.poliza || '').toString().trim().length > 0)
                                  || ((uiEx.contrato_nro || '').toString().trim().length > 0);
                    if (!hasFolio) {
                        // si esta página no tiene folio, la saltamos
                        continue;
                    }

                    addExcelRow(uiEx);
                    anyShown = true;
                }

                if (anyShown) {
                    section?.classList.remove('d-none');
                } else {
                    statusEl.textContent = 'El documento no tiene Póliza ni Contrato.';
                    statusEl.className = 'text-warning mt-2';
                }
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