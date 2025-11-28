(function () {
  const fileEl = document.getElementById('pdfFile');
  const issuerEl = document.getElementById('issuer');
  const btnUpload = document.getElementById('btnUpload');
  const btnSave = document.getElementById('btnSave');
  const tbody = document.querySelector('#extractTable tbody');
  const hint = document.getElementById('extractHint');
  const subAgenteTopEl = document.getElementById('subAgenteTop');
  const ejecutivoTopEl = document.getElementById('ejecutivoTop');
  const estadoTopEl = document.getElementById('estadoTop');
  const tipoPagoTopEl = document.getElementById('tipoPagoTop');
  // NUEVO: campos de comisiones
  const pctComCompaniaEl   = document.getElementById('pctComCompania');
  const impComCompaniaEl   = document.getElementById('impComCompania');
  const pctComSubAgenteEl  = document.getElementById('pctComSubAgente');
  const impComSubAgenteEl  = document.getElementById('impComSubAgente');
  let subAgenteEl = subAgenteTopEl || document.getElementById('subAgente');
  // REMOVIDO: no usar selector superior de Ramo
  // const ramoTopEl = document.getElementById('ramoTop');

  let extractedItems = []; // asegurar variable global para render/autoguardado
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
    const expectedCount = 13; // sin columna de Forma/Tipo Pago
    if (!hasRamo || !hasPrimaNeta || !hasAcciones || headers.length !== expectedCount) {
      thead.innerHTML = `
        <tr>
          <th>Póliza</th>
          <th>Proforma/Recibo</th>
          <th>Colectivo Asegurado</th>
          <th class="ramo-col">Ramo</th>
          <th>Inicio Vigencia</th>
          <th>Vencimiento</th>
          <th>Moneda</th>
          <th>Fecha Emisión</th>
          <!-- REMOVIDO: Tipo/Forma Pago -->
          <th>Último Día Pago</th>
          <th>Prima Neta</th>
          <th>Prima Comercial</th>
          <th>Prima + IGV</th>
          <th class="actions-col">Acciones</th>
        </tr>
      `;
    }
  }
  ensureHeader();

  // Helper: construir opciones del select de Ramo
  function buildRamoOptions(selected) {
    const abbrs = (window.ramosAbbrs || []).filter(x => !!x && x.trim() !== '');
    const opts = [`<option value="">Selecciona...</option>`];
    abbrs.forEach(val => {
      const sel = (selected || '').trim() === val ? ' selected' : '';
      opts.push(`<option value="${val}"${sel}>${val}</option>`);
    });
    return opts.join('');
  }
  function buildRamoSelect(selected) {
    // Select tamaño normal (sin -sm) y con title para tooltip
    const t = (selected || '').toString();
    return `<select class="form-select ramo-select" title="${t.toUpperCase()}">${buildRamoOptions(selected)}</select>`;
  }

  function render(items) {
    ensureHeader();
    const tbody = document.querySelector('#extractTable tbody');
    const btnSave = document.getElementById('btnSave');
    const hint = document.getElementById('extractHint');

    tbody.innerHTML = '';
    items.forEach((it, idx) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="numero_poliza">${it.numero_poliza || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="recibo">${it.recibo || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="colectivo_asegurado">${it.colectivo_asegurado || ''}</td>
        <td class="ramo-col" data-index="${idx}" data-field="ramo">${buildRamoSelect(it.ramo || '')}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="inicio_vigencia">${it.inicio_vigencia || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="vencimiento">${it.vencimiento || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="moneda">${it.moneda || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="fecha_emision">${it.fecha_emision || ''}</td>
        <!-- REMOVIDO: columna de Forma/Tipo Pago -->
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="ultimo_dia_pago">${it.ultimo_dia_pago || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="prima_neta">${it.prima_neta || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="prima_comercial">${it.prima_comercial || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="prima_comercial_igv">${it.prima_comercial_igv || it.prima_total || it.monto || ''}</td>
        <td class="actions-col">
          <div class="actions-stack">
            <button type="button" class="action-btn btn-del js-del" data-index="${idx}">Eliminar</button>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
    btnSave.disabled = items.length === 0;
    hint.textContent = items.length ? `Se extrajeron ${items.length} item(s). Revisa y guarda.` : 'Sube un PDF para ver información.';
  }

  // render() y normalizeItem

  // Helper: calcula Prima Neta desde Prima Comercial (val/1.03, con 2 decimales)
  function computePrimaNetaFromComercial(val) {
    const raw = (val || '').toString().trim();
    if (!raw) return '';
    const num = parseFloat(raw.replace(/[^\d.,-]/g, '').replace(',', '.'));
    if (!Number.isFinite(num)) return '';
    return (num / 1.03).toFixed(2);
  }
  // NUEVO: calcula Prima Comercial desde Prima Neta (val*1.03, con 2 decimales)
  function computePrimaComercialFromNeta(val) {
    const raw = (val || '').toString().trim();
    if (!raw) return '';
    const num = parseFloat(raw.replace(/[^\d.,-]/g, '').replace(',', '.'));
    if (!Number.isFinite(num)) return '';
    return (num * 1.03).toFixed(2);
  }
  // Helper: calcula Prima + IGV desde Prima Comercial (val*1.18)
  function computePrimaIGVFromComercial(val) {
    const raw = (val || '').toString().trim();
    if (!raw) return '';
    const num = parseFloat(raw.replace(/[^\d.,-]/g, '').replace(',', '.'));
    if (!Number.isFinite(num)) return '';
    return (num * 1.18).toFixed(2);
  }

  // normalizeItem: fuerza ambos cálculos según el dato disponible y aplica +IGV=1.18
  function normalizeItem(src) {
    const it = { ...src };
    let comercial = (it.prima_comercial || '').toString().trim();
    let neta = (it.prima_neta || '').toString().trim();
  
    if (!comercial && neta) {
      comercial = computePrimaComercialFromNeta(neta);
      it.prima_comercial = comercial;
    }
    if (comercial) {
      it.prima_neta = computePrimaNetaFromComercial(comercial);
      it.prima_comercial_igv = computePrimaIGVFromComercial(comercial);
    } else {
      it.prima_comercial_igv = '';
    }
    return it;
  }

  // Helper: construir opciones del select de Ramo (se mantiene para la tabla por fila)
  function buildRamoOptions(selected) {
    const abbrs = (window.ramosAbbrs || []).filter(x => !!x && x.trim() !== '');
    const opts = [`<option value="">Selecciona...</option>`];
    abbrs.forEach(val => {
      const sel = (selected || '').trim() === val ? ' selected' : '';
      opts.push(`<option value="${val}"${sel}>${val}</option>`);
    });
    return opts.join('');
  }
  function buildRamoSelect(selected) {
    return `<select class="form-select form-select-sm ramo-select">${buildRamoOptions(selected)}</select>`;
  }

  function render(items) {
    ensureHeader();
    tbody.innerHTML = '';
    items.forEach((it, idx) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="numero_poliza">${it.numero_poliza || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="recibo">${it.recibo || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="colectivo_asegurado">${it.colectivo_asegurado || ''}</td>
        <td data-index="${idx}" data-field="ramo">${buildRamoSelect(it.ramo || '')}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="inicio_vigencia">${it.inicio_vigencia || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="vencimiento">${it.vencimiento || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="moneda">${it.moneda || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="fecha_emision">${it.fecha_emision || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="ultimo_dia_pago">${it.ultimo_dia_pago || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="prima_neta">${it.prima_neta || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="prima_comercial">${it.prima_comercial || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="prima_comercial_igv">${it.prima_comercial_igv || it.prima_total || it.monto || ''}</td>
        <td class="actions-col">
          <div class="actions-stack">
            <button type="button" class="action-btn btn-del js-del" data-index="${idx}">Eliminar</button>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
    btnSave.disabled = items.length === 0;
    hint.textContent = items.length ? `Se extrajeron ${items.length} item(s). Revisa y guarda.` : 'Sube un PDF para ver información.';
  }

  // Delegación: cambios en el select por fila (se mantiene)
  tbody.addEventListener('change', (e) => {
    const sel = e.target.closest('.ramo-select');
    if (!sel) return;
    const td = sel.closest('td');
    const idx = Number(td?.dataset?.index);
    if (!Number.isFinite(idx)) return;
    extractedItems[idx].ramo = sel.value || '';
    scheduleAutoSave();
  });

  // Al cambiar el Ramo superior, completar sólo filas sin valor
  // ramoTopEl?.addEventListener('change', (e) => { ... }); // <- REMOVIDO

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
        try {
          const ct = (r.headers.get('content-type') || '').toLowerCase();
          const rawText = await r.text();
          let payload;
          if (ct.includes('application/json')) {
            payload = JSON.parse(rawText);
          } else {
            // Fallback: intenta parsear como JSON, si no, usa texto
            try { payload = JSON.parse(rawText); } catch { payload = rawText; }
          }

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

          // Aplicar Tipo de Pago + Estado + Comisiones globales
          const tipoPago = tipoPagoTopEl?.value || '';
          const estado   = estadoTopEl?.value || 'PENDIENTE';
          const pctCC    = pctComCompaniaEl?.value || '';
          const impCC    = impComCompaniaEl?.value || '';
          const pctSA    = pctComSubAgenteEl?.value || '';
          const impSA    = impComSubAgenteEl?.value || '';

          items = items.map(it => ({
            ...it,
            forma_pago: tipoPago || it.forma_pago || '',
            estado: estado || it.estado || 'PENDIENTE',
            comision_compania_pct: pctCC,
            comision_compania_importe: impCC,
            comision_subagente_pct: pctSA,
            comision_subagente_importe: impSA
          }));

          extractedItems = items;
          render(extractedItems);

          const elapsed = ((performance.now() - startTs) / 1000).toFixed(2);
          hint.textContent = items.length
            ? `Se extrajeron ${items.length} ítem(s) en ${elapsed}s. Revisa y guarda.`
            : `Sin datos. Procesado en ${elapsed}s.`;
        } catch (e) {
          console.error('[upload] processing error:', e);
          alert('Error procesando respuesta del servidor.');
        }
      })
      .catch((err) => {
        console.error('[upload] fetch error:', err);
        alert('No se pudo conectar con el servidor (/upload).');
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
    const expectedCount = 14; // FIX: 14 columnas incluyendo Ramo
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
          <th>Último Día Pago</th>
          <th>Prima Neta</th>
          <th>Prima Comercial</th>
          <th>Prima + IGV</th>
          <th class="actions-col">Acciones</th>
        </tr>
      `;
    }
  }
  ensureHeader();

  // Editar celdas y actualizar datos (+IGV dinámico con input)
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

  // NUEVO: util para actualizar DOM de celdas calculadas
  function updateComputedCells(idx, item) {
    const tdNeta = document.querySelector(`#extractTable td.editable[data-index="${idx}"][data-field="prima_neta"]`);
    const tdCom = document.querySelector(`#extractTable td.editable[data-index="${idx}"][data-field="prima_comercial"]`);
    const tdIgv = document.querySelector(`#extractTable td.editable[data-index="${idx}"][data-field="prima_comercial_igv"]`);
    if (tdNeta) tdNeta.textContent = item.prima_neta || '';
    if (tdCom) tdCom.textContent = item.prima_comercial || '';
    if (tdIgv) tdIgv.textContent = item.prima_comercial_igv || '';
  }

  // REEMPLAZO: manejador inicial de input ahora solo actualiza memoria y NO toca el DOM
  tbody.addEventListener('input', (e) => {
    const el = e.target.closest('.editable');
    if (!el) return;
    const idx = Number(el.dataset.index);
    const field = el.dataset.field;
    const value = (el.textContent || '').trim();
    if (!Number.isFinite(idx) || !field) return;
    extractedItems[idx] = extractedItems[idx] || {};
    extractedItems[idx][field] = value;
    // No actualizar DOM ni formatear aquí para no mover el caret
  });

  // REEMPLAZO: el blur inicial no hace nada (el formateo ocurre en focusout más abajo)
  tbody.addEventListener('blur', (e) => {
    const el = e.target.closest('.editable');
    if (!el) return;
    // No tocar contenido aquí
  });

  // Helpers para buscar celdas y actualizar dependientes sin tocar la celda activa
  function getTd(index, field) {
    return tbody.querySelector(`td[data-index="${index}"][data-field="${field}"]`);
  }
  function parseNumber(raw) {
    const s = (raw || '').toString().trim();
    if (!s) return NaN;
    return parseFloat(s.replace(/[^\d.,-]/g, '').replace(',', '.'));
  }
  
  // Actualiza dependientes según el campo modificado (sin modificar el td activo)
  function updateDependents(index, sourceField, activeTd) {
    const item = extractedItems[index] || {};
    const comercial = (item.prima_comercial || '').toString().trim();
    const neta = (item.prima_neta || '').toString().trim();
  
    if (sourceField === 'prima_comercial') {
      if (comercial) {
        const netaCalc = computePrimaNetaFromComercial(comercial);
        const igvCalc = computePrimaIGVFromComercial(comercial);
        item.prima_neta = netaCalc;
        item.prima_comercial_igv = igvCalc;
        const netaTd = getTd(index, 'prima_neta');
        const igvTd = getTd(index, 'prima_comercial_igv');
        if (netaTd && netaTd !== activeTd) netaTd.textContent = netaCalc;
        if (igvTd && igvTd !== activeTd) igvTd.textContent = igvCalc;
      } else {
        item.prima_neta = '';
        item.prima_comercial_igv = '';
        const netaTd = getTd(index, 'prima_neta');
        const igvTd = getTd(index, 'prima_comercial_igv');
        if (netaTd && netaTd !== activeTd) netaTd.textContent = '';
        if (igvTd && igvTd !== activeTd) igvTd.textContent = '';
      }
    } else if (sourceField === 'prima_neta') {
      if (neta) {
        const comercialCalc = computePrimaComercialFromNeta(neta);
        const igvCalc = computePrimaIGVFromComercial(comercialCalc);
        item.prima_comercial = comercialCalc;
        item.prima_comercial_igv = igvCalc;
        const comercialTd = getTd(index, 'prima_comercial');
        const igvTd = getTd(index, 'prima_comercial_igv');
        if (comercialTd && comercialTd !== activeTd) comercialTd.textContent = comercialCalc;
        if (igvTd && igvTd !== activeTd) igvTd.textContent = igvCalc;
      } else {
        item.prima_comercial = '';
        item.prima_comercial_igv = '';
        const comercialTd = getTd(index, 'prima_comercial');
        const igvTd = getTd(index, 'prima_comercial_igv');
        if (comercialTd && comercialTd !== activeTd) comercialTd.textContent = '';
        if (igvTd && igvTd !== activeTd) igvTd.textContent = '';
      }
    }
  }
  
  // Delegación: edición de celdas contenteditable
  tbody.addEventListener('input', (e) => {
    const td = e.target.closest('td.editable');
    if (!td) return;
    const idx = Number(td.dataset.index);
    const field = td.dataset.field;
    if (!Number.isFinite(idx) || !field) return;
  
    extractedItems[idx][field] = td.textContent.trim();
  
    if (field === 'prima_comercial' || field === 'prima_neta') {
      updateDependents(idx, field, td);
    }
  });
  
  tbody.addEventListener('focusout', (e) => {
    const td = e.target.closest('td.editable');
    if (!td) return;
    const idx = Number(td.dataset.index);
    const field = td.dataset.field;
    if (!Number.isFinite(idx) || !field) return;
  
    if (field === 'prima_comercial' || field === 'prima_neta' || field === 'prima_comercial_igv') {
      const num = parseNumber(td.textContent);
      const formatted = Number.isFinite(num) ? num.toFixed(2) : '';
      td.textContent = formatted;
      extractedItems[idx][field] = formatted;
    } else {
      extractedItems[idx][field] = td.textContent.trim();
    }
  
    if (field === 'prima_comercial' || field === 'prima_neta') {
      updateDependents(idx, field, td);
    }

    scheduleAutoSave();
  });
  
  // Evitar salto de línea dentro de celdas al presionar Enter
  tbody.addEventListener('keydown', (e) => {
    const td = e.target.closest('td.editable');
    if (!td) return;
    if (e.key === 'Enter') {
      e.preventDefault();
      td.blur();
    }
  });

  // Al subir PDF, normalizar y aplicar +IGV=1.18
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
        try {
          const ct = (r.headers.get('content-type') || '').toLowerCase();
          const rawText = await r.text();
          let payload;
          if (ct.includes('application/json')) {
            payload = JSON.parse(rawText);
          } else {
            // Fallback: intenta parsear como JSON, si no, usa texto
            try { payload = JSON.parse(rawText); } catch { payload = rawText; }
          }

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

          // Aplicar Tipo de Pago + Estado + Comisiones globales
          const tipoPago = tipoPagoTopEl?.value || '';
          const estado   = estadoTopEl?.value || 'PENDIENTE';
          const pctCC    = pctComCompaniaEl?.value || '';
          const impCC    = impComCompaniaEl?.value || '';
          const pctSA    = pctComSubAgenteEl?.value || '';
          const impSA    = impComSubAgenteEl?.value || '';

          items = items.map(it => ({
            ...it,
            forma_pago: tipoPago || it.forma_pago || '',
            estado: estado || it.estado || 'PENDIENTE',
            comision_compania_pct: pctCC,
            comision_compania_importe: impCC,
            comision_subagente_pct: pctSA,
            comision_subagente_importe: impSA
          }));

          extractedItems = items.map(normalizeItem);
          render(extractedItems);

          const elapsed = ((performance.now() - startTs) / 1000).toFixed(2);
          hint.textContent = items.length
            ? `Se extrajeron ${items.length} ítem(s) en ${elapsed}s. Revisa y guarda.`
            : `Sin datos. Procesado en ${elapsed}s.`;
        } catch (e) {
          console.error('[upload] processing error:', e);
          alert('Error procesando respuesta del servidor.');
        }
      })
      .catch((err) => {
        console.error('[upload] fetch error:', err);
        alert('No se pudo conectar con el servidor (/upload).');
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
    const expectedCount = 14; // FIX: 14 columnas incluyendo Ramo
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
          <th>Último Día Pago</th>
          <th>Prima Neta</th>
          <th>Prima Comercial</th>
          <th>Prima + IGV</th>
          <th class="actions-col">Acciones</th>
        </tr>
      `;
    }
  }
  ensureHeader();
})();