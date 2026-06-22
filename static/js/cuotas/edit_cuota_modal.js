(function() {
    window.CuotaEditModal = {
        currentId: null,
        currentPoliza: null,
        currentPolizaId: null,
        currentMoneda: '',
        _extractAbortController: null,
        _isExtracting: false,
        _localPreviewUrl: null,
        _docValidationOk: true,
        _clienteDocumento: '',

        init: function() {
            const btnGuardar = document.getElementById('btnGuardarCuota');
            if (btnGuardar) {
                // Remove existing listeners to avoid duplicates if init is called multiple times
                const newBtn = btnGuardar.cloneNode(true);
                btnGuardar.parentNode.replaceChild(newBtn, btnGuardar);
                
                newBtn.addEventListener('click', () => {
                    this.save();
                });
            }

            // File input listener
            const fileInput = document.getElementById('editDocumentoFile');
            if (fileInput) {
                fileInput.addEventListener('change', async () => {
                    const file = fileInput.files && fileInput.files[0];
                    const nombreEl = document.getElementById('editDocumentoNombre');
                    if (file && nombreEl) {
                        nombreEl.value = file.name;
                    }
                    if (file) {
                        await this.extractAndFillFromFile(file);
                    }
                });

                const dropZone = fileInput.closest('label');
                if (dropZone) {
                    const prevent = (e) => { e.preventDefault(); e.stopPropagation(); };
                    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                        dropZone.addEventListener(eventName, prevent, false);
                    });

                    ['dragenter', 'dragover'].forEach(eventName => {
                        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
                    });

                    ['dragleave', 'drop'].forEach(eventName => {
                        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
                    });

                    dropZone.addEventListener('drop', (e) => {
                        const files = e.dataTransfer && e.dataTransfer.files;
                        if (!files || !files.length) return;

                        const file = files[0];
                        const name = (file.name || '').toLowerCase();
                        const ok = name.endsWith('.pdf') || name.endsWith('.jpg') || name.endsWith('.jpeg') || name.endsWith('.png');
                        if (!ok) {
                            alert('Archivo no permitido. Use PDF, JPG o PNG.');
                            return;
                        }

                        const dt = new DataTransfer();
                        dt.items.add(file);
                        fileInput.files = dt.files;
                        fileInput.dispatchEvent(new Event('change', { bubbles: true }));
                    }, false);
                }
            }

            // Delete document listener
            const btnEliminarDoc = document.getElementById('btnEditDocumentoEliminar');
            if (btnEliminarDoc) {
                btnEliminarDoc.addEventListener('click', () => {
                    const nombreEl = document.getElementById('editDocumentoNombre');
                    if (nombreEl) nombreEl.value = '';
                    const fileInput = document.getElementById('editDocumentoFile');
                    if (fileInput) fileInput.value = '';
                    // Limpiar referencia del archivo actual para que Ver no lo muestre
                    this._archivoActual = null;
                    if (this._localPreviewUrl) {
                        try { URL.revokeObjectURL(this._localPreviewUrl); } catch (e) {}
                        this._localPreviewUrl = null;
                    }
                    if (this._extractAbortController) {
                        this._extractAbortController.abort();
                        this._extractAbortController = null;
                    }
                    this._setExtractingState(false);
                    this._docValidationOk = true;
                    this._setNumeroDocumentoUI(this._clienteDocumento || window.currentClienteDocumento || '', '', null);
                });
            }
            
            // View document listener
            const btnVer = document.getElementById('btnEditDocumentoVer');
            if (btnVer) {
                 btnVer.addEventListener('click', () => {
                    const fileInput = document.getElementById('editDocumentoFile');
                    const file = fileInput && fileInput.files && fileInput.files[0];
                    if (file) {
                        this.previewLocalFile(file);
                        return;
                    }
                    this.viewDocument(this.currentId);
                 });
            }

            const docInput = document.getElementById('editDocumentoNumeroDocumentoInput');
            if (docInput) {
                docInput.addEventListener('input', () => {
                    const raw = docInput.value;
                    this._setNumeroDocumentoUI(this._clienteDocumento || window.currentClienteDocumento || '', raw, null);
                    this._docValidationOk = true;
                    this._setSaveDisabled(this._isExtracting);
                });
            }
        },

        _setNumeroDocumentoUI: function(clienteDoc, docFromFile, match) {
            const cliEl = document.getElementById('editClienteNumeroDocumento');
            const docInput = document.getElementById('editDocumentoNumeroDocumentoInput');
            const badgeEl = document.getElementById('editDocumentoNumeroDocumentoBadge');

            if (cliEl) cliEl.textContent = (clienteDoc && String(clienteDoc).trim()) ? String(clienteDoc).trim() : '—';
            if (docInput) docInput.value = (docFromFile && String(docFromFile).trim()) ? String(docFromFile).trim() : '';

            if (!badgeEl) return;
            badgeEl.classList.add('d-none');
            badgeEl.classList.remove('bg-success', 'bg-danger', 'bg-warning');
            badgeEl.textContent = '';
        },

        _setSaveDisabled: function(disabled) {
            const btnGuardar = document.getElementById('btnGuardarCuota');
            if (btnGuardar) btnGuardar.disabled = !!disabled;
        },

        _setExtractingState: function(isExtracting) {
            this._isExtracting = !!isExtracting;
            this._setSaveDisabled(this._isExtracting);
        },

        previewLocalFile: function(file) {
            if (!file) return;
            if (this._localPreviewUrl) {
                try { URL.revokeObjectURL(this._localPreviewUrl); } catch (e) {}
                this._localPreviewUrl = null;
            }
            const url = URL.createObjectURL(file);
            this._localPreviewUrl = url;
            this._openPdfViewer({ ruta_archivo: url, nombre_original: file.name });
        },

        extractAndFillFromFile: async function(file) {
            if (!file) return;

            if (this._extractAbortController) {
                this._extractAbortController.abort();
            }
            this._extractAbortController = new AbortController();
            const currentController = this._extractAbortController;
            this._setExtractingState(true);

            const toISO = (str) => {
                if (!str) return '';
                const s = String(str).trim();
                if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
                const parts = s.split(/[-/]/);
                if (parts.length === 3) {
                    const d = parts[0].padStart(2, '0');
                    const m = parts[1].padStart(2, '0');
                    const y = parts[2];
                    if (/^\d{4}$/.test(y)) return `${y}-${m}-${d}`;
                }
                return '';
            };

            try {
                const formData = new FormData();
                formData.append('file', file);
                if (this.currentPoliza) formData.append('poliza', this.currentPoliza);
                const pid = this.currentPolizaId || window.currentPolizaId || window.currentPrimaId || '';
                if (pid) formData.append('poliza_id', String(pid));

                const response = await fetch('/cuotas/extract', {
                    method: 'POST',
                    body: formData,
                    signal: currentController.signal
                });

                const result = await response.json().catch(() => ({}));
                if (!result || !result.ok) return;

                const data = result.data || {};
                const valid = data && data.validacion_numero_documento ? data.validacion_numero_documento : null;
                if (valid) {
                    const cliDoc = valid.cliente || this._clienteDocumento || window.currentClienteDocumento || '';
                    const docFile = valid.documento || '';
                    this._clienteDocumento = cliDoc;
                    this._setNumeroDocumentoUI(cliDoc, docFile, null);
                } else {
                    const docFile = data.numero_documento_contratante || '';
                    this._setNumeroDocumentoUI(this._clienteDocumento || window.currentClienteDocumento || '', docFile, null);
                }
                this._docValidationOk = true;

                const fechaPagoEl = document.getElementById('editFechaPago');
                if (fechaPagoEl && data.fecha_pago) {
                    const iso = toISO(data.fecha_pago);
                    if (iso) fechaPagoEl.value = iso;
                }

                const facturaEl = document.getElementById('editFactura');
                if (facturaEl && data.factura) {
                    facturaEl.value = String(data.factura).trim();
                }
            } catch (e) {
                if (e && e.name === 'AbortError') return;
                console.error('[editCuota] Error extrayendo datos del archivo:', e);
            } finally {
                if (this._extractAbortController === currentController) {
                    this._extractAbortController = null;
                    this._setExtractingState(false);
                }
            }
        },

        open: function(data, polizaContext) {
            // Acepta distintas claves de id por robustez
            this.currentId = data.idCuota || data.id_cuota || data.id || null;
            this.currentPoliza = polizaContext || data.poliza; // fallback
            this.currentPolizaId = data.poliza_id || data.polizaId || window.currentPolizaId || window.currentPrimaId || null;
            this.currentMoneda = (data.moneda || window.currentMoneda || '').toString().trim();
            if (this._localPreviewUrl) {
                try { URL.revokeObjectURL(this._localPreviewUrl); } catch (e) {}
                this._localPreviewUrl = null;
            }
            this._docValidationOk = true;
            const passedClienteDoc =
                data.cliente_numero_documento ||
                data.numero_documento_cliente ||
                data.clienteDocumento ||
                data.numero_documento ||
                '';
            this._clienteDocumento = passedClienteDoc || window.currentClienteDocumento || '';
            if (passedClienteDoc) {
                window.currentClienteDocumento = this._clienteDocumento;
            }
            this._setNumeroDocumentoUI(this._clienteDocumento, '', null);
            this._setExtractingState(false);

            const setValue = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.value = val || '';
            };

            // Helper for date formatting YYYY-MM-DD
            const toISO = (str) => {
                if (!str) return '';
                if (/^\d{4}-\d{2}-\d{2}$/.test(str)) return str;
                // Try DD-MM-YYYY or DD/MM/YYYY
                const parts = str.split(/[-/]/);
                if (parts.length === 3) {
                    return `${parts[2]}-${parts[1]}-${parts[0]}`;
                }
                return str;
            };

            const monedaLabel = document.getElementById('editMonedaLabel');
            if (monedaLabel) {
                monedaLabel.textContent = this.currentMoneda || 'Moneda';
            }

            setValue('editSecuencia', data.numero_cuota || data.secuencia || '');
            setValue('editCupon', data.cupon);
            setValue('editFechaVenc', toISO(data.fecha_vencimiento));
            setValue('editImporte', data.importe);
            setValue('editFechaPago', toISO(data.fecha_pago));
            setValue('editFactura', data.factura);
            setValue('editObservacion', data.observacion);

            // Limpiar campo de archivo y file input
            setValue('editDocumentoNombre', '');
            const fileInput = document.getElementById('editDocumentoFile');
            if (fileInput) fileInput.value = '';

            // Cargar archivo existente desde la DB usando la cuota actual.
            const lookupId = this.currentId || '';
            if (lookupId) {
                fetch(`/api/cuotas/archivos/${lookupId}`)
                    .then(r => r.json())
                    .then(res => {
                        if (res.ok && res.archivos && res.archivos.length > 0) {
                            const archivo = res.archivos[0];
                            const nombreEl = document.getElementById('editDocumentoNombre');
                            if (nombreEl) nombreEl.value = archivo.nombre_original || archivo.ruta_archivo.split('/').pop();
                            this._archivoActual = archivo;
                        } else {
                            this._archivoActual = null;
                        }
                    })
                    .catch(() => { this._archivoActual = null; });
            } else {
                this._archivoActual = null;
            }

            const modalEl = document.getElementById('cuotaEditModal');
            if (modalEl) {
                // Persistir id en el propio modal para evitar pérdidas de contexto
                modalEl.dataset.idcuota = this.currentId || '';
                const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
                modal.show();
            }
        },

        save: async function() {
            if (this._isExtracting) {
                alert('Espere a que termine la lectura del archivo para guardar la cuota.');
                return;
            }

            // Robustez: recuperar id desde el modal si no está en memoria
            if (!this.currentId) {
                const modalEl = document.getElementById('cuotaEditModal');
                if (modalEl) {
                    const modalId = modalEl.dataset.idcuota || modalEl.getAttribute('data-idcuota');
                    if (modalId) this.currentId = modalId;
                }
            }
            const isUpdate = !!this.currentId;

            const getVal = (id) => {
                const el = document.getElementById(id);
                return el ? el.value.trim() : '';
            };

            const normalizeImporte = (value) => {
                const txt = String(value || '').trim();
                if (!txt) return '';
                const m = txt.match(/[-+]?\d[\d.,]*/);
                if (!m) return '';
                let raw = (m[0] || '').trim();
                if (!raw) return '';
                if (raw.startsWith('+')) raw = raw.slice(1);

                const lastDot = raw.lastIndexOf('.');
                const lastComma = raw.lastIndexOf(',');
                let cleaned = raw;
                if (lastDot === -1 && lastComma === -1) {
                    cleaned = raw;
                } else if (lastDot > lastComma) {
                    cleaned = raw.replace(/,/g, '');
                } else if (lastComma > lastDot) {
                    cleaned = raw.replace(/\./g, '').replace(/,/g, '.');
                } else {
                    const sepIdx = Math.max(lastDot, lastComma);
                    const intPart = raw.slice(0, sepIdx).replace(/[^\d-]/g, '');
                    const decPart = raw.slice(sepIdx + 1).replace(/\D/g, '');
                    cleaned = decPart ? `${intPart}.${decPart}` : intPart;
                }
                const num = Number(cleaned);
                if (!Number.isFinite(num)) return '';
                return num.toFixed(2);
            };

            const payload = {
                idCuota: this.currentId,
                poliza: this.currentPoliza || (window.currentPoliza || ''),
                cupon: getVal('editCupon'),
                fecha_vencimiento: getVal('editFechaVenc'),
                importe: normalizeImporte(getVal('editImporte')),
                fecha_pago: getVal('editFechaPago'),
                factura: getVal('editFactura'),
                observacion: getVal('editObservacion'),
            };

            try {
                this._setSaveDisabled(true);

                let ok = false;
                let errorMsg = '';

                if (isUpdate) {
                    const response = await fetch('/cuotas/update-cupon', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    const res = await response.json();
                    ok = !!res.ok;
                    errorMsg = res.error || '';
                } else {
                    // Crear nueva cuota si no existe id
                    const createPayload = {
                        poliza: payload.poliza,
                        cupon: payload.cupon,
                        fecha_vencimiento: payload.fecha_vencimiento,
                        moneda: this.currentMoneda || window.currentMoneda || 'S/.',
                        importe: payload.importe,
                        fecha_pago: payload.fecha_pago,
                        factura: payload.factura,
                        observacion: payload.observacion
                    };
                    const response = await fetch('/cuotas/save', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(createPayload)
                    });
                    const res = await response.json();
                    ok = !!res.ok;
                    errorMsg = res.error || '';
                    if (ok && res.idCuota) {
                        this.currentId = String(res.idCuota);
                        payload.idCuota = this.currentId;
                        const modalEl = document.getElementById('cuotaEditModal');
                        if (modalEl) modalEl.dataset.idcuota = this.currentId;
                    }
                }

                if (ok) {
                    // Handle file upload if present
                    const fileInput = document.getElementById('editDocumentoFile');
                    if (fileInput && fileInput.files && fileInput.files.length > 0) {
                        const fd = new FormData();
                        fd.append('archivo', fileInput.files[0]);
                        fd.append('cuota_id', this.currentId);
                        fd.append('cupon', payload.cupon);
                        if (this.currentPoliza) {
                            fd.append('numero_poliza', this.currentPoliza);
                        }
                        // Pasar poliza_id con todas las fuentes disponibles
                        const polizaId = this.currentPolizaId || window.currentPolizaId || window.currentPrimaId || '';
                        if (polizaId) {
                            fd.append('poliza_id', String(polizaId));
                        }

                        try {
                            const upResp = await fetch('/api/cuotas/upload-archivo', { method: 'POST', body: fd });
                            const upRes = await upResp.json();
                            if (upRes.ok) {
                                // Actualizar referencia del archivo actual
                                this._archivoActual = {
                                    ruta_archivo: upRes.ruta,
                                    nombre_original: fileInput.files[0].name,
                                    idArchivo: upRes.idArchivo
                                };
                                // Actualizar nombre visible en el input
                                const nombreEl = document.getElementById('editDocumentoNombre');
                                if (nombreEl) nombreEl.value = fileInput.files[0].name;
                            } else {
                                console.warn('[editCuota] Error al subir archivo:', upRes.error);
                                alert('Cuota guardada, pero error al subir el archivo: ' + (upRes.error || ''));
                            }
                        } catch (upErr) {
                            console.error('[editCuota] Error de red al subir archivo:', upErr);
                            alert('Cuota guardada, pero error de red al subir el archivo.');
                        }
                    }

                    // Dispatch event
                    const savedDetail = {
                        ...payload,
                        fecha_pago: getVal('editFechaPago'),
                        factura: getVal('editFactura'),
                        observacion: getVal('editObservacion')
                    };
                    if (this._archivoActual && this._archivoActual.idArchivo) {
                        savedDetail.idArchivo = this._archivoActual.idArchivo;
                        savedDetail.documento = this._archivoActual.ruta_archivo || '';
                    }
                    const event = new CustomEvent('cuota:saved', { detail: savedDetail });
                    document.dispatchEvent(event);

                    const modalEl = document.getElementById('cuotaEditModal');
                    if (modalEl) {
                        const modal = window.bootstrap.Modal.getInstance(modalEl);
                        modal.hide();
                    }
                } else {
                    alert('Error al guardar: ' + (errorMsg || 'Desconocido'));
                }
            } catch (e) {
                console.error(e);
                alert('Error de conexión.');
            } finally {
                this._setSaveDisabled(this._isExtracting);
            }
        },
        
        viewDocument: function(idCuota) {
            // Si ya tenemos el archivo cargado, usarlo directamente
            if (this._archivoActual) {
                this._openPdfViewer(this._archivoActual);
                return;
            }
            const lookupId = idCuota || this.currentId || '';
            if (!lookupId) {
                alert('No hay documento para visualizar.');
                return;
            }
            fetch(`/api/cuotas/archivos/${lookupId}`)
              .then(r => r.json())
              .then(res => {
                if (!res.ok || !res.archivos || res.archivos.length === 0) {
                  alert('No hay archivos guardados para esta cuota.');
                  return;
                }
                const archivo = res.archivos[0];
                this._archivoActual = archivo;
                this._openPdfViewer(archivo);
              })
              .catch(err => {
                console.error('Error cargando archivos:', err);
                alert('Error al intentar localizar el documento.');
              });
        },

        _openPdfViewer: function(archivo) {
            const raw = (archivo && archivo.ruta_archivo) ? String(archivo.ruta_archivo) : '';
            const isDirectUrl = /^(blob:|data:|https?:\/\/|\/uploads\/)/i.test(raw);
            const url = isDirectUrl ? raw : `/uploads/${raw}`;
            const displayName = (archivo && archivo.nombre_original) ? archivo.nombre_original : (raw.split('/').pop() || 'documento');

            const modalEl = document.getElementById('cuotaPdfModal');
            if (!modalEl) {
                window.open(url, '_blank');
                return;
            }

            const editModalEl = document.getElementById('cuotaEditModal');
            const shouldRestoreEdit = !!(editModalEl && editModalEl.classList.contains('show'));
            if (shouldRestoreEdit && window.bootstrap) {
                const inst = window.bootstrap.Modal.getInstance(editModalEl);
                if (inst) inst.hide();
            }

            const frame       = document.getElementById('pdfViewerFrame');
            const downloadBtn = document.getElementById('btnDownloadPdf');
            const titleEl     = document.getElementById('pdfFileName');

            if (frame) frame.src = url;
            if (downloadBtn) { downloadBtn.href = url; downloadBtn.download = displayName; }
            if (titleEl) titleEl.textContent = displayName;

            const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
            modal.show();

            if (shouldRestoreEdit) {
                modalEl.addEventListener('hidden.bs.modal', () => {
                    if (!window.bootstrap || !editModalEl) return;
                    const inst = window.bootstrap.Modal.getOrCreateInstance(editModalEl);
                    inst.show();
                }, { once: true });
            }
        }
    };

    // Initialize on load
    document.addEventListener('DOMContentLoaded', () => {
        if (window.CuotaEditModal) {
            window.CuotaEditModal.init();
        }
    });

})();
