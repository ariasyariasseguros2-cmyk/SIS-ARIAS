(function() {
    window.CuotaEditModal = {
        currentId: null,
        currentPoliza: null,

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
                fileInput.addEventListener('change', () => {
                    const file = fileInput.files && fileInput.files[0];
                    const nombreEl = document.getElementById('editDocumentoNombre');
                    if (file && nombreEl) {
                        nombreEl.value = file.name;
                    }
                });
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
                });
            }
            
            // View document listener
            const btnVer = document.getElementById('btnEditDocumentoVer');
            if (btnVer) {
                 btnVer.addEventListener('click', () => {
                    if (!this.currentId) {
                        alert('No hay documento para visualizar.');
                        return;
                    }
                    this.viewDocument(this.currentId);
                 });
            }
        },

        open: function(data, polizaContext) {
            this.currentId = data.idCuota;
            this.currentPoliza = polizaContext || data.poliza; // fallback

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

            // Cargar archivo existente desde la DB (busca por poliza_id con origen=CUOTA)
            const polizaIdCtx = window.currentPolizaId || window.currentPrimaId || '';
            if (polizaIdCtx) {
                fetch(`/api/cuotas/archivos/${polizaIdCtx}`)
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
                const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
                modal.show();
            }
        },

        save: async function() {
            if (!this.currentId) return;

            const getVal = (id) => {
                const el = document.getElementById(id);
                return el ? el.value.trim() : '';
            };

            const payload = {
                idCuota: this.currentId,
                poliza: this.currentPoliza,
                cupon: getVal('editCupon'),
                fecha_vencimiento: getVal('editFechaVenc'),
                importe: getVal('editImporte'),
                fecha_pago: getVal('editFechaPago'),
                factura: getVal('editFactura'),
                observacion: getVal('editObservacion'),
            };

            try {
                const btn = document.getElementById('btnGuardarCuota');
                if (btn) btn.disabled = true;

                const response = await fetch('/cuotas/update-cupon', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const res = await response.json();

                if (res.ok) {
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
                        const polizaId = window.currentPolizaId || window.currentPrimaId || '';
                        if (polizaId) {
                            fd.append('poliza_id', polizaId);
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
                    const event = new CustomEvent('cuota:saved', { detail: payload });
                    document.dispatchEvent(event);

                    const modalEl = document.getElementById('cuotaEditModal');
                    if (modalEl) {
                        const modal = window.bootstrap.Modal.getInstance(modalEl);
                        modal.hide();
                    }
                } else {
                    alert('Error al guardar: ' + (res.error || 'Desconocido'));
                }
            } catch (e) {
                console.error(e);
                alert('Error de conexión.');
            } finally {
                const btn = document.getElementById('btnGuardarCuota');
                if (btn) btn.disabled = false;
            }
        },
        
        viewDocument: function(idCuota) {
            // Si ya tenemos el archivo cargado, usarlo directamente
            if (this._archivoActual) {
                this._openPdfViewer(this._archivoActual);
                return;
            }
            // Buscar por poliza_id con origen=CUOTA en poliza_archivos
            const polizaIdCtx = window.currentPolizaId || window.currentPrimaId || '';
            if (!polizaIdCtx) {
                alert('No hay documento para visualizar.');
                return;
            }
            fetch(`/api/cuotas/archivos/${polizaIdCtx}`)
              .then(r => r.json())
              .then(res => {
                if (!res.ok || !res.archivos || res.archivos.length === 0) {
                  alert('No hay archivos guardados para esta póliza.');
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
            const url = `/uploads/${archivo.ruta_archivo}`;
            const displayName = archivo.nombre_original || archivo.ruta_archivo.split('/').pop();

            const modalEl = document.getElementById('cuotaPdfModal');
            if (!modalEl) {
                window.open(url, '_blank');
                return;
            }

            const frame       = document.getElementById('pdfViewerFrame');
            const downloadBtn = document.getElementById('btnDownloadPdf');
            const titleEl     = document.getElementById('pdfFileName');

            if (frame) frame.src = url;
            if (downloadBtn) { downloadBtn.href = url; downloadBtn.download = displayName; }
            if (titleEl) titleEl.textContent = displayName;

            const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
            modal.show();
        }
    };

    // Initialize on load
    document.addEventListener('DOMContentLoaded', () => {
        if (window.CuotaEditModal) {
            window.CuotaEditModal.init();
        }
    });

})();
