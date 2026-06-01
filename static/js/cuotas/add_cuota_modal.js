(function() {
    // Shared Modal Logic
    
    // Helper to increment string ending in number
    function incrementString(str) {
        if (!str) return '';
        // Find trailing number
        const match = str.match(/(\d+)$/);
        if (match) {
            const numberStr = match[1];
            const number = parseInt(numberStr, 10);
            const nextNumber = number + 1;
            const paddedNext = nextNumber.toString().padStart(numberStr.length, '0');
            return str.substring(0, match.index) + paddedNext;
        }
        // If no trailing number, just append 1 (or user logic might differ, but this is safe fallback)
        return str + '1';
    }

    function toISODate(value) {
        const s = String(value || '').trim();
        if (!s) return '';
        if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
        const parts = s.split(/[-/]/).map(p => p.trim()).filter(Boolean);
        if (parts.length !== 3) return '';
        if (parts[0].length === 4) {
            const y = parts[0];
            const m = String(parts[1] || '').padStart(2, '0');
            const d = String(parts[2] || '').padStart(2, '0');
            return `${y}-${m}-${d}`;
        }
        const d = String(parts[0] || '').padStart(2, '0');
        const m = String(parts[1] || '').padStart(2, '0');
        const y = parts[2];
        if (!/^\d{4}$/.test(y)) return '';
        return `${y}-${m}-${d}`;
    }

    function normalizeMoneda(value) {
        const v = String(value || '').trim().toUpperCase();
        if (!v) return '';
        if (v === 'USD' || v === 'US$' || v === 'USS' || v === '$') return 'USD';
        if (v === 'PEN' || v === 'S/.' || v === 'S/' || v === 'SOLES' || v === 'SOL') return 'S/.';
        return value;
    }

    function normalizeImporteNumber(value) {
        const s = String(value || '').trim();
        if (!s) return '';
        const clean = s.replace(/[^\d.,-]/g, '');
        if (!clean) return '';
        let t = clean;
        if (t.includes('.') && t.includes(',')) {
            if (t.lastIndexOf('.') > t.lastIndexOf(',')) t = t.replace(/,/g, '');
            else t = t.replace(/\./g, '').replace(/,/g, '.');
        } else if ((t.match(/\./g) || []).length > 1 && !t.includes(',')) {
            const parts = t.split('.');
            t = parts.slice(0, -1).join('') + '.' + parts[parts.length - 1];
        } else if ((t.match(/,/g) || []).length > 1 && !t.includes('.')) {
            const parts = t.split(',');
            t = parts.slice(0, -1).join('') + '.' + parts[parts.length - 1];
        } else if (t.includes(',')) {
            t = t.replace(/\./g, '').replace(/,/g, '.');
        }
        const num = parseFloat(t);
        return Number.isFinite(num) ? String(num) : '';
    }

    let _extractedCuotas = [];

    function setExtractListMode(isListMode) {
        const formCard = document.getElementById('addCuotaFormCard');
        const btnSave = document.getElementById('btnSaveNewCuota');
        if (formCard) formCard.classList.toggle('d-none', !!isListMode);
        if (btnSave) btnSave.classList.toggle('d-none', !!isListMode);
    }

    function clearSingleCuotaFields() {
        const ids = ['addCupon', 'addFechaVenc', 'addImporte', 'addFechaPago', 'addFactura', 'addObservacion'];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
    }

    function resetExtractedCuotasUI() {
        _extractedCuotas = [];
        const section = document.getElementById('extractCuotasSection');
        const tbody = document.querySelector('#extractCuotasTable tbody');
        const btnSelectAll = document.getElementById('btnExtractCuotasSelectAll');
        if (tbody) tbody.innerHTML = '';
        if (section) section.classList.add('d-none');
        if (btnSelectAll) btnSelectAll.textContent = 'Seleccionar todo';
        setExtractListMode(false);
    }

    function renderExtractedCuotasTable(cuotas) {
        const section = document.getElementById('extractCuotasSection');
        const tbody = document.querySelector('#extractCuotasTable tbody');
        const btnSelectAll = document.getElementById('btnExtractCuotasSelectAll');
        if (!section || !tbody) return;
        tbody.innerHTML = '';
        if (!Array.isArray(cuotas) || cuotas.length < 2) {
            section.classList.add('d-none');
            setExtractListMode(false);
            return;
        }
        const rows = cuotas.map((c, i) => {
            const cupon = String((c && c.cupon) || '').trim();
            const fecha = String((c && c.fecha_vencimiento) || '').trim();
            const importe = normalizeImporteNumber((c && c.importe) || '');
            const moneda = normalizeMoneda((c && c.moneda) || '');
            return `
              <tr data-idx="${i}">
                <td>
                  <input class="form-check-input extract-cuota-check" type="checkbox" data-idx="${i}" checked>
                </td>
                <td>${i + 1}</td>
                <td>${cupon || '—'}</td>
                <td>${fecha || ''}</td>
                <td class="text-end">${importe ? parseFloat(importe).toFixed(2) : ''}</td>
                <td>${moneda || ''}</td>
                <td class="text-end">
                  <button type="button" class="btn btn-sm btn-outline-primary rounded-pill px-3 btn-use-extract" data-idx="${i}">Usar</button>
                </td>
              </tr>
            `;
        }).join('');
        tbody.innerHTML = rows;
        section.classList.remove('d-none');
        if (btnSelectAll) btnSelectAll.textContent = 'Deseleccionar todo';
        setExtractListMode(true);
    }

    window.CuotaModal = {
        open: function(poliza, primaId, aviso) {
            const modalEl = document.getElementById('cuotaAddModal');
            if (!modalEl) return;

            modalEl.dataset.primaId = primaId || '';
            modalEl.dataset.aviso = aviso || '';

            // Reset form
            const form = document.getElementById('addCuotaForm');
            if (form) form.reset();

            // Set context
            const ctx = document.getElementById('addPolizaContext');
            if (ctx) ctx.value = poliza || '';

            // Prefijar secuencia automáticamente según la tabla actual
            try {
                const tbody = document.querySelector('#cuotas-table tbody');
                let nextSeq = 1;
                if (tbody) {
                    let maxSeq = 0;
                    Array.from(tbody.rows).forEach(r => {
                        const td = r.cells && r.cells[0];
                        if (!td) return;
                        const val = parseInt((td.textContent || '').trim(), 10);
                        if (!isNaN(val) && val > maxSeq) maxSeq = val;
                    });
                    nextSeq = maxSeq + 1;
                }
                const seqEl = document.getElementById('addSecuencia');
                if (seqEl) seqEl.value = String(nextSeq);
            } catch (e) {
                // no-op
            }
            
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
            resetExtractedCuotasUI();

            // Ocultar sección de archivos guardados
            const archivosSection = document.getElementById('cuotaArchivosSection');
            if (archivosSection) archivosSection.classList.add('d-none');
            const archivosCount = document.getElementById('cuotaArchivosCount');
            if (archivosCount) archivosCount.textContent = '0';
            const archivosList = document.getElementById('cuotaArchivosList');
            if (archivosList) archivosList.innerHTML = '<p class="text-muted small text-center py-2 mb-0">Sin archivos</p>';

            const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
            modal.show();

            if (poliza) {
                const params = new URLSearchParams();
                params.set('poliza', poliza);
                if (primaId) params.set('poliza_id', primaId);
                if (aviso) params.set('aviso', aviso);

                fetch(`/cuotas/info?${params.toString()}`)
                    .then(r => r.json())
                    .then(res => {
                        if (res.ok && res.data) {
                            const d = res.data;
                            const setVal = (id, val) => {
                                 const el = document.getElementById(id);
                                 if (el && val) el.value = val;
                            };
                            
                            if (d.cupon) setVal('addCupon', d.cupon);
                            
                            // --- AUTO-INCREMENT LOGIC START ---
                            // Check existing rows in the table to determine the next coupon
                            const tbody = document.querySelector('#cuotas-table tbody');
                            let nextCupon = '';
                            
                            if (tbody && tbody.rows.length > 0) {
                                // Get the last row's coupon (2nd column)
                                const lastRow = tbody.rows[tbody.rows.length - 1];
                                const tds = lastRow.querySelectorAll('td');
                                if (tds.length > 1) {
                                    const lastCupon = tds[1].textContent.trim();
                                    if (lastCupon) {
                                        nextCupon = incrementString(lastCupon);
                                    }
                                }
                            } else {
                                // If no rows, use 'Aviso Cob' from header
                                const avisoEl = document.getElementById('header-aviso-cob');
                                if (avisoEl) {
                                    nextCupon = avisoEl.textContent.trim();
                                }
                            }
                            
                            if (nextCupon) {
                                setVal('addCupon', nextCupon);
                            }
                            // --- AUTO-INCREMENT LOGIC END ---

                            // Prefijar (o confirmar) secuencia nuevamente con base en la tabla
                            try {
                                const tbody = document.querySelector('#cuotas-table tbody');
                                let nextSeq = 1;
                                if (tbody) {
                                    let maxSeq = 0;
                                    Array.from(tbody.rows).forEach(r => {
                                        const td = r.cells && r.cells[0];
                                        if (!td) return;
                                        const val = parseInt((td.textContent || '').trim(), 10);
                                        if (!isNaN(val) && val > maxSeq) maxSeq = val;
                                    });
                                    nextSeq = maxSeq + 1;
                                }
                                setVal('addSecuencia', String(nextSeq));
                            } catch (e) {
                                // no-op
                            }

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
        let _selectedFile = null; // mantiene el archivo ya sea por drop o por selector

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
                    _selectedFile = file;
                    // Reflejar el archivo en el input para unificar la fuente
                    try {
                        const dt = new DataTransfer();
                        dt.items.add(file);
                        addFileInput.files = dt.files;
                    } catch (e) {
                        // Si DataTransfer no está disponible, seguimos usando _selectedFile
                    }
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
            _selectedFile = null;
            resetExtractedCuotasUI();
          });
        }

        if (btnExtract) {
          btnExtract.addEventListener('click', async () => {
             const btn = btnExtract;
             const spinner = btn.querySelector('.spinner-border');
             const fileInput = document.getElementById('addDocumentoFile');
             
             const file = (fileInput && fileInput.files && fileInput.files[0]) || _selectedFile;
             if (!file) {
                 alert('Por favor seleccione un archivo primero.');
                 return;
             }

             btn.disabled = true;
             if (spinner) spinner.classList.remove('d-none');
             
             try {
                 const formData = new FormData();
                 formData.append('file', file);
                 
                 const response = await fetch('/cuotas/extract', {
                     method: 'POST',
                     body: formData
                 });
                 
                 const result = await response.json();
                 
                 if (result.ok) {
                     const data = result.data;
                     _extractedCuotas = Array.isArray(data && data.cuotas) ? data.cuotas : [];
                     if (_extractedCuotas.length > 0) {
                         renderExtractedCuotasTable(_extractedCuotas);
                     } else {
                         resetExtractedCuotasUI();
                     }
                     const setVal = (id, val) => {
                         const el = document.getElementById(id);
                         if (el && val) el.value = val;
                     };
                     
                     // Populate fields

                     if (_extractedCuotas.length >= 2) {
                         clearSingleCuotaFields();
                         if (data.moneda) setVal('addMoneda', data.moneda);
                     } else {
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
                     }
                     
                     //setVal('addObservacion', 'Datos extraídos automáticamente del PDF.');

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

        const extractTbody = document.querySelector('#extractCuotasTable tbody');
        const btnSelectAll = document.getElementById('btnExtractCuotasSelectAll');
        const btnSaveExtracted = document.getElementById('btnSaveExtractedCuotas');

        function applyExtractedToForm(idx) {
            const c = _extractedCuotas[idx];
            if (!c) return;
            const cupon = String(c.cupon || '').trim();
            const fechaIso = toISODate(c.fecha_vencimiento || '');
            const importe = normalizeImporteNumber(c.importe || '');
            const moneda = normalizeMoneda(c.moneda || '');
            const setVal = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.value = val || '';
            };
            if (cupon) setVal('addCupon', cupon);
            if (fechaIso) setVal('addFechaVenc', fechaIso);
            if (importe) setVal('addImporte', importe);
            if (moneda) setVal('addMoneda', moneda);
            setExtractListMode(false);
        }

        if (extractTbody) {
            extractTbody.addEventListener('click', (e) => {
                const btn = e.target && e.target.closest ? e.target.closest('.btn-use-extract') : null;
                if (!btn) return;
                const idx = parseInt(btn.dataset.idx, 10);
                if (Number.isFinite(idx)) applyExtractedToForm(idx);
            });
        }

        if (btnSelectAll) {
            btnSelectAll.addEventListener('click', () => {
                const checks = document.querySelectorAll('.extract-cuota-check');
                const anyUnchecked = Array.from(checks).some(c => !c.checked);
                checks.forEach(c => { c.checked = anyUnchecked; });
                btnSelectAll.textContent = anyUnchecked ? 'Deseleccionar todo' : 'Seleccionar todo';
            });
        }

        async function uploadFileForCuota(file, cuotaId, primaId, poliza, cupon) {
            const fd = new FormData();
            fd.append('archivo', file);
            fd.append('cuota_id', cuotaId);
            fd.append('poliza_id', primaId || '');
            fd.append('numero_poliza', poliza || '');
            fd.append('cupon', cupon || '');
            const upResp = await fetch('/api/cuotas/upload-archivo', { method: 'POST', body: fd });
            return await upResp.json().catch(() => ({}));
        }

        if (btnSaveExtracted) {
            btnSaveExtracted.addEventListener('click', async () => {
                const modalEl = document.getElementById('cuotaAddModal');
                const primaId = modalEl ? (modalEl.dataset.primaId || '') : '';
                const poliza = (document.getElementById('addPolizaContext')?.value || '').trim();
                if (!poliza) {
                    alert('Error: No hay póliza seleccionada en el contexto.');
                    return;
                }
                const selectedIdx = Array.from(document.querySelectorAll('.extract-cuota-check'))
                    .filter(c => c.checked)
                    .map(c => parseInt(c.dataset.idx, 10))
                    .filter(n => Number.isFinite(n));
                if (selectedIdx.length === 0) {
                    alert('Seleccione al menos una cuota.');
                    return;
                }

                const fileInput = document.getElementById('addDocumentoFile');
                const file = (fileInput && fileInput.files && fileInput.files[0]) || _selectedFile;

                btnSaveExtracted.disabled = true;
                if (btnSelectAll) btnSelectAll.disabled = true;
                if (btnExtract) btnExtract.disabled = true;

                const failures = [];
                for (const idx of selectedIdx) {
                    const c = _extractedCuotas[idx];
                    if (!c) continue;
                    const cupon = String(c.cupon || '').trim();
                    const fechaIso = toISODate(c.fecha_vencimiento || '');
                    const importe = normalizeImporteNumber(c.importe || '');
                    const moneda = normalizeMoneda(c.moneda || '') || (document.getElementById('addMoneda')?.value || 'S/.');

                    if (!fechaIso || !importe) {
                        failures.push({ cupon, error: 'Falta vencimiento o importe' });
                        continue;
                    }

                    const payload = {
                        poliza,
                        cupon,
                        prima_id: primaId,
                        fecha_vencimiento: fechaIso,
                        moneda,
                        importe,
                        fecha_pago: '',
                        factura: '',
                        observacion: ''
                    };

                    try {
                        const resp = await fetch('/cuotas/save', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(payload)
                        });
                        const res = await resp.json().catch(() => ({}));
                        if (!res || !res.ok) {
                            failures.push({ cupon, error: (res && res.error) ? res.error : 'Error al guardar' });
                            continue;
                        }

                        const newCuotaId = res.idCuota || res.cuota_id || null;
                        let upRes = null;
                        if (file && newCuotaId) {
                            try {
                                upRes = await uploadFileForCuota(file, newCuotaId, primaId, poliza, cupon);
                            } catch (e) {
                                upRes = null;
                            }
                        }

                        const event = new CustomEvent('cuota:saved', {
                            detail: {
                                ...payload,
                                idCuota: newCuotaId,
                                idArchivo: upRes && upRes.ok ? (upRes.idArchivo || null) : null
                            }
                        });
                        document.dispatchEvent(event);
                    } catch (e) {
                        failures.push({ cupon, error: 'Error de conexión' });
                    }
                }

                btnSaveExtracted.disabled = false;
                if (btnSelectAll) btnSelectAll.disabled = false;
                if (btnExtract) btnExtract.disabled = false;

                if (failures.length > 0) {
                    const msg = failures.slice(0, 8).map(f => `${f.cupon || '—'}: ${f.error}`).join('\n');
                    alert(`Algunas cuotas no se guardaron:\n${msg}${failures.length > 8 ? `\n... (${failures.length - 8} más)` : ''}`);
                } else {
                    const modal = window.bootstrap.Modal.getInstance(modalEl);
                    if (modal) modal.hide();
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

              const modalEl = document.getElementById('cuotaAddModal');
              const primaId = modalEl ? (modalEl.dataset.primaId || '') : '';
              
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
                prima_id: primaId,
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
                      // --- UPLOAD PDF si hay archivo seleccionado ---
                      const fileInput = document.getElementById('addDocumentoFile');
                      const file = (fileInput && fileInput.files && fileInput.files[0]) || (_selectedFile || null);
                      const newCuotaId = res.idCuota || res.cuota_id || null;

                      console.log('[cuota:save] idCuota recibido:', newCuotaId);
                      console.log('[cuota:save] archivo seleccionado:', file ? 1 : 0);

                      if (file) {
                          if (!newCuotaId) {
                              console.warn('[cuota:save] No se recibió idCuota del servidor, no se puede subir el archivo.');
                          } else {
                              try {
                                  const fd = new FormData();
                                  fd.append('archivo', file);
                                  fd.append('cuota_id', newCuotaId);
                                  fd.append('poliza_id', primaId || '');
                                  fd.append('numero_poliza', poliza);
                                  fd.append('cupon', cupon);

                                  console.log('[cuota:upload] Enviando archivo:', fileInput.files[0].name, 'cuota_id:', newCuotaId);

                                  const upResp = await fetch('/api/cuotas/upload-archivo', {
                                      method: 'POST',
                                      body: fd
                                  });
                                  const upRes = await upResp.json();
                                  console.log('[cuota:upload] respuesta:', upRes);
                                  if (!upRes.ok) {
                                      alert('Cuota guardada, pero error al subir el archivo: ' + upRes.error);
                                  }
                              } catch (upErr) {
                                  console.error('[cuota:upload] Error:', upErr);
                                  alert('Cuota guardada, pero error de red al subir el archivo.');
                              }
                          }
                      }

                      const modal = window.bootstrap.Modal.getInstance(modalEl);
                      modal.hide();

                      // Dispatch event for listeners
                      const seqEl = document.getElementById('addSecuencia');
                      const event = new CustomEvent('cuota:saved', { detail: { ...payload, idCuota: newCuotaId, secuencia: (seqEl && seqEl.value) || '' } });
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

        // ---- Función global para cargar archivos de una cuota existente ----
        window.loadCuotaArchivos = async function(cuotaId) {
            const section = document.getElementById('cuotaArchivosSection');
            const list = document.getElementById('cuotaArchivosList');
            const countBadge = document.getElementById('cuotaArchivosCount');
            if (!section || !list) return;

            // Usar poliza_id para buscar en poliza_archivos con origen=CUOTA
            const polizaId = window.currentPolizaId || window.currentPrimaId || cuotaId;

            try {
                const resp = await fetch(`/api/cuotas/archivos/${polizaId}`);
                const res = await resp.json();
                if (res.ok && res.archivos && res.archivos.length > 0) {
                    section.classList.remove('d-none');
                    countBadge.textContent = res.archivos.length;
                    list.innerHTML = res.archivos.map(a => `
                        <div class="d-flex align-items-center justify-content-between px-3 py-2 border-bottom">
                            <div class="d-flex align-items-center gap-2">
                                <i class="bi bi-file-earmark-pdf text-danger fs-5"></i>
                                <div>
                                    <div class="small fw-semibold text-truncate" style="max-width:220px;" title="${a.nombre_original || ''}">${a.nombre_original || 'archivo.pdf'}</div>
                                    <div class="text-muted" style="font-size:0.75rem;">${a.creado_en || ''}</div>
                                </div>
                            </div>
                            <div class="d-flex gap-1">
                                <a href="/uploads/${a.ruta_archivo}" target="_blank" class="btn btn-sm btn-outline-primary rounded-pill py-0 px-2" title="Ver archivo">
                                    <i class="bi bi-eye"></i>
                                </a>
                                <button type="button" class="btn btn-sm btn-outline-danger rounded-pill py-0 px-2 btn-del-cuota-archivo" 
                                        data-id="${a.idArchivo}" title="Eliminar">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
                        </div>
                    `).join('');

                    // Listeners eliminar
                    list.querySelectorAll('.btn-del-cuota-archivo').forEach(btn => {
                        btn.addEventListener('click', async function() {
                            if (!confirm('¿Eliminar este archivo?')) return;
                            const aid = this.dataset.id;
                            const dr = await fetch(`/api/cuotas/archivos/delete/${aid}`, { method: 'DELETE' });
                            const dres = await dr.json();
                            if (dres.ok) {
                                window.loadCuotaArchivos(polizaId);
                            } else {
                                alert('Error al eliminar: ' + (dres.error || ''));
                            }
                        });
                    });
                } else {
                    section.classList.remove('d-none');
                    countBadge.textContent = '0';
                    list.innerHTML = '<p class="text-muted small text-center py-2 mb-0">Sin archivos guardados</p>';
                }
            } catch(e) {
                console.error('Error cargando archivos de cuota:', e);
            }
        };

        // URL Parameter Handler (Auto Open)
        const params = new URLSearchParams(window.location.search);
        if (params.get('action') === 'add') {
             // We need poliza. If in URL use it.
             const p = params.get('poliza');
             // Or from context if available
             const currentPoliza = p || (window.currentPoliza || '');
             
             if (currentPoliza) {
                 setTimeout(() => {
                    window.CuotaModal.open(currentPoliza, window.currentPrimaId, window.currentAviso);
                 }, 500);
             }
        }
    });
})();
