const Cuotas = (() => {
  let allRows = [];
  let pageSize = 20;
  let editIndex = null;
  let confirmModal = null;
  let confirmMessageEl = null;
  let confirmCallback = null;

  function init() {
    const tbody = document.querySelector('#cuotas-table tbody');
    if (!tbody) return;
    allRows = Array.from(tbody.querySelectorAll('tr'));
    applyFilter('');

    const modalEl = document.getElementById('cuotaConfirmModal');
    const msgEl = document.getElementById('cuotaConfirmMessage');
    if (modalEl && msgEl && window.bootstrap) {
      confirmModal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
      confirmMessageEl = msgEl;
    }
  }

  function applyFilter(query) {
    const q = (query || '').toLowerCase();
    let shown = 0;
    allRows.forEach(tr => {
      const text = tr.innerText.toLowerCase();
      const match = text.indexOf(q) !== -1;
      if (match && shown < pageSize) {
        tr.style.display = '';
        shown++;
      } else {
        tr.style.display = 'none';
      }
    });
  }

  function onSearch(val) { applyFilter(val); }
  function onPageSize(val) {
    pageSize = parseInt(val || '20', 10);
    const input = document.getElementById('cuotas-search');
    applyFilter(input ? input.value : '');
  }

  function getRow(idx) {
    const tbody = document.querySelector('#cuotas-table tbody');
    if (!tbody) return null;
    const rows = tbody.querySelectorAll('tr');
    return rows[idx] || null;
  }

  function getCellsData(tr, idx) {
    if (!tr) return null;
    const tds = tr.querySelectorAll('td');
    return {
      secuencia: (idx + 1),
      cupon: tds[1]?.textContent.trim() || '',
      fecha_vencimiento: tds[2]?.textContent.trim() || '',
      moneda: tds[3]?.textContent.trim() || '',
      importe: tds[4]?.textContent.trim() || '',
      fecha_pago: tds[5]?.textContent.trim() || '',
      factura: tds[6]?.textContent.trim() || '',
      observacion: tds[7]?.textContent.trim() || '',
      documento: tr.dataset.documento || ''
    };
  }

  function recalcTotal() {
    const tbody = document.querySelector('#cuotas-table tbody');
    const totalEl = document.querySelector('.importe-text .importe-monto');
    if (!tbody || !totalEl) return;
    let total = 0;
    tbody.querySelectorAll('tr').forEach(tr => {
      const td = tr.querySelector('td:nth-child(5)');
      if (!td) return;
      const raw = td.textContent || '';
      const num = parseFloat(raw.replace('S/.', '').replace(',', '.').trim());
      if (!isNaN(num)) total += num;
    });
    totalEl.textContent = total.toFixed(2);
  }

  function openConfirm(message, onAccept) {
    if (!confirmModal || !confirmMessageEl) {
      if (window.confirm(message)) onAccept();
      return;
    }
    confirmMessageEl.textContent = message;
    confirmCallback = onAccept;
    confirmModal.show();
  }

  // Acción PDF: abre en nueva pestaña usando factura o cupón como nombre base
  function onPDF(idx) {
    const tr = getRow(idx);
    const data = getCellsData(tr, idx);
    if (!data) return;
    const base = data.factura || data.cupon;
    if (!base) {
      alert('No hay documento asociado a esta cuota.');
      return;
    }
    const filename = encodeURIComponent(String(base).trim() + '.pdf');
    const url = `/uploads/${filename}`;
    window.open(url, '_blank');
  }

  function onRevert(idx) {
    const tr = getRow(idx);
    if (!tr) return;
    openConfirm('¿Está seguro de revertir esta cuota? Se borrarán los datos de pago.', () => {
      const tds = tr.querySelectorAll('td');
      if (tds[5]) tds[5].textContent = '';
      if (tds[6]) tds[6].textContent = '';
      if (tds[7]) tds[7].textContent = '';
      tr.dataset.documento = '';

      const btnRevert = tr.querySelector('.btn-revert');
      if (btnRevert) btnRevert.style.display = 'none';
    });
  }

  // Detalles: muestra modal de solo lectura
  function onDetails(idx) {
    const tr = getRow(idx);
    const data = getCellsData(tr, idx);
    if (!data) return;

    const usuario = window.currentUser || '';
    const docName = data.documento || data.factura || '';

    const setText = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val || '';
    };

    setText('detailSecuencia', data.secuencia);
    setText('detailCupon', data.cupon);
    setText('detailFechaVenc', data.fecha_vencimiento);
    setText('detailImporte', data.importe);
    setText('detailFechaPago', data.fecha_pago);
    setText('detailFactura', data.factura);
    setText('detailObservacion', data.observacion);
    setText('detailUsuario', usuario);

    const docEl = document.getElementById('detailDocumento');
    if (docEl) {
      docEl.innerHTML = '';
      if (docName) {
        const link = document.createElement('a');
        link.href = `/uploads/${encodeURIComponent(docName.endsWith('.pdf') ? docName : `${docName}.pdf`)}`;
        link.target = '_blank';
        link.rel = 'noopener';
        link.textContent = docName;
        docEl.appendChild(link);
      } else {
        docEl.textContent = 'Sin documento';
      }
    }

    const modalEl = document.getElementById('cuotaDetailsModal');
    if (!modalEl) return;
    const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }

  // Editar: abre modal con campos editables
  function onEdit(idx) {
    const tr = getRow(idx);
    const data = getCellsData(tr, idx);
    if (!data) return;
    editIndex = idx;

    const setValue = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val || '';
    };

    setValue('editSecuencia', data.secuencia);
    setValue('editCupon', data.cupon);
    setValue('editFechaVenc', data.fecha_vencimiento);
    setValue('editImporte', data.importe);
    setValue('editFechaPago', data.fecha_pago);
    setValue('editFactura', data.factura);
    setValue('editDocumentoNombre', data.documento || data.factura || '');
    const obsEl = document.getElementById('editObservacion');
    if (obsEl) obsEl.value = data.observacion || '';

    const fileInput = document.getElementById('editDocumentoFile');
    if (fileInput) fileInput.value = '';

    const modalEl = document.getElementById('cuotaEditModal');
    if (!modalEl) return;
    const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }

  function onDelete(idx) {
    const tbody = document.querySelector('#cuotas-table tbody');
    if (!tbody) return;
    const tr = tbody.querySelectorAll('tr')[idx];
    if (!tr) return;
    openConfirm('¿Eliminar definitivamente esta cuota?', () => {
      tr.remove();
      recalcTotal();
    });
  }
  function onAdd() { 
    const modalEl = document.getElementById('cuotaAddModal');
    if (!modalEl) return;
    
    // Reset form
    const form = document.getElementById('addCuotaForm');
    if (form) form.reset();
    
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
  }

  // Eventos adicionales del modal de edición y Añadir
  document.addEventListener('DOMContentLoaded', () => {
    // --- Logic for Add Modal ---
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
        e.stopPropagation(); // prevent triggering dropZone click if any
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
                 // Auto-increment sequence
                 const tbody = document.querySelector('#cuotas-table tbody');
                 const nextSeq = tbody ? tbody.rows.length + 1 : 1;
                 setVal('addSecuencia', nextSeq);
                 
                 // data.cupon se ignora por solicitud
                 // if (data.cupon) setVal('addCupon', data.cupon);
                 
                 // data.fecha_vencimiento se ignora por solicitud
                 /*
                 if (data.fecha_vencimiento) {
                     // Convert dd/mm/yyyy to yyyy-mm-dd
                     const parts = data.fecha_vencimiento.split(/[-/]/);
                     if (parts.length === 3) {
                         const date = new Date(parts[2], parts[1] - 1, parts[0]);
                         if (!isNaN(date.getTime())) {
                             const y = date.getFullYear();
                             const m = String(date.getMonth() + 1).padStart(2, '0');
                             const d = String(date.getDate()).padStart(2, '0');
                             setVal('addFechaVenc', `${y}-${m}-${d}`);
                         }
                     }
                 }
                 */
                 
                 if (data.importe) setVal('addImporte', data.importe);
                 
                 if (data.fecha_pago) {
                      const parts = data.fecha_pago.split(/[-/]/);
                      if (parts.length === 3) {
                          const date = new Date(parts[2], parts[1] - 1, parts[0]);
                          if (!isNaN(date.getTime())) {
                             const y = date.getFullYear();
                             const m = String(date.getMonth() + 1).padStart(2, '0');
                             const d = String(date.getDate()).padStart(2, '0');
                             setVal('addFechaPago', `${y}-${m}-${d}`);
                          }
                      }
                 }
                 
                 if (data.factura) setVal('addFactura', data.factura);
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
      btnSaveNew.addEventListener('click', () => {
          const getVal = (id) => {
             const el = document.getElementById(id);
             return el ? el.value.trim() : '';
          };
          
          const sec = getVal('addSecuencia');
          const venc = getVal('addFechaVenc');
          const imp = getVal('addImporte');
          
          if (!sec || !venc || !imp) {
              alert('Por favor complete los campos obligatorios (*).');
              return;
          }

          // Add to table
          const tbody = document.querySelector('#cuotas-table tbody');
          if (tbody) {
            const rowCount = tbody.rows.length;
            const tr = document.createElement('tr');
            const fileInput = document.getElementById('addDocumentoFile');
            const fileName = (fileInput && fileInput.files[0]) ? fileInput.files[0].name : '';
            
            tr.dataset.documento = fileName;
            
            tr.innerHTML = `
              <td>${rowCount + 1}</td>
              <td>${getVal('addCupon')}</td>
              <td>${venc}</td>
              <td>USD</td>
              <td>${parseFloat(imp).toFixed(2)}</td>
              <td>${getVal('addFechaPago')}</td>
              <td>${getVal('addFactura')}</td>
              <td>${getVal('addObservacion')}</td>
              <td class="text-end actions">
                <div class="d-flex gap-2 justify-content-end flex-wrap">
                  <button class="btn btn-sm btn-lift btn-pdf" onclick="Cuotas.onPDF(${rowCount})">PDF</button>
                  <button class="btn btn-sm btn-lift btn-revert" onclick="Cuotas.onRevert(${rowCount})">Revertir</button>
                  <button class="btn btn-sm btn-lift btn-details" onclick="Cuotas.onDetails(${rowCount})">Detalles</button>
                  <button class="btn btn-sm btn-lift btn-edit" onclick="Cuotas.onEdit(${rowCount})">Editar</button>
                  <button class="btn btn-sm btn-lift btn-delete" onclick="Cuotas.onDelete(${rowCount})">Eliminar</button>
                </div>
              </td>
            `;
            tbody.appendChild(tr);
            
            // Re-init list and total
            allRows.push(tr); // Update internal list
            recalcTotal();
            
            // Close modal
            const modalEl = document.getElementById('cuotaAddModal');
            if (modalEl) {
               const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
               modal.hide();
            }
          }
      });
    }

    const btnGuardar = document.getElementById('btnGuardarCuota');
    if (btnGuardar) {
      btnGuardar.addEventListener('click', () => {
        if (editIndex === null) return;
        const tr = getRow(editIndex);
        if (!tr) return;

        const tds = tr.querySelectorAll('td');
        const getVal = (id) => {
          const el = document.getElementById(id);
          return el ? el.value.trim() : '';
        };

        const nuevaFechaPago = getVal('editFechaPago');
        const nuevaFactura = getVal('editFactura');
        const nuevaObservacion = getVal('editObservacion');

        if (tds[2]) tds[2].textContent = getVal('editFechaVenc');
        if (tds[4]) tds[4].textContent = getVal('editImporte');
        if (tds[5]) tds[5].textContent = nuevaFechaPago;
        if (tds[6]) tds[6].textContent = nuevaFactura;
        if (tds[7]) tds[7].textContent = nuevaObservacion;

        const docNombre = getVal('editDocumentoNombre');
        tr.dataset.documento = docNombre;

        // Actualizar visibilidad botón Revertir
        const btnRevert = tr.querySelector('.btn-revert');
        if (btnRevert) {
          if (nuevaFechaPago || nuevaFactura || nuevaObservacion) {
            btnRevert.style.display = 'inline-block'; // o '' para default
          } else {
            btnRevert.style.display = 'none';
          }
        }

        recalcTotal();

        const modalEl = document.getElementById('cuotaEditModal');
        if (modalEl) {
          const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
          modal.hide();
        }
        editIndex = null;
      });
    }

    const btnVer = document.getElementById('btnEditDocumentoVer');
    if (btnVer) {
      btnVer.addEventListener('click', () => {
        const nombreEl = document.getElementById('editDocumentoNombre');
        const name = nombreEl ? nombreEl.value.trim() : '';
        if (!name) {
          alert('No hay documento para visualizar.');
          return;
        }
        const filename = encodeURIComponent(name.endsWith('.pdf') ? name : `${name}.pdf`);
        window.open(`/uploads/${filename}`, '_blank');
      });
    }

    const btnEliminarDoc = document.getElementById('btnEditDocumentoEliminar');
    if (btnEliminarDoc) {
      btnEliminarDoc.addEventListener('click', () => {
        const nombreEl = document.getElementById('editDocumentoNombre');
        if (nombreEl) nombreEl.value = '';
        const fileInput = document.getElementById('editDocumentoFile');
        if (fileInput) fileInput.value = '';
      });
    }

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

    const btnConfirmOk = document.getElementById('btnCuotaConfirmOk');
    if (btnConfirmOk) {
      btnConfirmOk.addEventListener('click', () => {
        if (confirmCallback) {
          const fn = confirmCallback;
          confirmCallback = null;
          fn();
        }
        if (confirmModal) confirmModal.hide();
      });
    }
  });

  return { init, onSearch, onPageSize, onPDF, onRevert, onDetails, onEdit, onDelete, onAdd };
})();
