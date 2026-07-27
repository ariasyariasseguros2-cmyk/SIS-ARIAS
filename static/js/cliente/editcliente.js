/**
 * editcliente.js - Manejo de edición de clientes
 */

(function() {
    'use strict';

    let currentEditingClienteId = null;
    let editDocumentoLookupTimer = null;
    let lastEditDocumentoLookupKey = '';

    function normalizeTipoDocumento(raw) {
        const t = (raw || '').toString().trim().toUpperCase();
        if (!t) return 'DNI';
        if (t.includes('RUC')) return 'RUC';
        if (t.includes('DNI')) return 'DNI';
        if (t.includes('PAS')) return 'PAS';
        if (t.includes('CEX')) return 'CEX';
        if (t === 'CE' || t.includes('EXTRAN') || t.includes('CARNET')) return 'CEX';
        return 'DNI';
    }

    function normalizeText(value) {
        return (value || '')
            .toString()
            .trim()
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toUpperCase();
    }

    function setSelectOptions(selectEl, items, placeholder = 'Seleccionar...') {
        if (!selectEl) return;

        selectEl.innerHTML = '';

        const firstOption = document.createElement('option');
        firstOption.value = '';
        firstOption.textContent = placeholder;
        selectEl.appendChild(firstOption);

        (items || []).forEach(item => {
            const option = document.createElement('option');
            option.value = item;
            option.textContent = item;
            selectEl.appendChild(option);
        });
    }

    function setSelectValueByText(selectEl, value) {
        if (!selectEl) return;

        const target = normalizeText(value);
        const match = Array.from(selectEl.options).find(
            opt => normalizeText(opt.value) === target
        );

        selectEl.value = match ? match.value : '';
    }

    function toggleSelectState(selectEl, enabled) {
        if (!selectEl) return;

        selectEl.disabled = !enabled;
        if (!enabled) {
            selectEl.value = '';
            selectEl.classList.remove('is-valid', 'is-invalid');
        }
    }

    async function loadEditDepartamentos(selectedDepartamento = '') {
        const departamentoEl = document.getElementById('edit_departamento');
        if (!departamentoEl) return;

        try {
            const resp = await fetch('/api/ubigeos/departamentos');
            const result = await resp.json().catch(() => ({}));
            if (!resp.ok || !result.ok) throw new Error('No se pudo cargar departamentos');

            setSelectOptions(departamentoEl, result.departamentos || []);
            toggleSelectState(departamentoEl, true);

            if (selectedDepartamento) {
                setSelectValueByText(departamentoEl, selectedDepartamento);
            }
        } catch (error) {
            console.error('Error cargando departamentos en edición:', error);
            setSelectOptions(departamentoEl, []);
            toggleSelectState(departamentoEl, false);
        }
    }

    async function loadEditProvincias(departamento, selectedProvincia = '') {
        const provinciaEl = document.getElementById('edit_provincia');
        const distritoEl = document.getElementById('edit_distrito');
        if (!provinciaEl || !distritoEl) return;

        setSelectOptions(provinciaEl, []);
        setSelectOptions(distritoEl, []);
        toggleSelectState(distritoEl, false);

        if (!departamento) {
            toggleSelectState(provinciaEl, false);
            return;
        }

        try {
            const qs = new URLSearchParams({ departamento });
            const resp = await fetch(`/api/ubigeos/provincias?${qs.toString()}`);
            const result = await resp.json().catch(() => ({}));
            if (!resp.ok || !result.ok) throw new Error('No se pudo cargar provincias');

            setSelectOptions(provinciaEl, result.provincias || []);
            toggleSelectState(provinciaEl, true);

            if (selectedProvincia) {
                setSelectValueByText(provinciaEl, selectedProvincia);
            }
        } catch (error) {
            console.error('Error cargando provincias en edición:', error);
            setSelectOptions(provinciaEl, []);
            toggleSelectState(provinciaEl, false);
        }
    }

    async function loadEditDistritos(departamento, provincia, selectedDistrito = '') {
        const distritoEl = document.getElementById('edit_distrito');
        if (!distritoEl) return;

        setSelectOptions(distritoEl, []);

        if (!departamento || !provincia) {
            toggleSelectState(distritoEl, false);
            return;
        }

        try {
            const qs = new URLSearchParams({ departamento, provincia });
            const resp = await fetch(`/api/ubigeos/distritos?${qs.toString()}`);
            const result = await resp.json().catch(() => ({}));
            if (!resp.ok || !result.ok) throw new Error('No se pudo cargar distritos');

            setSelectOptions(distritoEl, result.distritos || []);
            toggleSelectState(distritoEl, true);

            if (selectedDistrito) {
                setSelectValueByText(distritoEl, selectedDistrito);
            }
        } catch (error) {
            console.error('Error cargando distritos en edición:', error);
            setSelectOptions(distritoEl, []);
            toggleSelectState(distritoEl, false);
        }
    }

    async function initializeEditUbigeoSelectors(defaults = {}) {
        const departamentoEl = document.getElementById('edit_departamento');
        const provinciaEl = document.getElementById('edit_provincia');
        if (!departamentoEl || !provinciaEl) return;

        await loadEditDepartamentos(defaults.departamento || '');

        const departamentoValue = departamentoEl.value || defaults.departamento || '';
        await loadEditProvincias(departamentoValue, defaults.provincia || '');

        const provinciaValue = provinciaEl.value || defaults.provincia || '';
        await loadEditDistritos(departamentoValue, provinciaValue, defaults.distrito || '');
    }

    function setupEditUbigeoListeners() {
        const departamentoEl = document.getElementById('edit_departamento');
        const provinciaEl = document.getElementById('edit_provincia');
        const distritoEl = document.getElementById('edit_distrito');
        if (!departamentoEl || !provinciaEl || !distritoEl) return;
        if (departamentoEl.dataset.ubigeoBound === '1') return;

        departamentoEl.dataset.ubigeoBound = '1';

        departamentoEl.addEventListener('change', async (e) => {
            const departamento = e.target.value || '';
            await loadEditProvincias(departamento);
        });

        provinciaEl.addEventListener('change', async (e) => {
            const provincia = e.target.value || '';
            await loadEditDistritos(departamentoEl.value || '', provincia);
        });
    }

    function resetEditUbigeoSelectors() {
        const departamentoEl = document.getElementById('edit_departamento');
        const provinciaEl = document.getElementById('edit_provincia');
        const distritoEl = document.getElementById('edit_distrito');

        setSelectOptions(departamentoEl, []);
        setSelectOptions(provinciaEl, []);
        setSelectOptions(distritoEl, []);
        toggleSelectState(departamentoEl, true);
        toggleSelectState(provinciaEl, false);
        toggleSelectState(distritoEl, false);
    }

    function getEditLookupStatusEl() {
        let el = document.getElementById('edit_doc_lookup_status');
        if (el) return el;

        const numeroDoc = document.getElementById('edit_numero_documento');
        const container = numeroDoc?.parentElement;
        if (!container) return null;

        el = document.createElement('div');
        el.id = 'edit_doc_lookup_status';
        el.className = 'form-text small mt-1';
        container.appendChild(el);
        return el;
    }

    function setEditLookupStatus(type, message) {
        const el = getEditLookupStatusEl();
        if (!el) return;

        el.className = 'form-text small mt-1';
        if (type === 'loading') el.classList.add('text-info');
        if (type === 'success') el.classList.add('text-success');
        if (type === 'error') el.classList.add('text-danger');
        if (type === 'warning') el.classList.add('text-warning');
        el.textContent = message || '';
    }

    function applyEditTipoPersona(tipoPersona) {
        const tipoPersonaEl = document.getElementById('edit_tipo_persona');
        if (!tipoPersonaEl || !tipoPersona) return;

        const value = normalizeText(tipoPersona);
        if (value === 'JURIDICA' || value === '2') {
            tipoPersonaEl.value = '2';
        } else if (value) {
            tipoPersonaEl.value = '1';
        }
    }

    async function applyDocumentoLookupToEditForm(data) {
        if (!data) return;

        const razonInput = document.getElementById('edit_razon_social');
        const direccionInput = document.getElementById('edit_direccion');

        if (razonInput && data.razon_social) {
            razonInput.value = data.razon_social;
        }

        if (direccionInput && data.direccion) {
            direccionInput.value = data.direccion;
        }

        applyEditTipoPersona(data.tipo_persona);

        if (data.departamento || data.provincia || data.distrito) {
            await initializeEditUbigeoSelectors({
                departamento: data.departamento || '',
                provincia: data.provincia || '',
                distrito: data.distrito || ''
            });
        }
    }

    async function performEditDocumentoLookup(force = false) {
        const numeroDoc = document.getElementById('edit_numero_documento');
        const tipoDocEl = document.getElementById('edit_tipo_documento');
        if (!numeroDoc || !tipoDocEl) return;

        numeroDoc.value = (numeroDoc.value || '').replace(/[^0-9]/g, '');
        const numero = numeroDoc.value;
        const tipo = normalizeTipoDocumento(tipoDocEl.value || '');
        const expectedLength = tipo === 'RUC' ? 11 : (tipo === 'DNI' ? 8 : 0);

        if (!expectedLength || numero.length !== expectedLength) return;

        const lookupKey = `${tipo}:${numero}`;
        if (!force && lookupKey === lastEditDocumentoLookupKey) return;
        lastEditDocumentoLookupKey = lookupKey;

        setEditLookupStatus('loading', `Consultando ${tipo}...`);

        try {
            const qs = new URLSearchParams({
                tipo_documento: tipo,
                numero_documento: numero
            });
            const resp = await fetch(`/api/clientes/documento-lookup?${qs.toString()}`);
            const result = await resp.json().catch(() => ({}));

            if (!resp.ok || !result.ok) {
                setEditLookupStatus('warning', result.error || 'No se pudo consultar el documento');
                return;
            }

            await applyDocumentoLookupToEditForm(result.data || {});
            setEditLookupStatus('success', `${tipo} consultado correctamente`);
        } catch (error) {
            console.error('Error consultando documento en edición:', error);
            setEditLookupStatus('error', 'Error consultando el documento');
        }
    }

    function scheduleEditDocumentoLookup(force = false) {
        if (editDocumentoLookupTimer) {
            clearTimeout(editDocumentoLookupTimer);
        }

        editDocumentoLookupTimer = setTimeout(() => {
            performEditDocumentoLookup(force);
        }, force ? 0 : 500);
    }

    function setupEditDocumentoLookupListeners() {
        const numeroDoc = document.getElementById('edit_numero_documento');
        const tipoDocEl = document.getElementById('edit_tipo_documento');
        if (!numeroDoc || !tipoDocEl || numeroDoc.dataset.lookupBound === '1') return;

        numeroDoc.dataset.lookupBound = '1';

        numeroDoc.addEventListener('input', () => {
            numeroDoc.value = (numeroDoc.value || '').replace(/[^0-9]/g, '');

            const numero = numeroDoc.value;
            if (numero.length === 8) {
                tipoDocEl.value = 'DNI';
                applyEditTipoPersona('NATURAL');
                scheduleEditDocumentoLookup(false);
            } else if (numero.length === 11) {
                tipoDocEl.value = 'RUC';
                applyEditTipoPersona(numero.startsWith('20') ? 'JURIDICA' : 'NATURAL');
                scheduleEditDocumentoLookup(false);
            }
        });
    }

    /**
     * Inicializar eventos al cargar el DOM
     */
    document.addEventListener('DOMContentLoaded', function() {
        initEditButtons();
        initEditForm();
        setupEditUbigeoListeners();
        setupEditDocumentoLookupListeners();

        const editModalEl = document.getElementById('editClienteModal');
        if (editModalEl) {
            editModalEl.addEventListener('show.bs.modal', () => {
                document.body.classList.add('modal-backdrop-strong');
            });
            editModalEl.addEventListener('hidden.bs.modal', () => {
                document.body.classList.remove('modal-backdrop-strong');
            });
        }
    });

    /**
     * Inicializar botones de editar
     */
    function initEditButtons() {
        document.addEventListener('click', function(e) {
            const btn = e.target.closest('.btn-edit-cliente');
            if (!btn) return;

            const clienteId = btn.getAttribute('data-id');
            if (clienteId) {
                loadClienteData(clienteId);
            }
        });
    }

    /**
     * Cargar datos del cliente para editar
     */
    function loadClienteData(clienteId) {
        // Mostrar loading
        showLoadingModal();

        fetch(`/clientes/detalle/${clienteId}`)
            .then(response => response.json())
            .then(async data => {
                if (data.status === 'success') {
                    currentEditingClienteId = clienteId;
                    await populateEditForm(data.data);
                    hideLoadingModal();

                    const editModal = new bootstrap.Modal(document.getElementById('editClienteModal'));
                    editModal.show();
                } else {
                    hideLoadingModal();
                    showAlert('error', data.message || 'Error al cargar los datos del cliente');
                }
            })
            .catch(error => {
                hideLoadingModal();
                console.error('Error:', error);
                showAlert('error', 'Error al cargar los datos del cliente');
            });
    }

    /**
     * Poblar el formulario de edición con los datos del cliente
     */
    async function populateEditForm(cliente) {
        // Datos básicos
        document.getElementById('edit_idCliente').value = cliente.idCliente || cliente.id || '';
        document.getElementById('edit_tipo_persona').value = cliente.tipo_persona || cliente.tipo_persona_id || '';
        document.getElementById('edit_tipo_documento').value = normalizeTipoDocumento(cliente.tipo_documento || '');
        document.getElementById('edit_numero_documento').value = cliente.numero_documento || '';
        document.getElementById('edit_razon_social').value = cliente.razon_social || '';
        document.getElementById('edit_estado').value = cliente.estado || 'Vigente';
        document.getElementById('edit_profesion').value = cliente.profesion || '';

        // Datos de contacto
        document.getElementById('edit_telefono').value = cliente.telefono || '';
        document.getElementById('edit_celular').value = cliente.celular || '';
        document.getElementById('edit_telefono_sec').value = cliente.telefono_sec || '';
        document.getElementById('edit_email').value = cliente.email || '';

        // Ubicación
        document.getElementById('edit_direccion').value = cliente.direccion || '';
        await initializeEditUbigeoSelectors({
            departamento: cliente.departamento || '',
            provincia: cliente.provincia || '',
            distrito: cliente.distrito || ''
        });

        // Relación comercial
        // Si el servidor devuelve subagente como abreviación o como texto, colocarlo
        document.getElementById('edit_subagente').value = cliente.subagente || cliente.sub_agente || '';
        document.getElementById('edit_grupo_economico').value = cliente.grupo_economico || '';
        document.getElementById('edit_giro_negocio').value = cliente.giro_negocio || '';
        document.getElementById('edit_recomendado_por').value = cliente.recomendado_por || '';

        // Fechas
        document.getElementById('edit_fecha_ingreso').value = cliente.fecha_ingreso || '';
        document.getElementById('edit_fecha_nacimiento').value = cliente.fecha_nacimiento || '';

        // Licencia combinada
       const catEl = document.getElementById('edit_licencia_cat');
        const numEl = document.getElementById('edit_licencia_num');
        let rawLic = (cliente.licenciaConducir || cliente.licencia_num || '').toString().trim();

        if (rawLic) {
            // Si contiene '|' lo separamos
            if (rawLic.includes('|')) {
                const parts = rawLic.split('|').map(s => s.trim());
                const cat = parts[0] || '';
                const num = parts.slice(1).join(' | ') || '';
                if (catEl) {
                    let matched = false;
                    for (const opt of Array.from(catEl.options)) {
                        if (!opt.value) continue;
                        if (cat === opt.value || cat.includes(opt.value) || opt.value.includes(cat)) {
                            catEl.value = opt.value;
                            matched = true;
                            break;
                        }
                    }
                    if (!matched) catEl.value = cat;
                }
                if (numEl) numEl.value = num;
            } else {
                // Intentar detectar categoría buscando coincidencias con los option values dentro del texto
                let matchedCat = '';
                if (catEl) {
                    const lowerRaw = rawLic.toLowerCase();
                    for (const opt of Array.from(catEl.options)) {
                        if (!opt.value) continue;
                        const val = opt.value.toLowerCase();
                        const title = (opt.title || '').toLowerCase();
                        const text = (opt.textContent || '').toLowerCase();
                        if (lowerRaw.indexOf(val) !== -1 || (title && lowerRaw.indexOf(title) !== -1) || (text && lowerRaw.indexOf(text) !== -1)) {
                            matchedCat = opt.value;
                            break;
                        }
                    }
                }

                if (matchedCat) {
                    if (catEl) catEl.value = matchedCat;
                    // quitar la categoría encontrada del texto (primera ocurrencia), luego limpiar separadores para obtener el número
                    const idx = rawLic.toLowerCase().indexOf(matchedCat.toLowerCase());
                    if (idx !== -1) {
                        rawLic = (rawLic.slice(0, idx) + rawLic.slice(idx + matchedCat.length)).trim();
                    }
                    rawLic = rawLic.replace(/[:|\-]/g, ' ').replace(/\s+/g, ' ').trim();
                }

                // Si el resto es numérico, asumir que es el número
                if (numEl) {
                    if (/^\d+$/.test(rawLic)) numEl.value = rawLic;
                    else if (rawLic) numEl.value = rawLic;
                }
            }
        } else {
            // Fallback: si viene separado
            if (catEl && cliente.categoria_licencia) catEl.value = cliente.categoria_licencia || '';
            if (numEl && cliente.licencia_num) numEl.value = cliente.licencia_num || '';
        }
        // Si aún no se detectó categoría, intentar buscar en campos alternativos que pueda devolver la API
        try {
            if (catEl && (!catEl.value || catEl.value === '')) {
                const candidateFields = ['categoria_licencia','categoria','categoria_lic','categoriaLicencia','categoria_licencia_id','categoria_licencia_nombre','categoria_abreviacion','categoria_abbr','licencia_categoria'];
                for (const f of candidateFields) {
                    const v = cliente[f];
                    if (v && v.toString().trim()) {
                        // si coincide con alguna option, usar option.value, sino asignar directamente
                        const lowerV = v.toString().trim().toLowerCase();
                        let matched = false;
                        for (const opt of Array.from(catEl.options)) {
                            if (!opt.value) continue;
                            const optVal = opt.value.toLowerCase();
                            const optTitle = (opt.title || '').toLowerCase();
                            if (optVal === lowerV || lowerV.indexOf(optVal) !== -1 || optVal.indexOf(lowerV) !== -1 || (optTitle && optTitle.indexOf(lowerV) !== -1)) {
                                catEl.value = opt.value;
                                matched = true;
                                break;
                            }
                        }
                        if (!matched) catEl.value = v.toString().trim();
                        break;
                    }
                }
                // si aún no hay categoría, loguear para depuración (no crítico)
                if (!catEl.value) console.debug('No se detectó categoría de licencia para cliente:', cliente.idCliente || cliente.id, 'rawLic:', rawLic, 'cliente fields:', cliente);
            }
        } catch (e) {
            // ignore
        }
         document.getElementById('edit_licencia_venc').value = cliente.licencia_venc || '';

        // Contacto de emergencia
        document.getElementById('edit_recibir_notificaciones').checked = cliente.recibir_notificaciones === 1 || cliente.recibir_notificaciones === true || cliente.recibir_notificaciones === '1';
        document.getElementById('edit_contacto_nombre').value = cliente.contacto_nombre || '';
        document.getElementById('edit_contacto_email').value = cliente.contacto_email || '';
        document.getElementById('edit_contacto_telefono').value = cliente.contacto_telefono || '';

        // Relación Comercial - Referencia (trasladada desde Información Adicional)
        document.getElementById('edit_referencia').value = cliente.referencia || '';

        // Auditoría: fecha y usuario de registro (UTC)
        const userRegEl = document.getElementById('edit_usuario_registro');
        if (userRegEl) {
            const displayName =
                cliente.usuario_registro_display ||
                cliente.usuario_registro ||
                '';
            userRegEl.textContent = displayName;
        }
        const fechaRegEl = document.getElementById('edit_fecha_registro');
        if (fechaRegEl) {
            const fecha = cliente.fecha_registro || cliente.creado_en || '';
            fechaRegEl.textContent = fecha ? (fecha) : '';
        }
    }

    /**
     * Inicializar formulario de edición
     */
    function initEditForm() {
        const btnGuardar = document.getElementById('btnGuardarEditCliente');
        const form = document.getElementById('formEditCliente');

        if (btnGuardar && form) {
            btnGuardar.addEventListener('click', function() {
                if (form.checkValidity()) {
                    saveEditedCliente();
                } else {
                    form.classList.add('was-validated');
                    showAlert('warning', 'Por favor, complete todos los campos requeridos');
                }
            });
        }
    }

    /**
     * Guardar cliente editado
     */
    function saveEditedCliente() {
        const form = document.getElementById('formEditCliente');
        const formData = new FormData(form);

        // Convertir FormData a objeto JSON
        const data = {};
        formData.forEach((value, key) => {
            data[key] = value;
        });

        // Compatibilidad entre versiones: normalizar y enviar aliases de documento.
        data.tipo_documento = normalizeTipoDocumento((data.tipo_documento || data.tipoDocumento || '').trim());
        data.numero_documento = (data.numero_documento || data.nro_documento || data.numeroDocumento || '').trim();
        data.tipoDocumento = data.tipo_documento;
        data.nro_documento = data.numero_documento;
        data.numeroDocumento = data.numero_documento;

        // Agregar el checkbox manualmente
        data.recibir_notificaciones = document.getElementById('edit_recibir_notificaciones').checked ? 1 : 0;

        // Enviar la licencia como campo combinado 'CATEGORIA | NUM' (solo este campo)
        const licenciaCat = document.getElementById('edit_licencia_cat')?.value || '';
        const licenciaNum = document.getElementById('edit_licencia_num')?.value || '';
        if (licenciaCat && licenciaNum) data.licenciaConducir = `${licenciaCat} | ${licenciaNum}`;
        else data.licenciaConducir = licenciaNum || licenciaCat || '';
        // Asegurar no enviar campos separados
        delete data.licencia_num;

        // Deshabilitar botón para evitar múltiples envíos
        const btnGuardar = document.getElementById('btnGuardarEditCliente');
        btnGuardar.disabled = true;
        btnGuardar.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando...';

        fetch('/clientes/edit', {
            method: 'POST',
            credentials: 'same-origin', // enviar cookies de sesión
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                return response.text().then(raw => {
                    try {
                        const body = raw ? JSON.parse(raw) : null;
                        throw { status: response.status, body, raw };
                    } catch (_e) {
                        throw { status: response.status, raw };
                    }
                });
            }
            return response.json();
        })
        .then(data => {
            btnGuardar.disabled = false;
            btnGuardar.innerHTML = '<i class="bi-check-circle me-1"></i>Guardar Cambios';

            if (data.status === 'success' || data.ok === true) {
                showAlert('success', data.message || 'Cliente actualizado correctamente');

                // Cerrar modal
                const editModal = bootstrap.Modal.getInstance(document.getElementById('editClienteModal'));
                if (editModal) {
                    editModal.hide();
                }

                // Recargar la página después de un breve delay
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                const msg = (data && (data.message || (data.body && data.body.message) || (data.errors && data.errors.join(', ')))) || 'Error al actualizar el cliente';
                showAlert('error', msg);
            }
        })
        .catch(error => {
            btnGuardar.disabled = false;
            btnGuardar.innerHTML = '<i class="bi-check-circle me-1"></i>Guardar Cambios';
            console.error('Error:', error);
            if (error && error.status === 401) {
                showAlert('error', 'No autenticado. Por favor inicia sesión.');
            } else {
                const backendMsg = (error && error.body && (error.body.message || error.body.error)) || null;
                const rawMsg = error && typeof error.raw === 'string' ? error.raw.replace(/<[^>]+>/g, ' ').trim() : '';
                const fallbackMsg = rawMsg ? rawMsg.slice(0, 180) : 'Error al actualizar el cliente';
                showAlert('error', backendMsg || fallbackMsg);
            }
        });
    }

    /**
     * Mostrar modal de carga
     */
    function showLoadingModal() {
        // Crear modal de loading si no existe
        let loadingModal = document.getElementById('loadingModal');
        if (!loadingModal) {
            loadingModal = document.createElement('div');
            loadingModal.id = 'loadingModal';
            loadingModal.className = 'modal fade';
            loadingModal.setAttribute('data-bs-backdrop', 'static');
            loadingModal.innerHTML = `
                <div class="modal-dialog modal-sm modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-body text-center py-4">
                            <div class="spinner-border text-primary mb-3" role="status">
                                <span class="visually-hidden">Cargando...</span>
                            </div>
                            <p class="mb-0">Cargando datos...</p>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(loadingModal);
        }

        const modal = bootstrap.Modal.getOrCreateInstance(loadingModal);
        modal.show();
    }

    /**
     * Ocultar modal de carga
     */
    function hideLoadingModal() {
        const loadingModal = document.getElementById('loadingModal');
        if (loadingModal) {
            const modal = bootstrap.Modal.getOrCreateInstance(loadingModal);
            try {
                modal.hide();
            } catch (e) {
                // ignore
            }
            // eliminar del DOM después de un breve delay para evitar problemas con el backdrop
            setTimeout(() => {
                if (loadingModal && loadingModal.parentNode) {
                    loadingModal.parentNode.removeChild(loadingModal);
                }
                // también eliminar cualquier backdrop residual
                const backdrops = document.querySelectorAll('.modal-backdrop');
                backdrops.forEach(b => b.remove());
            }, 300);
        }
    }

    /**
     * Mostrar alerta
     */
    function showAlert(type, message) {
        // Crear contenedor de alertas si no existe
        let alertContainer = document.getElementById('alertContainer');
        if (!alertContainer) {
            alertContainer = document.createElement('div');
            alertContainer.id = 'alertContainer';
            alertContainer.style.position = 'fixed';
            alertContainer.style.top = '20px';
            alertContainer.style.right = '20px';
            alertContainer.style.zIndex = '9999';
            alertContainer.style.maxWidth = '400px';
            document.body.appendChild(alertContainer);
        }

        // Crear alerta
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.setAttribute('role', 'alert');
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        alertContainer.appendChild(alert);

        // Auto-ocultar después de 5 segundos
        setTimeout(() => {
            alert.classList.remove('show');
            setTimeout(() => alert.remove(), 150);
        }, 5000);
    }

    // Limpiar el formulario cuando se cierra el modal
    document.getElementById('editClienteModal')?.addEventListener('hidden.bs.modal', function() {
        const form = document.getElementById('formEditCliente');
        if (form) {
            form.reset();
            form.classList.remove('was-validated');
        }
        resetEditUbigeoSelectors();
        setEditLookupStatus('', '');
        lastEditDocumentoLookupKey = '';
        currentEditingClienteId = null;

        setTimeout(() => {
            try {
                const openModals = document.querySelectorAll('.modal.show');
                if (!openModals || openModals.length === 0) {

                    document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());


                    document.body.classList.remove('modal-open');
                    document.body.style.overflow = '';
                    document.body.style.paddingRight = '';
                }
            } catch (e) {

                console.error('Error limpiando modal/backdrop:', e);
            }
        }, 200);
    });

})();
