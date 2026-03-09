document.addEventListener('DOMContentLoaded', () => {
    console.log('editar-poliza.js loaded');

    // ─── Guardar póliza ────────────────────────────────────────────────────────
    const btnGuardar = document.getElementById('btnGuardar');
    if (btnGuardar) {
        console.log('Button btnGuardar found');
        btnGuardar.addEventListener('click', async (e) => {
            e.preventDefault();
            console.log('Button Guardar clicked');
            
            const data = {
                idPoliza: document.getElementById('idPoliza').value,
                poliza: document.getElementById('poliza').value,
                asegurado: document.getElementById('asegurado').value,
                sub_agente: document.getElementById('subAgente').value,
                cia: document.getElementById('compania').value,
                ramo: document.getElementById('ramo').value,
                ramos_producto: document.getElementById('producto').value,
                porc_compania: document.getElementById('comisionCompania').value,
                porc_subagente: document.getElementById('comisionSubAgente').value,
                motivo: document.getElementById('tipoVigencia').value,
                tipo_vigencia: document.getElementById('tipoVigencia').value,
                endosatario: document.getElementById('endosatario').value,
                vig_desde: document.getElementById('vigenciaInicio').value,
                vig_hasta: document.getElementById('vigenciaFin').value,
                moneda: document.getElementById('moneda').value,
                asegurada: document.getElementById('descripcion').value,
                ejecutivo: document.getElementById('ejecutivoCuenta').value,
                observacion: document.getElementById('masInformacion').value
            };

            if (!data.poliza || !data.cia || !data.ramo) {
                Swal.fire('Atención', 'Por favor complete los campos obligatorios (Póliza, Compañía, Ramo)', 'warning');
                return;
            }

            try {
                btnGuardar.disabled = true;
                btnGuardar.textContent = 'Guardando...';

                const resp = await fetch('/polizas/update', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const res = await resp.json();
                
                if (resp.ok && res.ok) {
                    Swal.fire('Guardado', 'Póliza actualizada correctamente', 'success').then(() => {
                        window.location.href = '/menu/listado-poliza';
                    });
                } else {
                    Swal.fire('Error', res.error || 'No se pudo actualizar', 'error');
                    btnGuardar.disabled = false;
                    btnGuardar.textContent = 'Guardar';
                }
            } catch (e) {
                console.error(e);
                Swal.fire('Error', 'Error de red', 'error');
                btnGuardar.disabled = false;
                btnGuardar.textContent = 'Guardar';
            }
        });
    }

    // ─── Archivos de póliza ────────────────────────────────────────────────────
    const polizaId = document.getElementById('idPoliza')?.value;

    async function cargarArchivos() {
        if (!polizaId) return;
        try {
            const resp = await fetch(`/api/polizas/archivos/${polizaId}`);
            const res = await resp.json();
            if (res.ok) renderArchivos(res.archivos || []);
        } catch (e) {
            console.error('Error cargando archivos:', e);
        }
    }

    function renderArchivos(archivos) {
        const tbody = document.getElementById('archivosPolizaTbody');
        const tabla = document.getElementById('tablaArchivosPoliza');
        if (!tbody || !tabla) return;

        tbody.innerHTML = '';

        if (archivos.length === 0) {
            tabla.classList.add('d-none');
            return;
        }

        tabla.classList.remove('d-none');

        const tipoLabels = {
            'PROFORMA': '<span class="badge badge-soft-proforma">Proforma</span>',
            'ARCHIVO_EXTRA': '<span class="badge badge-soft-extra">Archivo extra</span>',
        };

        archivos.forEach((a, idx) => {
            const tipoBadge = tipoLabels[a.origen] || `<span class="badge bg-light text-dark">${a.origen || '-'}</span>`;
            const url = `/static/uploads/${a.ruta_archivo}`;
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${idx + 1}</td>
                <td>
                    <a href="${url}" target="_blank" class="text-decoration-none">
                        <i class="bi-file-earmark me-1"></i>${a.nombre_original || '-'}
                    </a>
                </td>
                <td>${tipoBadge}</td>
                <td><small class="text-muted">${a.creado_en || ''}</small></td>
                <td>
                    <button type="button" class="btn btn-sm btn-outline-danger btn-eliminar-archivo"
                        data-id="${a.idArchivo}" title="Eliminar">
                        <i class="bi-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        tbody.querySelectorAll('.btn-eliminar-archivo').forEach(btn => {
            btn.addEventListener('click', async () => {
                const id = btn.dataset.id;
                const confirmResult = await Swal.fire({
                    title: '¿Eliminar archivo?',
                    text: 'Esta acción no se puede deshacer.',
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonText: 'Sí, eliminar',
                    cancelButtonText: 'Cancelar',
                    confirmButtonColor: '#dc3545'
                });
                if (!confirmResult.isConfirmed) return;
                try {
                    const r = await fetch(`/api/polizas/archivos/delete/${id}`, { method: 'DELETE' });
                    const res = await r.json();
                    if (res.ok) {
                        await cargarArchivos();
                    } else {
                        Swal.fire('Error', res.error || 'No se pudo eliminar', 'error');
                    }
                } catch (e) {
                    Swal.fire('Error', 'Error de red', 'error');
                }
            });
        });
    }

    // ── Flujo inline: botón → input file oculto → panel de confirmación ──────
    const btnAdjuntar = document.getElementById('btnAdjuntarArchivo');
    const archivoInput = document.getElementById('archivoPolizaInput');
    const panel = document.getElementById('panelArchivoSeleccionado');
    const spanNombre = document.getElementById('nombreArchivoSeleccionado');
    const btnCancelar = document.getElementById('btnCancelarArchivo');
    const btnSubir = document.getElementById('btnSubirArchivo');
    const progress = document.getElementById('inlineArchivoProgress');

    if (btnAdjuntar && archivoInput) {
        // Clic en "Adjuntar archivo" → abre el selector de archivos del sistema
        btnAdjuntar.addEventListener('click', () => archivoInput.click());

        // Al seleccionar un archivo, muestra el panel inline
        archivoInput.addEventListener('change', () => {
            const file = archivoInput.files[0];
            if (!file) return;
            spanNombre.textContent = file.name;
            // Pre-rellena el nombre con el nombre del archivo (sin extensión)
            const sinExt = file.name.replace(/\.[^/.]+$/, '');
            document.getElementById('inlineNombreDocumento').value = sinExt;
            document.getElementById('inlineTipoDocumento').value = 'ARCHIVO_EXTRA';
            panel.classList.remove('d-none');
        });
    }

    // Cancelar: oculta panel y limpia input
    if (btnCancelar) {
        btnCancelar.addEventListener('click', () => {
            panel.classList.add('d-none');
            archivoInput.value = '';
            document.getElementById('inlineNombreDocumento').value = '';
            document.getElementById('inlineTipoDocumento').value = '';
        });
    }

    // Subir archivo
    if (btnSubir) {
        btnSubir.addEventListener('click', async () => {
            const tipo = document.getElementById('inlineTipoDocumento').value;
            const nombre = document.getElementById('inlineNombreDocumento').value.trim();
            const file = archivoInput.files[0];

            if (!tipo) {
                Swal.fire('Atención', 'Selecciona el tipo de documento', 'warning');
                return;
            }
            if (!nombre) {
                Swal.fire('Atención', 'Ingresa el nombre del documento', 'warning');
                return;
            }
            if (!file) return;

            const numeroPoliza = document.getElementById('poliza').value || '';
            // Preservar la extensión original del archivo
            const extMatch = file.name.match(/\.[^/.]+$/);
            const ext = extMatch ? extMatch[0] : '';
            const nombreConExt = nombre.endsWith(ext) ? nombre : nombre + ext;

            const formData = new FormData();
            formData.append('poliza_id', polizaId);
            formData.append('numero_poliza', numeroPoliza);
            formData.append('tipo_documento', tipo);
            formData.append('nombre_documento', nombreConExt);
            formData.append('archivo', file);

            progress.classList.remove('d-none');
            btnSubir.disabled = true;

            try {
                const resp = await fetch('/api/polizas/upload-archivo', {
                    method: 'POST',
                    body: formData
                });
                const res = await resp.json();

                progress.classList.add('d-none');
                btnSubir.disabled = false;

                if (res.ok) {
                    panel.classList.add('d-none');
                    archivoInput.value = '';
                    await cargarArchivos();
                    Swal.fire({ icon: 'success', title: 'Guardado', text: `"${res.nombre}" subido correctamente`, timer: 2000, showConfirmButton: false });
                } else {
                    Swal.fire('Error', res.error || 'No se pudo guardar el archivo', 'error');
                }
            } catch (e) {
                progress.classList.add('d-none');
                btnSubir.disabled = false;
                Swal.fire('Error', 'Error de red al subir el archivo', 'error');
            }
        });
    }

    // Cargar archivos al iniciar
    cargarArchivos();
});
