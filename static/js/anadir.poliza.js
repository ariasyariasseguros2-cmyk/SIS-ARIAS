(function () {
  const fileEl = document.getElementById('pdfFile');
  const issuerEl = document.getElementById('issuer');
  const btnUpload = document.getElementById('btnUpload');
  const btnSave = document.getElementById('btnSave');
  const tbody = document.querySelector('#extractTable tbody');
  const hint = document.getElementById('extractHint');
  const subAgenteTopEl = document.getElementById('subAgenteTop');
  let subAgenteEl = subAgenteTopEl || document.getElementById('subAgente');

  // Ventana modal de carga
  const loadingModalEl = document.getElementById('loadingModal');
  const loadingModalMsgEl = document.getElementById('loadingModalMsg');
  const loadingModalElapsedEl = document.getElementById('loadingModalElapsed');
  let loadingModal, loadingInterval = null;
  if (loadingModalEl && window.bootstrap) {
    loadingModal = new bootstrap.Modal(loadingModalEl, { backdrop: 'static', keyboard: false });
  }
  function showLoading(msg) {
    if (!loadingModal) return;
    if (msg && loadingModalMsgEl) loadingModalMsgEl.textContent = msg;
    loadingModal.show();
    const start = performance.now();
    clearInterval(loadingInterval);
    loadingInterval = setInterval(() => {
      const secs = ((performance.now() - start) / 1000).toFixed(1);
      if (loadingModalElapsedEl) loadingModalElapsedEl.textContent = `${secs}s`;
    }, 100);
  }
  function hideLoading() {
    if (!loadingModal) return;
    clearInterval(loadingInterval);
    loadingInterval = null;
    loadingModal.hide();
  }

  // NUEVO: SweetAlert2 modal como preferencia (tipo Angular Swal)
  let swalInterval = null;
  function openLoadingSwal(msg) {
    if (window.Swal) {
      Swal.fire({
        title: msg || 'Procesando PDF…',
        html: `
          <div class="d-flex align-items-center gap-3">
            <span class="spinner-border text-primary" role="status" aria-hidden="true"></span>
            <div>Tiempo transcurrido: <b id="swalElapsed">0.0s</b></div>
          </div>
        `,
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        didOpen: () => {
          const start = performance.now();
          Swal.showLoading();
          clearInterval(swalInterval);
          swalInterval = setInterval(() => {
            const secs = ((performance.now() - start) / 1000).toFixed(1);
            const el = Swal.getHtmlContainer()?.querySelector('#swalElapsed');
            if (el) el.textContent = `${secs}s`;
          }, 100);
        },
        willClose: () => {
          clearInterval(swalInterval);
          swalInterval = null;
        }
      });
    } else {
      // Fallback al modal Bootstrap si no hay Swal
      showLoading(msg || 'Procesando PDF…');
    }
  }
  function closeLoadingSwal() {
    if (window.Swal) {
      Swal.close();
    } else {
      hideLoading();
    }
  }

  // render() y normalizeItem
  function ensureSubAgente() {
    subAgenteEl = document.getElementById('subAgente');
    if (subAgenteEl) return;

    const host = Array.from(document.querySelectorAll('.card .card-body'))
      .find(el => el.textContent.toLowerCase().includes('cliente seleccionado'));
    if (!host) return;

    const wrapper = document.createElement('div');
    wrapper.innerHTML = `
      <div class="d-flex gap-4 mt-2">
        <div>
          <span class="text-muted small">Sub Agente</span>
          <select id="subAgente" class="form-select form-select-sm" style="min-width: 220px;">
            <option value="">Selecciona...</option>
            <option value="Arias y Arias">Arias y Arias</option>
            <option value="Yuri Garcia">Yuri Garcia</option>
          </select>
        </div>
      </div>
    `;
    host.appendChild(wrapper.firstElementChild);
    subAgenteEl = document.getElementById('subAgente');
  }

  ensureSubAgente();

  function populateSubAgenteOptions() {
    const el = subAgenteTopEl || document.getElementById('subAgente');
    if (!el) return;
    const base = Array.from(el.options).map(o => o.value);
    const incoming = (window.availableSubagentes || []).filter(x => !!x && x.trim() !== '');
    incoming.forEach(val => {
      if (!base.includes(val)) {
        const opt = document.createElement('option');
        opt.value = val;
        opt.textContent = val;
        el.appendChild(opt);
      }
    });
  }
  populateSubAgenteOptions();

  // Preseleccionar si viene del servidor
  if (subAgenteEl && window.selectedCliente) {
    const val = window.selectedCliente.subagente || '';
    if (val && !Array.from(subAgenteEl.options).some(o => o.value === val)) {
      const opt = document.createElement('option');
      opt.value = val;
      opt.textContent = val;
      subAgenteEl.appendChild(opt);
    }
    subAgenteEl.value = val;
  }

  // Persistir en memoria del cliente
  (subAgenteTopEl || document.getElementById('subAgente'))?.addEventListener('change', (e) => {
    window.selectedCliente = window.selectedCliente || {};
    window.selectedCliente.subagente = e.target.value;

    // Enviar al backend para persistir en sesión (clientes_select)
    const payload = {
      nombre: window.selectedCliente.nombre || window.selectedCliente.razon_social || '',
      razon_social: window.selectedCliente.razon_social || '',
      tipo_doc: window.selectedCliente.tipo_doc || '',
      n_doc: window.selectedCliente.n_doc || '',
      tel: window.selectedCliente.tel || '',
      subagente: e.target.value
    };
    fetch('/clientes/select', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(r => r.json())
      .then(res => {
        console.log('[clientes/select] persist subagente:', res);
      })
      .catch(err => console.warn('[clientes/select] error:', err));
  });

  function ensureHeader() {
    const thead = document.querySelector('#extractTable thead');
    if (!thead) return;
    const headers = Array.from(thead.querySelectorAll('th')).map(th => th.textContent.trim().toLowerCase());
    const hasRamo = headers.includes('ramo');
    const hasPrimaNeta = headers.includes('prima neta');
    const hasAcciones = headers.includes('acciones');
    const expectedCount = 14;
    if (!hasRamo || !hasPrimaNeta || !hasAcciones || headers.length !== expectedCount) {
      thead.innerHTML = `
        <tr>
          <th>Póliza</th>
          <th>Proforma/Recibo</th>
          <th>Colectivo Asegurado</th>
          <th>Ramo</th>
          <th>Inicio Vigencia</th>
          <th>Vencimiento</th>
          <th>Moneda</th>
          <th>Fecha Emisión</th>
          <th>Forma Pago</th>
          <th>Último Día Pago</th>
          <th>Prima Comercial</th>
          <th>Prima Neta</th>
          <th>Prima + IGV</th>
          <th class="actions-col">Acciones</th>
        </tr>
      `;
    }
  }
  ensureHeader();

  function render(items) {
    ensureHeader();
    tbody.innerHTML = '';
    items.forEach((it, idx) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="numero_poliza">${it.numero_poliza || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="recibo">${it.recibo || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="colectivo_asegurado">${it.colectivo_asegurado || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="ramo">${it.ramo || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="inicio_vigencia">${it.inicio_vigencia || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="vencimiento">${it.vencimiento || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="moneda">${it.moneda || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="fecha_emision">${it.fecha_emision || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="forma_pago">${it.forma_pago || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="ultimo_dia_pago">${it.ultimo_dia_pago || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="prima_comercial">${it.prima_comercial || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="prima_neta">${it.prima_neta || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="prima_comercial_igv">${it.prima_comercial_igv || it.prima_total || it.monto || ''}</td>
        <td class="actions-col">
          <div class="actions-stack">
            <button type="button" class="action-btn btn-del js-del" data-index="${idx}">
              Eliminar
            </button>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
    btnSave.disabled = items.length === 0;
    hint.textContent = items.length ? `Se extrajeron ${items.length} item(s). Revisa y guarda.` : 'Sube un PDF para ver información.';
  }

  // Borrado de fila con delegación
  tbody.addEventListener('click', (e) => {
    const btn = e.target.closest('.js-del');
    if (!btn) return;
    const idx = parseInt(btn.getAttribute('data-index'), 10);
    if (Number.isNaN(idx)) return;
    extractedItems.splice(idx, 1);
    render(extractedItems);
  });

  // Eliminar tabla completa
  document.getElementById('btnClear')?.addEventListener('click', () => {
    if (!extractedItems.length) { alert('No hay datos para eliminar.'); return; }
    if (!confirm('¿Eliminar todos los ítems de la tabla?')) return;
    extractedItems = [];
    render(extractedItems);
  });

  // Normalizador defensivo en el cliente (sin mezclar neta en comercial)
  function normalizeItem(it) {
    return {
      numero_poliza: it.numero_poliza || it.poliza || it.folio_id || it.contrato_nro || '',
      recibo: it.recibo || it.numero_proforma || it.nro_tramite || '',
      colectivo_asegurado: it.colectivo_asegurado || it.asegurado || it.contratante || '',
      ramo: it.ramo || it.doc_tipo || '',
      inicio_vigencia: it.inicio_vigencia || it.vigencia_desde || '',
      vencimiento: it.vencimiento || it.vigencia_hasta || it.hasta || '',
      moneda: it.moneda || '',
      fecha_emision: it.fecha_emision || it.emision || '',
      forma_pago: it.forma_pago || '',
      ultimo_dia_pago: it.ultimo_dia_pago || '',
      prima_comercial: it.prima_comercial || '',
      prima_neta: it.prima_neta || '',
      prima_total: it.prima_total || it.monto || '',
      prima_comercial_igv: it.prima_comercial_igv || it.prima_total || it.monto || '',
    };
  }

  btnUpload?.addEventListener('click', () => {
    const file = fileEl?.files?.[0];
    if (!file) { alert('Selecciona un PDF.'); return; }

    // Mostrar ventana de carga tipo Swal
    openLoadingSwal('Procesando PDF…');
    const startTs = performance.now();
    btnUpload.disabled = true;
    issuerEl.disabled = true;
    fileEl.disabled = true;
    btnUpload.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Extrayendo…`;

    const fd = new FormData();
    fd.append('file', file);
    fd.append('issuer', issuerEl?.value || '');
    fd.append('debug', '1'); // activar trazas del backend

    fetch('/upload', { method: 'POST', body: fd })
      .then(async (r) => {
        const isJson = (r.headers.get('content-type') || '').includes('application/json');
        const payload = isJson ? await r.json() : await r.text();
        console.log('[upload] status:', r.status, 'payload:', payload);

        if (payload && Array.isArray(payload.debug)) {
          payload.debug.forEach((line) => console.log('[server]', line));
        }

        if (!r.ok) {
          alert(typeof payload === 'string' ? payload : (payload.error || 'Error al extraer datos.'));
          return;
        }

        let items = [];
        if (payload.items && Array.isArray(payload.items)) {
          items = payload.items.map(normalizeItem);
        } else if (payload.fields && typeof payload.fields === 'object') {
          items = [normalizeItem(payload.fields)];
        }
        extractedItems = items;
        render(extractedItems);

        const elapsed = ((performance.now() - startTs) / 1000).toFixed(2);
        hint.textContent = items.length
          ? `Se extrajeron ${items.length} ítem(s) en ${elapsed}s. Revisa y guarda.`
          : `Sin datos. Procesado en ${elapsed}s.`;
      })
      .catch((err) => {
        console.error('[upload] fetch error:', err);
        alert('Error de red al extraer datos del PDF.');
      })
      .finally(() => {
        // Ocultar ventana de carga y restaurar controles
        closeLoadingSwal();
        btnUpload.disabled = false;
        issuerEl.disabled = false;
        fileEl.disabled = false;
        btnUpload.textContent = 'Extraer datos';
      });
  });

  // Preseleccionar subagente si viene del servidor
  if (subAgenteEl && window.selectedCliente) {
    subAgenteEl.value = window.selectedCliente.subagente || '';
  }

  function ensureHeader() {
    const thead = document.querySelector('#extractTable thead');
    if (!thead) return;
    const headers = Array.from(thead.querySelectorAll('th')).map(th => th.textContent.trim().toLowerCase());
    const hasRamo = headers.includes('ramo');
    const hasPrimaNeta = headers.includes('prima neta');
    const hasAcciones = headers.includes('acciones');
    const expectedCount = 14;
    if (!hasRamo || !hasPrimaNeta || !hasAcciones || headers.length !== expectedCount) {
      thead.innerHTML = `
        <tr>
          <th>Póliza</th>
          <th>Proforma/Recibo</th>
          <th>Colectivo Asegurado</th>
          <th>Ramo</th>
          <th>Inicio Vigencia</th>
          <th>Vencimiento</th>
          <th>Moneda</th>
          <th>Fecha Emisión</th>
          <th>Forma Pago</th>
          <th>Último Día Pago</th>
          <th>Prima Comercial</th>
          <th>Prima Neta</th>
          <th>Prima + IGV</th>
          <th class="actions-col">Acciones</th>
        </tr>
      `;
    }
  }
  ensureHeader();

  // Editar celdas y actualizar datos
  let autoSaveTimer = null;
  function scheduleAutoSave() {
    clearTimeout(autoSaveTimer);
    autoSaveTimer = setTimeout(() => {
      const selected = Object.assign({}, (window.selectedCliente || {}), {
        subagente: (document.getElementById('subAgenteTop')?.value ||
                    document.getElementById('subAgente')?.value ||
                    (window.selectedCliente || {}).subagente || '')
      });
      fetch('/polizas/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: extractedItems, selected })
      })
      .then(r => r.json())
      .then(res => {
        if (res.ok) {
          hint.textContent = `Cambios guardados automáticamente (${res.count}).`;
        }
      })
      .catch(err => console.warn('[autosave] error:', err));
    }, 1200);
  }

  tbody.addEventListener('blur', (e) => {
    const el = e.target.closest('.editable');
    if (!el) return;
    const idx = Number(el.dataset.index);
    const field = el.dataset.field;
    const val = el.textContent.trim();
    if (!Number.isFinite(idx) || !field) return;
    extractedItems[idx][field] = val;
    scheduleAutoSave();
  }, true);

  tbody.addEventListener('keydown', (e) => {
    const el = e.target.closest('.editable');
    if (!el) return;
    if (e.key === 'Enter') {
      e.preventDefault();
      el.blur();
    }
  });

  // IMPORTANTE: ya existe ensureHeader() arriba; evita duplicarlo.
  // Elimina cualquier segunda definición de ensureHeader() al final del archivo si estuviera presente.

  btnSave?.addEventListener('click', () => {
    if (!extractedItems.length) { alert('No hay datos para guardar.'); return; }
    const selected = Object.assign({}, (window.selectedCliente || {}), {
      subagente: (document.getElementById('subAgenteTop')?.value ||
                  document.getElementById('subAgente')?.value ||
                  (window.selectedCliente || {}).subagente || '')
    });
    fetch('/polizas/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: extractedItems, selected })
    })
    .then(r => r.json())
    .then(res => {
      if (res.ok) {
        alert(`Guardado: ${res.count} póliza(s).`);
        extractedItems = [];
        render(extractedItems);
      } else {
        alert(res.errors?.[0] || 'No se pudo guardar.');
      }
    })
    .catch(() => alert('Error al guardar.'));
  });
})();