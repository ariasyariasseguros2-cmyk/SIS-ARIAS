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

            setValue('editSecuencia', data.numero_cuota || data.secuencia || ''); // Use sequence if available
            setValue('editCupon', data.cupon);
            setValue('editFechaVenc', toISO(data.fecha_vencimiento));
            setValue('editImporte', data.importe);
            setValue('editFechaPago', toISO(data.fecha_pago));
            setValue('editFactura', data.factura);
            setValue('editObservacion', data.observacion);
            
            // Document handling
            setValue('editDocumentoNombre', data.documento || data.factura || ''); // Simplified logic
            const fileInput = document.getElementById('editDocumentoFile');
            if (fileInput) fileInput.value = '';

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
                // documento is handled via file upload usually, or just keeping the name
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
                        // We might need poliza info for folder structure, backend handles it by idCuota mostly?
                        // api/cuotas/upload-archivo expects cuota_id. 
                        await fetch('/api/cuotas/upload-archivo', { method: 'POST', body: fd });
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
             fetch(`/api/cuotas/archivos/${idCuota}`)
              .then(r => r.json())
              .then(res => {
                if (!res.ok || !res.archivos || res.archivos.length === 0) {
                  alert('No hay archivos PDF guardados para esta cuota.');
                  return;
                }
                // Use most recent
                const archivo = res.archivos[0];
                const url = `/uploads/${archivo.ruta_archivo}`;
                // Simplified view: open in new tab
                window.open(url, '_blank');
              })
              .catch(err => {
                console.error('Error cargando archivos:', err);
                alert('Error al intentar localizar el documento.');
              });
        }
    };

    // Initialize on load
    document.addEventListener('DOMContentLoaded', () => {
        if (window.CuotaEditModal) {
            window.CuotaEditModal.init();
        }
    });

})();
