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

    const params = new URLSearchParams(window.location.search);
    if (params.get('action') === 'add') {
      // Small delay to ensure DOM is fully ready if needed, though init is called on extra_js_bottom
      setTimeout(() => {
        onAdd();
      }, 100);
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
      fecha_pago: tr.dataset.fechaPago || '',
      factura: tr.dataset.factura || '',
      observacion: tr.dataset.observacion || '',
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
      tr.dataset.fechaPago = '';
      tr.dataset.factura = '';
      tr.dataset.observacion = '';
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
    if (window.CuotaModal) {
      window.CuotaModal.open(window.currentPoliza);
    } else {
      console.error('CuotaModal not loaded');
    }
  }

  // Eventos adicionales del modal de edición
  document.addEventListener('DOMContentLoaded', () => {
    // Note: Add Modal logic is handled by add_cuota_modal.js

    // Listen for shared modal save event
    document.addEventListener('cuota:saved', (e) => {
        const data = e.detail;
        const tbody = document.querySelector('#cuotas-table tbody');
        if (!tbody) return;
        
        // Check if we are on the page for this poliza
        if (window.currentPoliza && window.currentPoliza !== data.poliza) return;

        const rowCount = tbody.rows.length;
        const tr = document.createElement('tr');
        
        tr.dataset.documento = ''; 
        tr.dataset.fechaPago = data.fecha_pago || '';
        tr.dataset.factura = data.factura || '';
        tr.dataset.observacion = data.observacion || '';
        
        tr.innerHTML = `
            <td>${data.secuencia || rowCount + 1}</td>
            <td>${data.cupon || ''}</td>
            <td>${data.fecha_vencimiento || ''}</td>
            <td>${data.moneda || 'USD'}</td>
            <td>${parseFloat(data.importe || 0).toFixed(2)}</td>
            <td>${data.fecha_pago || ''}</td>
            <td>${data.factura || ''}</td>
            <td>${data.observacion || ''}</td>
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
        allRows.push(tr);
        recalcTotal();
    });

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
        
        // Update dataset instead of cells for hidden columns
        tr.dataset.fechaPago = nuevaFechaPago;
        tr.dataset.factura = nuevaFactura;
        tr.dataset.observacion = nuevaObservacion;

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