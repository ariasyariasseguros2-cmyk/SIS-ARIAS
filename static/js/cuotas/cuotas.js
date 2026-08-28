const Cuotas = (() => {
  let allRows = [];
  let filteredRows = [];
  let pageSize = 20;
  let currentPage = 1;
  let editIndex = null;
  let confirmModal = null;
  let confirmMessageEl = null;
  let confirmOkBtn = null;
  let confirmCallback = null;
  let pagerWrap = null;
  let pagerPrevBtn = null;
  let pagerNextBtn = null;
  let pagerInfoEl = null;
  let saveListenerBound = false;
  let confirmButtonBound = false;

  function init() {
    const tbody = document.querySelector('#cuotas-table tbody');
    if (!tbody) return;
    tbody.querySelectorAll('tr').forEach(tr => {
      if (String(tr.dataset.activo || '1') === '0') {
        tr.remove();
      }
    });
    allRows = Array.from(tbody.querySelectorAll('tr'));
    ensurePager();
    syncRowIndices();

    const modalEl = document.getElementById('cuotaConfirmModal');
    const msgEl = document.getElementById('cuotaConfirmMessage');
    if (modalEl && msgEl && window.bootstrap) {
      confirmModal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
      confirmMessageEl = msgEl;
      confirmOkBtn = document.getElementById('btnCuotaConfirmOk');
    }

    bindSharedListeners();

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
    filteredRows = allRows.filter(tr => {
      const text = tr.innerText.toLowerCase();
      return text.indexOf(q) !== -1;
    });
    renderPage();
  }

  function onSearch(val) {
    currentPage = 1;
    applyFilter(val);
  }
  function onPageSize(val) {
    pageSize = parseInt(val || '20', 10);
    currentPage = 1;
    const input = document.getElementById('cuotas-search');
    applyFilter(input ? input.value : '');
  }

  function ensurePager() {
    if (pagerWrap) return;
    const toolbar = document.querySelector('.table-toolbar');
    if (!toolbar) return;
    if (document.getElementById('cuotas-pager')) {
      pagerWrap = document.getElementById('cuotas-pager');
      pagerPrevBtn = document.getElementById('cuotas-pager-prev');
      pagerNextBtn = document.getElementById('cuotas-pager-next');
      pagerInfoEl = document.getElementById('cuotas-pager-info');
      return;
    }

    pagerWrap = document.createElement('div');
    pagerWrap.id = 'cuotas-pager';
    pagerWrap.className = 'd-flex align-items-center gap-2';
    pagerWrap.innerHTML = `
      <button type="button" class="btn btn-sm btn-outline-secondary" id="cuotas-pager-prev">Anterior</button>
      <span class="text-secondary small" id="cuotas-pager-info"></span>
      <button type="button" class="btn btn-sm btn-outline-secondary" id="cuotas-pager-next">Siguiente</button>
    `;
    toolbar.appendChild(pagerWrap);

    pagerPrevBtn = document.getElementById('cuotas-pager-prev');
    pagerNextBtn = document.getElementById('cuotas-pager-next');
    pagerInfoEl = document.getElementById('cuotas-pager-info');

    if (pagerPrevBtn) {
      pagerPrevBtn.addEventListener('click', () => {
        if (currentPage > 1) {
          currentPage -= 1;
          renderPage();
        }
      });
    }
    if (pagerNextBtn) {
      pagerNextBtn.addEventListener('click', () => {
        const totalPages = Math.max(1, Math.ceil((filteredRows || []).length / Math.max(1, pageSize)));
        if (currentPage < totalPages) {
          currentPage += 1;
          renderPage();
        }
      });
    }
  }

  function renderPage() {
    const safePageSize = Math.max(1, pageSize || 20);
    const total = (filteredRows || []).length;
    const totalPages = Math.max(1, Math.ceil(total / safePageSize));
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    allRows.forEach(tr => { tr.style.display = 'none'; });

    const start = (currentPage - 1) * safePageSize;
    const end = start + safePageSize;
    (filteredRows || []).slice(start, end).forEach(tr => { tr.style.display = ''; });

    if (pagerWrap) {
      pagerWrap.style.display = total > 0 ? '' : 'none';
    }
    if (pagerInfoEl) {
      pagerInfoEl.textContent = total > 0 ? `Página ${currentPage} de ${totalPages} (${total})` : '';
    }
    if (pagerPrevBtn) pagerPrevBtn.disabled = currentPage <= 1;
    if (pagerNextBtn) pagerNextBtn.disabled = currentPage >= totalPages;
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
      idCuota: tr.dataset.idcuota || '',
      secuencia: tds[0]?.textContent.trim() || (idx + 1),
      cupon: tds[1]?.textContent.trim() || '',
      fecha_vencimiento: tds[2]?.textContent.trim() || '',
      importe: tds[3]?.textContent.trim() || '',
      fecha_pago: tr.dataset.fechaPago || '',
      factura: tr.dataset.factura || '',
      fecha_factura: tr.dataset.fechaFactura || '',
      observacion: tr.dataset.observacion || '',
      documento: tr.dataset.documento || '',
      usuario_registro: tr.dataset.usuarioRegistro || '',
      fecha_creado: tr.dataset.fechaCreado || ''
    };
  }

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function updateObservationCell(tr) {
    if (!tr) return;
    const tds = tr.querySelectorAll('td');
    // Observación siempre es la penúltima columna (última antes de Acciones)
    const cell = tds.length >= 2 ? tds[tds.length - 2] : null;
    if (!cell) return;
    const observacion = escapeHtml(tr.dataset.observacion || '');
    const motivo = escapeHtml(tr.dataset.motivoAnulacion || '');
    const anulada = String(tr.dataset.activo || '1') === '0';
    cell.innerHTML = `
      <div>${observacion}</div>
      ${anulada ? `<div class="small text-danger fw-semibold">ANULADA${motivo ? `: ${motivo}` : ''}</div>` : ''}
    `;
  }

  function updateActionState(tr) {
    if (!tr) return;
    const anulada = String(tr.dataset.activo || '1') === '0';
    const actionsWrap = tr.querySelector('.action-buttons');
    if (!actionsWrap) return;

    const toggle = (selector, visible) => {
      const btn = actionsWrap.querySelector(selector);
      if (btn) btn.style.display = visible ? '' : 'none';
    };

    toggle('.btn-revert', !anulada && !!(tr.dataset.fechaPago && tr.dataset.factura));
    toggle('.btn-edit', !anulada);
    toggle('.btn-delete', !anulada);
    toggle('.btn-hard-delete', !anulada);

    let badge = actionsWrap.querySelector('.cuota-status-badge');
    if (anulada) {
      tr.classList.add('table-danger');
      if (!badge) {
        badge = document.createElement('span');
        badge.className = 'badge text-bg-danger cuota-status-badge';
        badge.textContent = 'Anulada';
        actionsWrap.appendChild(badge);
      }
      badge.style.display = '';
    } else {
      tr.classList.remove('table-danger');
      if (badge) badge.style.display = 'none';
    }
  }

  function markRowAsActive(tr) {
    if (!tr) return;
    tr.dataset.activo = '1';
    tr.dataset.motivoAnulacion = '';
    tr.dataset.usuarioAnulacion = '';
    tr.dataset.fechaAnulacion = '';
    updateObservationCell(tr);
    updateActionState(tr);
  }

  function markRowAsAnulada(tr, motivo) {
    if (!tr) return;
    tr.dataset.activo = '0';
    tr.dataset.motivoAnulacion = (motivo || '').trim();
    updateObservationCell(tr);
    updateActionState(tr);
  }

  function removeRow(tr) {
    if (!tr) return;
    tr.remove();
  }

  function recalcTotal() {
    const tbody = document.querySelector('#cuotas-table tbody');
    // Elemento para mostrar el total de la prima
    const totalEl = document.getElementById('header-total-monto');
    const currencyEl = document.getElementById('header-total-currency');
    
    if (!tbody || !totalEl) return;
    
    let total = 0;
    // Seleccionamos todas las filas, incluyendo las ocultas por el filtro
    tbody.querySelectorAll('tr').forEach(tr => {
      if (String(tr.dataset.activo || '1') === '0') return;
      const td = tr.querySelector('td:nth-child(4)');
      if (!td) return;
      
      const raw = (td.textContent || '').trim();
      // Limpiar el texto: quitar comas y cualquier cosa que no sea número o punto
      let clean = raw.replace(/,/g, '').replace(/[^0-9.-]/g, '');
      
      const num = parseFloat(clean);
      if (!isNaN(num)) total += num;
    });
    
    // Formatear el total con comas para miles y dos decimales
    totalEl.textContent = total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    
    // Si tenemos una moneda global, actualizar el símbolo
    if (currencyEl && window.currentMoneda) {
      currencyEl.textContent = window.currentMoneda;
    }
  }

  function openConfirm(message, onAccept, type) {
    if (!confirmModal || !confirmMessageEl) {
      if (window.confirm(message)) onAccept();
      return;
    }
    confirmMessageEl.textContent = message;
    confirmCallback = onAccept;
    
    // Adjust button style based on action type
    if (confirmOkBtn) {
      if (type === 'revert') {
        confirmOkBtn.classList.remove('btn-danger');
        confirmOkBtn.classList.add('btn-warning');
      } else {
        confirmOkBtn.classList.remove('btn-warning');
        confirmOkBtn.classList.add('btn-danger');
      }
    }
    
    confirmModal.show();
  }

  function bindSharedListeners() {
    if (!saveListenerBound) {
      document.addEventListener('cuota:saved', onCuotaSaved);
      saveListenerBound = true;
    }

    if (!confirmButtonBound) {
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
        confirmButtonBound = true;
      }
    }
  }

  function onCuotaSaved(e) {
    const data = e.detail || {};
    const tbody = document.querySelector('#cuotas-table tbody');
    if (!tbody) return;

    if (window.currentPoliza && data.poliza && window.currentPoliza !== data.poliza) return;

    let tr = null;
    if (data.idCuota) {
      tr = Array.from(tbody.querySelectorAll('tr')).find(row => row.dataset.idcuota == data.idCuota);
    }
    if (!tr && editIndex !== null) {
      tr = getRow(editIndex);
    }

    const isNew = !tr;
    if (isNew) {
      tr = document.createElement('tr');
      tbody.appendChild(tr);
      allRows.push(tr);
    }

    const documentoActual = (data.documento ?? '').toString().trim() || (tr.dataset.documento || '');
    const importe = Number.parseFloat(data.importe || 0);
    const importeTexto = Number.isFinite(importe) ? importe.toFixed(2) : '0.00';

    tr.dataset.idcuota = data.idCuota || '';
    tr.dataset.fechaPago = data.fecha_pago || '';
    tr.dataset.factura = data.factura || '';
    tr.dataset.fechaFactura = data.fecha_factura || '';
    tr.dataset.observacion = data.observacion || '';
    tr.dataset.documento = documentoActual;
    tr.dataset.activo = '1';
    tr.dataset.motivoAnulacion = '';
    tr.dataset.usuarioAnulacion = '';
    tr.dataset.fechaAnulacion = '';
    tr.dataset.usuarioRegistro = data.usuario_registro_display || data.usuario_registro || (tr.dataset.usuarioRegistro || '');
    tr.dataset.fechaCreado = data.fecha_creado || (tr.dataset.fechaCreado || '');

    const rowCount = isNew ? tbody.rows.length : (Array.from(tbody.rows).indexOf(tr) + 1);

    tr.innerHTML = `
        <td>${rowCount}</td>
        <td>${data.cupon || '—'}</td>
        <td>${fromISODate(data.fecha_vencimiento) || ''}</td>
        <td>${importeTexto}</td>
        <td>${fromISODate(data.fecha_pago) || ''}</td>
        <td>${data.factura || ''}</td>
        <td>${data.observacion || ''}</td>
        <td class="text-end actions">
            <div class="action-buttons justify-content-end">
              <button class="btn-action btn-secondary btn-pdf" onclick="Cuotas.onPDF(${rowCount - 1})">PDF</button>
              <button class="btn-action btn-warning btn-revert" onclick="Cuotas.onRevert(${rowCount - 1})" style="${(data.fecha_pago && data.factura) ? '' : 'display:none'}">Revertir</button>
              <button class="btn-action btn-info btn-details" onclick="Cuotas.onDetails(${rowCount - 1})">Detalles</button>
              <button class="btn-action btn-success btn-edit" onclick="Cuotas.onEdit(${rowCount - 1})">Editar</button>
              <button class="btn-action btn-danger btn-delete" onclick="Cuotas.onDelete(${rowCount - 1})">Anular</button>
            </div>
        </td>
    `;

    const pdfBtn = tr.querySelector('.btn-pdf');
    if (pdfBtn) {
      const hasDocumento = !!(data.idArchivo || documentoActual);
      pdfBtn.style.display = hasDocumento ? '' : 'none';
    }

    updateObservationCell(tr);
    updateActionState(tr);

    syncRowIndices();
    editIndex = null;
  }

  // Acción PDF: consulta la ruta real en cuota_archivos y abre el visualizador
  function onPDF(idx) {
    const tr = getRow(idx);
    const data = getCellsData(tr, idx);
    if (!data) return;

    // Detectar tema actual
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const swalConfig = {
      confirmButtonText: 'Aceptar',
      confirmButtonColor: '#3b82f6',
      background: isDark ? '#1a1a1a' : '#ffffff',
      color: isDark ? '#ffffff' : '#333333',
      customClass: {
        popup: 'rounded-4', // Bordes redondeados del modal
        confirmButton: 'rounded-pill px-4' // Botón redondeado tipo píldora
      }
    };

    const idCuota = data.idCuota || '';
    if (!idCuota) {
      Swal.fire({
        ...swalConfig,
        icon: 'info',
        title: 'Aviso',
        text: 'No se pudo identificar la cuota.'
      });
      return;
    }

    fetch(`/api/cuotas/archivos/${idCuota}`)
      .then(r => r.json())
      .then(res => {
        if (!res.ok || !res.archivos || res.archivos.length === 0) {
          Swal.fire({
            ...swalConfig,
            icon: 'info',
            title: 'Aviso',
            text: 'No hay archivos PDF guardados para esta cuota.'
          });
          return;
        }

        const archivo = res.archivos[0];
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
      })
      .catch(err => {
        console.error('Error cargando archivos de cuota:', err);
        Swal.fire({
          ...swalConfig,
          icon: 'error',
          title: 'Error',
          text: 'Error al intentar cargar el documento.'
        });
      });
  }

  function onRevert(idx) {
    const tr = getRow(idx);
    if (!tr) return;
    openConfirm('¿Está seguro de revertir esta cuota? Se borrarán los datos definitivamente.', () => {
      const idCuota = tr.dataset.idcuota || '';
      if (!idCuota) {
        alert('No se pudo identificar la cuota.');
        return;
      }
      fetch('/cuotas/revert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ idCuota })
      })
      .then(r => r.json())
      .then(res => {
        if (!res.ok) {
          alert('Error al revertir: ' + (res.error || 'Desconocido'));
          return;
        }
        const tds = tr.querySelectorAll('td');
        // Columnas actuales: #, Cupón, F.Venc, Importe, F.Pago, Factura, Observación, Acción
        if (tds[4]) tds[4].textContent = '';  // Fecha Pago
        if (tds[5]) tds[5].textContent = '';  // Factura
        // Limpio TODOS los datasets (incluida Fecha Factura) para que Detalles no la muestre
        tr.dataset.fechaPago = '';
        tr.dataset.factura = '';
        tr.dataset.fechaFactura = '';
        tr.dataset.observacion = '';
        tr.dataset.documento = '';
        updateObservationCell(tr);
        updateActionState(tr);
        // Ocultar botones que dependen de Factura/Pago/Documento
        const btnRevert = tr.querySelector('.btn-revert');
        if (btnRevert) btnRevert.style.display = 'none';
        const btnPdf = tr.querySelector('.btn-pdf');
        if (btnPdf) btnPdf.style.display = 'none';
        recalcTotal();
      })
      .catch(e => {
        console.error(e);
        alert('Error de red al revertir.');
      });
    }, 'revert');
  }

  // Detalles: muestra modal de solo lectura
  function onDetails(idx) {
    const tr = getRow(idx);
    const data = getCellsData(tr, idx);
    if (!data) return;

    const usuario = data.usuario_registro || window.currentUser || '';
    const fechaCreado = data.fecha_creado || '';

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
    setText('detailFooterUsuario', usuario);
    setText('detailFooterFechaCreado', fechaCreado ? (fechaCreado ) : '');

    // Mostrar Fecha Factura SOLO en el Resumen Económico (fila de la tarjeta).
    // NO mostrarla en el Timeline "Fechas Clave" (lo pide oculto).
    let fechaFacturaVal = data.fecha_factura ? String(data.fecha_factura).trim() : '';
    // Normalizar formato dd-mm-yyyy (o dd-mm-yyyy hh:mm) -> dd/mm/yyyy
    if (fechaFacturaVal) {
      fechaFacturaVal = fechaFacturaVal.replace(/-/g, '/').split(' ')[0];
    }
    const tieneFactura = !!(data.factura && String(data.factura).trim());
    const rowFechaFactura = document.getElementById('detailRowFechaFactura');
    const tlFechaFactura  = document.getElementById('detailTimelineFechaFactura');
    const tlFechaFacturaVal = document.getElementById('detailTimelineFechaFacturaVal');
    setText('detailFechaFactura', fechaFacturaVal);
    if (tlFechaFacturaVal) tlFechaFacturaVal.textContent = fechaFacturaVal;
    if (rowFechaFactura) {
      rowFechaFactura.style.display = (tieneFactura && fechaFacturaVal) ? '' : 'none';
    }
    // Timeline "Emisión Factura" permanentemente oculto
    if (tlFechaFactura) {
      tlFechaFactura.style.display = 'none';
    }

    // Limpiar el campo de documento mientras carga
    const docEl = document.getElementById('detailDocumento');
    if (docEl) docEl.innerHTML = '<span class="text-muted small">Cargando...</span>';

    const modalEl = document.getElementById('cuotaDetailsModal');
    if (!modalEl) return;
    const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();

    const idCuota = data.idCuota || '';
    if (idCuota && docEl) {
      fetch(`/api/cuotas/archivos/${idCuota}`)
        .then(r => r.json())
        .then(res => {
          if (!res.ok || !res.archivos || res.archivos.length === 0) {
            docEl.textContent = 'Sin documento';
            return;
          }
          docEl.innerHTML = '';
          res.archivos.forEach(archivo => {
            const url = `/uploads/${archivo.ruta_archivo}`;
            const displayName = archivo.nombre_original || archivo.ruta_archivo.split('/').pop();

            const wrapper = document.createElement('div');
            wrapper.className = 'd-flex align-items-center gap-2 mb-1';

            const link = document.createElement('a');
            link.href = url;
            link.target = '_blank';
            link.rel = 'noopener';
            link.textContent = displayName;

            // Botón abrir en visor
            const btnVisor = document.createElement('button');
            btnVisor.type = 'button';
            btnVisor.className = 'btn btn-sm btn-outline-primary py-0 px-2 rounded-pill';
            btnVisor.title = 'Ver en visor';
            btnVisor.innerHTML = '<i class="bi bi-eye"></i>';
            btnVisor.addEventListener('click', () => {
              const pdfModalEl = document.getElementById('cuotaPdfModal');
              if (!pdfModalEl) { window.open(url, '_blank'); return; }
              const frame       = document.getElementById('pdfViewerFrame');
              const downloadBtn = document.getElementById('btnDownloadPdf');
              const titleEl     = document.getElementById('pdfFileName');
              if (frame) frame.src = url;
              if (downloadBtn) { downloadBtn.href = url; downloadBtn.download = displayName; }
              if (titleEl) titleEl.textContent = displayName;
              const pdfModal = window.bootstrap.Modal.getOrCreateInstance(pdfModalEl);
              pdfModal.show();
            });

            wrapper.appendChild(link);
            wrapper.appendChild(btnVisor);
            docEl.appendChild(wrapper);
          });
        })
        .catch(() => {
          if (docEl) docEl.textContent = 'Sin documento';
        });
    } else if (docEl) {
      docEl.textContent = 'Sin documento';
    }
  }

  // Helper: convierte DD/MM/YYYY o DD-MM-YYYY -> YYYY-MM-DD
  function toISODate(str) {
    if (!str) return '';
    // Si ya tiene formato YYYY-MM-DD, devolver tal cual
    if (/^\d{4}-\d{2}-\d{2}$/.test(str)) return str;
    
    // Normalizar separadores a guiones (temporalmente para parsing)
    const s = str.replace(/\//g, '-');
    
    // Si tiene formato DD-MM-YYYY
    if (s.includes('-')) {
      const parts = s.split('-');
      if (parts.length === 3) {
        // Asumimos DD-MM-YYYY -> YYYY-MM-DD
        return `${parts[2]}-${parts[1]}-${parts[0]}`;
      }
    }
    return '';
  }

  // Helper: convierte YYYY-MM-DD -> DD/MM/YYYY
  function fromISODate(str) {
    if (!str || !str.includes('-')) return '';
    const parts = str.split('-');
    if (parts.length === 3) {
      // Retorna formato DD/MM/YYYY (con barras)
      return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    return '';
  }

  // Editar: abre modal con campos editables
  function onEdit(idx) {
    const tr = getRow(idx);
    const data = getCellsData(tr, idx);
    if (!data) return;
    editIndex = idx;

    if (window.CuotaEditModal) {
        // Pass global poliza context if available
        const poliza = window.currentPoliza || ''; 
        window.CuotaEditModal.open(data, poliza);
    } else {
        console.error('CuotaEditModal no cargado');
    }
  }

  let anularCuotaModalEl = null;
  let anularCuotaModalInstance = null;
  let anularCuotaFields = null;

  function initAnularCuotaModal() {
    if (anularCuotaModalEl) return;
    anularCuotaModalEl = document.getElementById('anularCuotaModal');
    if (!anularCuotaModalEl || !window.bootstrap) return;
    anularCuotaModalInstance = window.bootstrap.Modal.getOrCreateInstance(anularCuotaModalEl, { backdrop: 'static' });
    anularCuotaFields = {
      cupon: document.getElementById('anularCuotaCupon'),
      importe: document.getElementById('anularCuotaImporte'),
      motivo: document.getElementById('anularCuotaMotivo'),
      motivoError: document.getElementById('anularCuotaMotivoError'),
      btnOk: document.getElementById('anularCuotaConfirm'),
      btnCancel: document.getElementById('anularCuotaCancel')
    };
  }

  function setAnularCuotaMotivoError(message) {
    if (!anularCuotaFields || !anularCuotaFields.motivo) return;
    if (message) {
      anularCuotaFields.motivo.classList.add('is-invalid');
      if (anularCuotaFields.motivoError) anularCuotaFields.motivoError.textContent = message;
    } else {
      anularCuotaFields.motivo.classList.remove('is-invalid');
    }
  }

  function openAnularCuotaModal(data) {
    initAnularCuotaModal();
    if (!anularCuotaModalEl || !anularCuotaModalInstance || !anularCuotaFields.motivo || !anularCuotaFields.btnOk) {
      const motivo = window.prompt('Motivo de la anulación de la cuota:');
      if (!motivo || !motivo.trim()) return Promise.resolve(null);
      return Promise.resolve(motivo.trim());
    }

    if (anularCuotaFields.cupon) anularCuotaFields.cupon.value = data.cupon || '';
    if (anularCuotaFields.importe) anularCuotaFields.importe.value = data.importe || '';
    anularCuotaFields.motivo.value = '';
    setAnularCuotaMotivoError('');

    return new Promise((resolve) => {
      let decided = false;

      const cleanup = () => {
        anularCuotaFields.btnOk.removeEventListener('click', onOk);
        anularCuotaFields.btnCancel?.removeEventListener('click', onCancel);
        anularCuotaModalEl.removeEventListener('hidden.bs.modal', onHidden);
        anularCuotaFields.motivo.removeEventListener('input', onInput);
      };

      const onInput = () => setAnularCuotaMotivoError('');

      const onOk = () => {
        const motivo = anularCuotaFields.motivo.value.trim();
        if (!motivo) {
          setAnularCuotaMotivoError('Ingrese el motivo de la anulación.');
          return;
        }
        if (motivo.length > 200) {
          setAnularCuotaMotivoError('El motivo no puede exceder 200 caracteres.');
          return;
        }
        decided = true;
        cleanup();
        anularCuotaModalInstance.hide();
        resolve(motivo);
      };

      const onCancel = () => {
        decided = true;
        cleanup();
        anularCuotaModalInstance.hide();
        resolve(null);
      };

      const onHidden = () => {
        if (decided) return;
        cleanup();
        resolve(null);
      };

      anularCuotaFields.btnOk.addEventListener('click', onOk);
      anularCuotaFields.btnCancel?.addEventListener('click', onCancel);
      anularCuotaModalEl.addEventListener('hidden.bs.modal', onHidden);
      anularCuotaFields.motivo.addEventListener('input', onInput);

      anularCuotaModalInstance.show();
      anularCuotaFields.motivo.focus();
    });
  }

  function onDelete(idx) {
    const tbody = document.querySelector('#cuotas-table tbody');
    if (!tbody) return;
    const tr = tbody.querySelectorAll('tr')[idx];
    if (!tr) return;
    const idCuota = tr.dataset.idcuota;
    if (!idCuota) {
      tr.remove();
      syncRowIndices();
      return;
    }
    const data = getCellsData(tr, idx) || {};
    openAnularCuotaModal(data).then(motivo => {
      if (!motivo) return;
      fetch('/cuotas/delete', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({idCuota: idCuota, motivo: motivo})
      })
      .then(r => r.json())
      .then(res => {
        if (res.ok) {
          markRowAsAnulada(tr, motivo);
          removeRow(tr);
          syncRowIndices();
        } else {
          alert('Error al anular: ' + (res.error || 'Desconocido'));
        }
      })
      .catch(e => alert('Error de red: ' + e));
    });
  }

  function onHardDelete(idx) {
    const tbody = document.querySelector('#cuotas-table tbody');
    if (!tbody) return;
    const tr = tbody.querySelectorAll('tr')[idx];
    if (!tr) return;
    openConfirm('⚠️ ELIMINAR PERMANENTEMENTE esta cuota. Esta acción es irreversible. ¿Continuar?', () => {
      const idCuota = tr.dataset.idcuota;
      if (!idCuota) { tr.remove(); syncRowIndices(); return; }
      fetch('/cuotas/hard-delete', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({idCuota: idCuota})
      })
      .then(r => r.json())
      .then(res => {
        if (res.ok) {
          tr.remove();
          syncRowIndices();
        } else {
          alert('Error al eliminar: ' + (res.error || 'Desconocido'));
        }
      })
      .catch(e => alert('Error de red: ' + e));
    }, 'delete');
  }
  function onAdd() { 
    if (window.CuotaModal) {
      window.CuotaModal.open(window.currentPoliza, window.currentPrimaId, window.currentAviso);
    } else {
      console.error('CuotaModal not loaded');
    }
  }

  // Eventos adicionales del modal de edición
  document.addEventListener('DOMContentLoaded', () => {
    // Removed duplicate btnGuardarCuota listener as it is handled by CuotaEditModal

    // Logic for edit modal listeners is now handled in edit_cuota_modal.js
    /*
    const btnVer = document.getElementById('btnEditDocumentoVer');
    if (btnVer) {
      btnVer.addEventListener('click', () => {
        // Obtener idCuota del row en edición
        const tr = getRow(editIndex);
        const idCuota = tr ? (tr.dataset.idcuota || '') : '';
        if (!idCuota) {
          alert('No hay documento para visualizar.');
          return;
        }

        fetch(`/api/cuotas/archivos/${idCuota}`)
          .then(r => r.json())
          .then(res => {
            if (!res.ok || !res.archivos || res.archivos.length === 0) {
              alert('No hay archivos PDF guardados para esta cuota.');
              return;
            }
            const archivo = res.archivos[0];
            const url = `/uploads/${archivo.ruta_archivo}`;
            const displayName = archivo.nombre_original || archivo.ruta_archivo.split('/').pop();

            const modalEl = document.getElementById('cuotaPdfModal');
            if (!modalEl) { window.open(url, '_blank'); return; }

            const frame       = document.getElementById('pdfViewerFrame');
            const downloadBtn = document.getElementById('btnDownloadPdf');
            const titleEl     = document.getElementById('pdfFileName');

            if (frame) frame.src = url;
            if (downloadBtn) { downloadBtn.href = url; downloadBtn.download = displayName; }
            if (titleEl) titleEl.textContent = displayName;

            const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
            modal.show();
          })
          .catch(err => {
            console.error('Error cargando archivos de cuota:', err);
            alert('Error al intentar localizar el documento.');
          });
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
    */

    bindSharedListeners();
  });

  function syncRowIndices() {
    const tbody = document.querySelector('#cuotas-table tbody');
    if (!tbody) return;

    const rows = Array.from(tbody.querySelectorAll('tr'));
    rows.forEach((tr, idx) => {
      if (tr.cells && tr.cells[0]) {
        tr.cells[0].textContent = String(idx + 1);
      }

      updateObservationCell(tr);
      updateActionState(tr);

      const pdfBtn = tr.querySelector('.btn-pdf');
      if (pdfBtn) pdfBtn.setAttribute('onclick', `Cuotas.onPDF(${idx})`);
      const revertBtn = tr.querySelector('.btn-revert');
      if (revertBtn) revertBtn.setAttribute('onclick', `Cuotas.onRevert(${idx})`);
      const detailsBtn = tr.querySelector('.btn-details');
      if (detailsBtn) detailsBtn.setAttribute('onclick', `Cuotas.onDetails(${idx})`);
      const editBtn = tr.querySelector('.btn-edit');
      if (editBtn) editBtn.setAttribute('onclick', `Cuotas.onEdit(${idx})`);
      const deleteBtn = tr.querySelector('.btn-delete');
      if (deleteBtn) deleteBtn.setAttribute('onclick', `Cuotas.onDelete(${idx})`);
    });

    allRows = rows;
    const input = document.getElementById('cuotas-search');
    const q = input ? input.value : '';
    applyFilter(q);
    recalcTotal();
  }

  return { init, onSearch, onPageSize, onPDF, onRevert, onDetails, onEdit, onDelete, onHardDelete, onAdd };
})();
