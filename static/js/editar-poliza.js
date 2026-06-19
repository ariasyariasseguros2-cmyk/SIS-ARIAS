(function () {
    function initEditarPoliza(root) {
        const scope = root || document;
        const form = scope.querySelector('#editPolicyForm');
        if (form && form.dataset && form.dataset.editarPolizaInit === '1') return;
        if (form && form.dataset) form.dataset.editarPolizaInit = '1';

        console.log('editar-poliza.js loaded');

        const q = (id) => scope.querySelector(`#${id}`);
        const normalize = (v) => (v ?? '').toString().trim().toLowerCase();

        const setupSearchableSelect = (select, placeholder) => {
            if (!select || select.dataset.searchableInit === '1') return;
            select.dataset.searchableInit = '1';

            const wrapper = document.createElement('div');
            wrapper.className = 'position-relative';

            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'form-control';
            input.placeholder = placeholder;
            input.autocomplete = 'off';
            input.setAttribute('aria-label', placeholder);

            const dropdown = document.createElement('div');
            dropdown.className = 'list-group position-absolute w-100 shadow-sm d-none';
            dropdown.style.top = 'calc(100% + 4px)';
            dropdown.style.left = '0';
            dropdown.style.maxHeight = '240px';
            dropdown.style.overflowY = 'auto';
            dropdown.style.zIndex = '1060';

            const renderOptions = (term = '') => {
                const filter = normalize(term);
                const options = Array.from(select.options).filter(opt => opt.value !== '');
                const matches = options.filter(opt => normalize(opt.text).includes(filter));

                dropdown.innerHTML = '';

                if (matches.length === 0) {
                    const empty = document.createElement('div');
                    empty.className = 'list-group-item text-muted small';
                    empty.textContent = 'No se encontraron resultados';
                    dropdown.appendChild(empty);
                    dropdown.classList.remove('d-none');
                    return;
                }

                matches.slice(0, 100).forEach(opt => {
                    const item = document.createElement('button');
                    item.type = 'button';
                    item.className = `list-group-item list-group-item-action${opt.selected ? ' active' : ''}`;
                    item.textContent = opt.text;
                    item.addEventListener('mousedown', (e) => {
                        e.preventDefault();
                        select.value = opt.value;
                        input.value = opt.text;
                        dropdown.classList.add('d-none');
                        select.dispatchEvent(new Event('input', { bubbles: true }));
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                    });
                    dropdown.appendChild(item);
                });

                dropdown.classList.remove('d-none');
            };

            const syncInputFromSelect = () => {
                const selectedOption = select.options[select.selectedIndex];
                input.value = selectedOption && selectedOption.value !== '' ? selectedOption.text : '';
            };

            select.parentNode.insertBefore(wrapper, select);
            wrapper.appendChild(input);
            wrapper.appendChild(dropdown);
            wrapper.appendChild(select);
            select.classList.add('d-none');

            syncInputFromSelect();

            input.addEventListener('focus', () => renderOptions(input.value));
            input.addEventListener('click', () => renderOptions(input.value));
            input.addEventListener('input', () => renderOptions(input.value));
            input.addEventListener('blur', () => {
                window.setTimeout(() => {
                    dropdown.classList.add('d-none');
                    syncInputFromSelect();
                }, 150);
            });
            select.addEventListener('change', syncInputFromSelect);
        };

        setupSearchableSelect(q('contratante'), 'Buscar contratante...');

        // Lógica para filtrar productos por ramo
        const selectRamo = q('ramo');
        const selectProducto = q('producto');
        
        if (selectRamo && selectProducto) {
            let lastRamoN = normalize(selectRamo.value);

            const sortSelect = (select) => {
                const options = Array.from(select.options);
                const firstOption = options.shift(); // Preservar "Selecciona..."
                options.sort((a, b) => a.text.localeCompare(b.text));
                select.innerHTML = '';
                if (firstOption) select.appendChild(firstOption);
                options.forEach(opt => select.appendChild(opt));
            };

            const filterProducts = () => {
                const selectedRamo = selectRamo.value;
                const selectedRamoN = normalize(selectedRamo);

                // Si el usuario cambió el ramo y el producto ya no corresponde, resetear.
                // En la carga inicial NO reseteamos para evitar "desaparecer" el producto guardado si hay inconsistencias en BD.
                const currentOption = selectProducto.options[selectProducto.selectedIndex];
                const currentProductRamoN = normalize(currentOption ? currentOption.getAttribute('data-ramo') : '');
                if (lastRamoN !== selectedRamoN && selectedRamoN && currentProductRamoN && currentProductRamoN !== selectedRamoN) {
                    selectProducto.value = "";
                }

                const options = selectProducto.querySelectorAll('option');
                options.forEach(opt => {
                    if (opt.value === "") return;
                    const ramoOptN = normalize(opt.getAttribute('data-ramo'));
                    const matches = !selectedRamoN || ramoOptN === selectedRamoN;
                    const keepVisible = matches || opt.selected;
                    opt.hidden = !keepVisible;
                    opt.disabled = !keepVisible;
                });

                lastRamoN = selectedRamoN;
            };
            
            selectRamo.addEventListener('change', filterProducts);
            sortSelect(selectRamo);
            sortSelect(selectProducto);
            // Ejecutar al inicio para filtrar si ya hay un ramo seleccionado
            filterProducts();
        }

        const btnGuardar = q('btnGuardar');
        if (btnGuardar) {
            console.log('Button btnGuardar found');
            btnGuardar.addEventListener('click', async (e) => {
                e.preventDefault();
                console.log('Button Guardar clicked');

                const data = {
                    idPoliza: q('idPoliza').value,
                    cliente_id: q('contratante').value,
                    poliza: q('poliza').value,
                    asegurado: q('asegurado').value,
                    sub_agente: q('subAgente').value,
                    cia: q('compania').value,
                    ramo: q('ramo').value,
                    ramos_producto: q('producto').value,
                    porc_compania: q('comisionCompania').value,
                    porc_subagente: q('comisionSubAgente').value,
                    motivo: q('tipoVigencia').value,
                    tipo_vigencia: q('tipoVigencia').value,
                    endosatario: q('endosatario').value,
                    vig_desde: q('vigenciaInicio').value,
                    vig_hasta: q('vigenciaFin').value,
                    moneda: q('moneda').value,
                    asegurada: q('descripcion').value,
                    ejecutivo: q('ejecutivoCuenta').value,
                    observacion: q('masInformacion').value
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
                        headers: { 'Content-Type': 'application/json' },
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

        const btnCancelarEdicion = scope.querySelector('.editar-poliza-btn-cancel');
        if (btnCancelarEdicion) {
            btnCancelarEdicion.addEventListener('click', (e) => {
                e.preventDefault();
                const modalEl = btnCancelarEdicion.closest('.modal');
                if (modalEl && window.bootstrap && typeof window.bootstrap.Modal?.getInstance === 'function') {
                    const inst = window.bootstrap.Modal.getInstance(modalEl);
                    if (inst && typeof inst.hide === 'function') {
                        inst.hide();
                        return;
                    }
                }
                window.location.href = '/menu/listado-poliza';
            });
        }

        const polizaId = q('idPoliza')?.value;

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
            const tbody = q('archivosPolizaTbody');
            const tabla = q('tablaArchivosPoliza');
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
                const url = `/uploads/${a.ruta_archivo}`;
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

        const btnAdjuntar = q('btnAdjuntarArchivo');
        const archivoInput = q('archivoPolizaInput');
        const panel = q('panelArchivoSeleccionado');
        const spanNombre = q('nombreArchivoSeleccionado');
        const btnCancelar = q('btnCancelarArchivo');
        const btnSubir = q('btnSubirArchivo');
        const progress = q('inlineArchivoProgress');

        if (btnAdjuntar && archivoInput) {
            btnAdjuntar.addEventListener('click', () => archivoInput.click());

            archivoInput.addEventListener('change', () => {
                const file = archivoInput.files[0];
                if (!file) return;
                spanNombre.textContent = file.name;
                const sinExt = file.name.replace(/\.[^/.]+$/, '');
                q('inlineNombreDocumento').value = sinExt;
                q('inlineTipoDocumento').value = 'ARCHIVO_EXTRA';
                panel.classList.remove('d-none');
            });
        }

        if (btnCancelar) {
            btnCancelar.addEventListener('click', () => {
                panel.classList.add('d-none');
                archivoInput.value = '';
                q('inlineNombreDocumento').value = '';
                q('inlineTipoDocumento').value = '';
            });
        }

        if (btnSubir) {
            btnSubir.addEventListener('click', async () => {
                const tipo = q('inlineTipoDocumento').value;
                const nombre = q('inlineNombreDocumento').value.trim();
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

                const numeroPoliza = q('poliza').value || '';
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

        cargarArchivos();
    }

    window.initEditarPoliza = initEditarPoliza;
    document.addEventListener('DOMContentLoaded', () => initEditarPoliza(document));
})();
