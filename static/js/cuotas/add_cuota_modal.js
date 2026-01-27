(function() {
    // Shared Modal Logic
    
    window.CuotaModal = {
        open: function(poliza) {
            const modalEl = document.getElementById('cuotaAddModal');
            if (!modalEl) return;

            // Reset form
            const form = document.getElementById('addCuotaForm');
            if (form) form.reset();

            // Set context
            const ctx = document.getElementById('addPolizaContext');
            if (ctx) ctx.value = poliza || '';
            
            // Reset Upload Zone
            const zone = document.getElementById('dropZone');
            if (zone) {
                const content = zone.querySelector('.upload-content');
                const prev = zone.querySelector('.file-preview');
                const btnExtract = document.getElementById('btnExtractData');
                const fileInput = document.getElementById('addDocumentoFile');
                
                if (content) content.classList.remove('d-none');
                if (prev) prev.classList.add('d-none');
                if (btnExtract) btnExtract.disabled = true;
                if (fileInput) fileInput.value = '';
            }

            const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
            modal.show();

            // Fetch default data for this policy
            if (poliza) {
                fetch(`/cuotas/info?poliza=${encodeURIComponent(poliza)}`)
                    .then(r => r.json())
                    .then(res => {
                        if (res.ok && res.data) {
                            const d = res.data;
                            const setVal = (id, val) => {
                                 const el = document.getElementById(id);
                                 if (el && val) el.value = val;
                            };
                            
                            if (d.cupon) setVal('addCupon', d.cupon);
                            if (d.importe) setVal('addImporte', d.importe);
                            if (d.moneda) setVal('addMoneda', d.moneda);
                            
                            // Date conversion if needed (dd/mm/yyyy -> yyyy-mm-dd)
                            if (d.fecha_vencimiento) {
                                const parts = d.fecha_vencimiento.split(/[-/]/);
                                if (parts.length === 3) {
                                    // assume dd/mm/yyyy
                                    setVal('addFechaVenc', `${parts[2]}-${parts[1]}-${parts[0]}`);
                                }
                            }
                        }
                    })
                    .catch(console.error);
            }
        }
    };

    document.addEventListener('DOMContentLoaded', function() {
        // --- MODAL LOGIC (Drag & Drop, Extract, Save) ---

        const dropZone = document.getElementById('dropZone');
        const addFileInput = document.getElementById('addDocumentoFile');
        const btnExtract = document.getElementById('btnExtractData');
        const removeFileBtn = document.getElementById('removeFileBtn');

        if (dropZone && addFileInput) {
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
              dropZone.addEventListener(eventName, (e) => { e.preventDefault(); e.stopPropagation(); }, false);
            });

            ['dragenter', 'dragover'].forEach(eventName => {
              dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
              dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
            });

            dropZone.addEventListener('drop', (e) => {
              const dt = e.dataTransfer;
              handleFiles(dt.files);
            }, false);

            addFileInput.addEventListener('change', function() {
                handleFiles(this.files);
            });

            function handleFiles(files) {
                if (files.length > 0) {
                    const file = files[0];
                    const content = dropZone.querySelector('.upload-content');
                    const prev = dropZone.querySelector('.file-preview');
                    const nameEl = document.getElementById('fileNamePreview');
                    const sizeEl = document.getElementById('fileSizePreview');

                    if (content) content.classList.add('d-none');
                    if (prev) prev.classList.remove('d-none');
                    if (nameEl) nameEl.textContent = file.name;
                    if (sizeEl) sizeEl.textContent = (file.size / 1024 / 1024).toFixed(2) + ' MB';
                    if (btnExtract) btnExtract.disabled = false;
                }
            }
        }

        if (removeFileBtn) {
          removeFileBtn.addEventListener('click', (e) => {
            e.stopPropagation(); 
            const zone = document.getElementById('dropZone');
            const content = zone.querySelector('.upload-content');
            const prev = zone.querySelector('.file-preview');
            const btnExtract = document.getElementById('btnExtractData');
            const fileInput = document.getElementById('addDocumentoFile');

            if (content) content.classList.remove('d-none');
            if (prev) prev.classList.add('d-none');
            if (btnExtract) btnExtract.disabled = true;
            if (fileInput) fileInput.value = '';
          });
        }

        if (btnExtract) {
          btnExtract.addEventListener('click', async () => {
             const btn = btnExtract;
             const spinner = btn.querySelector('.spinner-border');
             const fileInput = document.getElementById('addDocumentoFile');
             
             if (!fileInput || !fileInput.files || !fileInput.files.length) {
                 alert('Por favor seleccione un archivo primero.');
                 return;
             }

             btn.disabled = true;
             if (spinner) spinner.classList.remove('d-none');
             
             try {
                 const formData = new FormData();
                 formData.append('file', fileInput.files[0]);
                 
                 const response = await fetch('/cuotas/extract', {
                     method: 'POST',
                     body: formData
                 });
                 
                 const result = await response.json();
                 
                 if (result.ok) {
                     const data = result.data;
                     const setVal = (id, val) => {
                         const el = document.getElementById(id);
                         if (el && val) el.value = val;
                     };
                     
                     // Populate fields
                     
                     // 1. Número Cupón / Proforma / Recibo
                     if (data.cupon) setVal('addCupon', data.cupon);

                     // 2. Importe
                     if (data.importe) setVal('addImporte', data.importe);

                     // 3. Moneda
                     if (data.moneda) setVal('addMoneda', data.moneda);
                     
                     // 4. Fecha Vencimiento
                     if (data.fecha_vencimiento) {
                          const parts = data.fecha_vencimiento.split(/[-/]/);
                          if (parts.length === 3) {
                              // Asumimos DD/MM/YYYY
                              const d = parts[0].padStart(2, '0');
                              const m = parts[1].padStart(2, '0');
                              const y = parts[2];
                              setVal('addFechaVenc', `${y}-${m}-${d}`);
                          }
                     }
                     
                     // Optional: Factura & Fecha Pago (Hidden fields)
                     if (data.factura) setVal('addFactura', data.factura);
                     
                     if (data.fecha_pago) {
                          const parts = data.fecha_pago.split(/[-/]/);
                          if (parts.length === 3) {
                              const d = parts[0].padStart(2, '0');
                              const m = parts[1].padStart(2, '0');
                              const y = parts[2];
                              setVal('addFechaPago', `${y}-${m}-${d}`);
                          }
                     }
                     
                     setVal('addObservacion', 'Datos extraídos automáticamente del PDF.');

                 } else {
                     alert('No se pudieron extraer datos: ' + (result.error || 'Revise el archivo'));
                 }
             } catch (e) {
                 console.error(e);
                 alert('Error al procesar el archivo. Asegúrese de que sea un PDF válido.');
             } finally {
                 if (spinner) spinner.classList.add('d-none');
                 btn.disabled = false;
             }
          });
        }

        const btnSaveNew = document.getElementById('btnSaveNewCuota');
        if (btnSaveNew) {
          btnSaveNew.addEventListener('click', async () => {
              const getVal = (id) => {
                 const el = document.getElementById(id);
                 return el ? el.value.trim() : '';
              };
              
              const poliza = getVal('addPolizaContext');
              const cupon = getVal('addCupon');
              const venc = getVal('addFechaVenc');
              const imp = getVal('addImporte');
              
              if (!venc || !imp) {
                  alert('Por favor complete los campos obligatorios (Fecha Vencimiento e Importe).');
                  return;
              }
              if (!poliza) {
                  alert('Error: No hay póliza seleccionada en el contexto.');
                  return;
              }

              const payload = {
                poliza: poliza,
                cupon: cupon,
                fecha_vencimiento: venc,
                moneda: getVal('addMoneda') || 'S/.', 
                importe: imp,
                fecha_pago: getVal('addFechaPago'),
                factura: getVal('addFactura'),
                observacion: getVal('addObservacion')
              };

              try {
                  btnSaveNew.disabled = true;
                  const resp = await fetch('/cuotas/save', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify(payload)
                  });
                  const res = await resp.json();
                  
                  if (res.ok) {
                      alert('Cuota guardada exitosamente.');
                      const modalEl = document.getElementById('cuotaAddModal');
                      const modal = window.bootstrap.Modal.getInstance(modalEl);
                      modal.hide();
                      
                      // Dispatch event for listeners
                      const event = new CustomEvent('cuota:saved', { detail: payload });
                      document.dispatchEvent(event);
                  } else {
                      alert('Error al guardar: ' + (res.error || 'Error desconocido'));
                  }
              } catch (e) {
                  console.error(e);
                  alert('Error de conexión al guardar.');
              } finally {
                  btnSaveNew.disabled = false;
              }
          });
        }
        
        // URL Parameter Handler (Auto Open)
        const params = new URLSearchParams(window.location.search);
        if (params.get('action') === 'add') {
             // We need poliza. If in URL use it.
             const p = params.get('poliza');
             // Or from context if available
             const currentPoliza = p || (window.currentPoliza || '');
             
             if (currentPoliza) {
                 setTimeout(() => {
                    window.CuotaModal.open(currentPoliza);
                 }, 500);
             }
        }
    });
})();
