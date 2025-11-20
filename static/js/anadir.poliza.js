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

    // NUEVO: elementos para ingreso manual
    const manualFolioInput = document.getElementById('manualFolioInput');
    const manualAddBtn = document.getElementById('manualAddBtn');
    let lastPdfUrl = null; // URL del último PDF subido
    // NUEVO: botón Guardar
    const saveBtn = document.getElementById('saveBoardBtn');
    // MOVER A ÁMBITO SUPERIOR: mapa de proveedor → compañía legible
    const CIA_BY_ISSUER = {
        'MAPFRE': 'MAPFRE',
        'LA_POSITIVA_EPS': 'LA POSITIVA',
        'LA_POSITIVA_VIDA': 'LA POSITIVA',
        'LA_POSITIVA_SEGUROS': 'LA POSITIVA',
    };

    const FIELD_KEYS = [
        'numero_proforma',
        // Eliminado: 'ruc',
        'emision',
        'nro_tramite',
        'vigencia_desde',
        'hasta',
        'poliza',
        'contrato_nro',
        'asegurado',
        'ramo',
        'moneda',
        'prima_neta',
        'prima_total',
        'monto',
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

    // NUEVO: mostrar/ocultar botón Guardar según haya filas
    function updateSaveButtonVisibility() {
        const hasRows = !!excelBody && excelBody.querySelectorAll('tr').length > 0;
        if (saveBtn) saveBtn.classList.toggle('d-none', !hasRows);
    }

    function addExcelRow(ex) {
        if (!excelBody) return;
        const tr = document.createElement('tr');

        // Guardar la URL del PDF asociada a esta fila
        tr.dataset.pdfUrl = lastPdfUrl || '';

        FIELD_KEYS.forEach(key => {
            const td = document.createElement('td');
            // Nuevo: etiqueta el TD con su clave para mapeo seguro
            td.dataset.key = key;
            // Habilitar edición directa en el tablero
            td.contentEditable = 'true';
            // Mostrar en mayúsculas al insertar
            const raw = ex[key];
            const base = (typeof raw === 'string') ? raw : (raw ?? '');
            const val = (typeof base === 'string') ? base.replace(/^\s*:\s*/, '').trim() : base;
            td.textContent = (val || '').toString().toUpperCase();
            tr.appendChild(td);
        });

        // celda de acciones (no editable)
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
                // NUEVO: actualizar visibilidad del botón Guardar tras eliminar
                updateSaveButtonVisibility();
            }
        });
        actionWrap.appendChild(delBtn);
    
        actionTd.appendChild(actionWrap);
        tr.appendChild(actionTd);

        excelBody.appendChild(tr);
        // NUEVO: actualizar visibilidad del botón Guardar
        updateSaveButtonVisibility();
    }

    function startEditRow(tr) {
        currentEditRow = tr;
        FIELD_KEYS.forEach((key) => {
            // Leer por data-key en lugar de índice
            const td = tr.querySelector(`td[data-key="${key}"]`);
            const value = (td?.textContent || '').trim();
            const input = document.getElementById(`edit_${key}`);
            if (input) input.value = value;
        });
        // Solo al abrir el modal, marcar los faltantes en rojo
        markMissingInEditModal();
        editModal?.show();
    }

    // Prellenar el modal sin depender de una fila existente
    function prefillEditFields(ex) {
        FIELD_KEYS.forEach(key => {
            const input = document.getElementById(`edit_${key}`);
            if (!input) return;
            const raw = ex[key];
            const base = (typeof raw === 'string') ? raw : (raw ?? '');
            const val = (typeof base === 'string') ? base.replace(/^\s*:\s*/, '').trim() : base;
            input.value = val || '';
        });
        // Marcar campos requeridos vacíos
        markMissingInEditModal();
    }

    function saveEditModal() {
        if (currentEditRow) {
            FIELD_KEYS.forEach((key) => {
                const input = document.getElementById(`edit_${key}`);
                const newVal = (input?.value || '').trim();
                const td = currentEditRow.querySelector(`td[data-key="${key}"]`);
                if (td) td.textContent = newVal;
            });
            REQUIRED_KEYS.forEach(key => {
                const input = document.getElementById(`edit_${key}`);
                input?.classList.remove('is-invalid');
            });
            editModal?.hide();
            currentEditRow = null;
            return;
        }

        // Sin fila seleccionada: crear una nueva solo si hay folio (no rompe duplicación)
        const ex = {};
        FIELD_KEYS.forEach(key => {
            const input = document.getElementById(`edit_${key}`);
            ex[key] = (input?.value || '').trim();
        });
        const hasFolio = ((ex.poliza || '').length > 0) || ((ex.contrato_nro || '').length > 0);
        if (hasFolio) {
            addExcelRow({ ...ex, hasta: ex.hasta ?? ex.vigencia_hasta ?? '' });
            section?.classList.remove('d-none');
        }
        REQUIRED_KEYS.forEach(key => {
            const input = document.getElementById(`edit_${key}`);
            input?.classList.remove('is-invalid');
        });
        editModal?.hide();
        currentEditRow = null;
    }
    document.getElementById('editSaveBtn')?.addEventListener('click', saveEditModal);

    // NUEVO: agregar fila manual sin abrir modal (en mayúsculas)
    manualAddBtn?.addEventListener('click', () => {
        const folio = (manualFolioInput?.value || '').toUpperCase().trim();
        if (!folio) {
            const s = document.getElementById('tblStatus') || document.getElementById('uploadStatus');
            if (s) {
                s.textContent = 'Escribe un folio (Póliza o Contrato).';
                s.className = 'text-warning mt-2';
            }
            return;
        }
        const ex = {};
        FIELD_KEYS.forEach(k => { ex[k] = ''; });
        ex.poliza = folio; // o usar ex.contrato_nro = folio;

        addExcelRow({ ...ex, hasta: ex.hasta ?? ex.vigencia_hasta ?? '' });
        section?.classList.remove('d-none');
        manualFolioInput.value = '';
    });

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
                let firstUiEx = null;

                // Dentro de uploadBtn?.addEventListener('click', async () => { ... })
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
                
                    // NUEVO: mapa de proveedor → compañía legible
                    // (Usar el mapa global; se quita la redeclaración local)
                    if (!firstUiEx) firstUiEx = uiEx;
                
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
                    // Mostrar tablero y avisar para completar manualmente, sin abrir modal
                    section?.classList.remove('d-none');
                    const s = document.getElementById('tblStatus') || document.getElementById('uploadStatus');
                    if (s) {
                        s.textContent = 'No se detectaron datos. Completa manualmente en el tablero.';
                        s.className = 'text-warning mt-2';
                    }
                    // No abrir modal; el input manual queda disponible
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

    // NUEVO: recolectar las filas del tablero para guardar
    function collectTableItems() {
        const items = [];
        const rows = excelBody ? excelBody.querySelectorAll('tr') : [];
        rows.forEach(tr => {
            const item = {};
            FIELD_KEYS.forEach(key => {
                const td = tr.querySelector(`td[data-key="${key}"]`);
                item[key] = (td?.textContent || '').trim();
            });
            // Si no hay subagente en la fila, tomar del cliente seleccionado
            if (!item.subagente) {
                item.subagente = (window.selectedCliente && window.selectedCliente.subagente) || '';
            }
            // NUEVO: si no hay compañía en la fila, inferir desde el selector de proveedor
            const issuer = (docSourceSelect?.value || '').trim();
            if (!item.cia) {
                item.cia = CIA_BY_ISSUER[issuer] || issuer || '';
            }
            items.push(item);
        });
        return items;
    }

    // NUEVO: reiniciar tablero y estado de carga tras guardar
    function resetBoardUI() {
        try {
            excelBody && (excelBody.innerHTML = '');
            updateSaveButtonVisibility();
            section?.classList.add('d-none');
            if (tblFileNameEl) tblFileNameEl.textContent = '-';
            if (statusEl) { statusEl.textContent = '-'; statusEl.className = ''; }
            if (fileInput) fileInput.value = '';
            if (manualFolioInput) manualFolioInput.value = '';
            if (docSourceSelect) docSourceSelect.value = '';
            lastPdfUrl = null;
        } catch (e) {
            console.warn('resetBoardUI error:', e);
        }
    }

    // NUEVO: enviar al backend y reiniciar tablero
    saveBtn?.addEventListener('click', async () => {
        const items = collectTableItems();
        if (!items.length) {
            statusEl.textContent = 'No hay filas para guardar.';
            statusEl.className = 'text-warning mt-2';
            return;
        }
        statusEl.textContent = 'Guardando...';
        statusEl.className = 'text-muted mt-2';

        try {
            const resp = await fetch('/polizas/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    items,
                    selected: window.selectedCliente || {}
                }),
            });
            const data = await resp.json();
            if (resp.ok && data.ok) {
                statusEl.textContent = `Guardado: ${data.saved ?? items.length} filas.`;
                statusEl.className = 'text-success mt-2';
                resetBoardUI();

                // Si quieres redirigir al tablero de Pólizas al terminar:
                // window.location.href = '/menu/polizas';
            } else {
                const detail = Array.isArray(data.errors) ? data.errors.join('; ') : (data.error || 'Error');
                statusEl.textContent = `Error al guardar: ${detail}`;
                statusEl.className = 'text-danger mt-2';
            }
        } catch (err) {
            statusEl.textContent = 'Error de red al guardar.';
            statusEl.className = 'text-danger mt-2';
        }
    });
});