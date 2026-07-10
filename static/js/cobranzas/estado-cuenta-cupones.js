(() => {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('formEstadoCuentaCupones');
    const alertBox = document.getElementById('estadoCuentaCuponesAlert');
    const tbody = document.getElementById('tbodyEstadoCuentaCupones');
    const info = document.getElementById('estadoCuentaCuponesInfo');
    const tbodyFull = document.getElementById('tbodyEstadoCuentaCuponesFull');
    const infoFull = document.getElementById('estadoCuentaCuponesInfoFull');
    const btnExport = document.getElementById('btnExportPlanillaCupones');
    const btnClear = document.getElementById('btnClearEstadoCuentaCupones');
    const quickSearch = document.getElementById('quickSearchCupones');
    const quickSearchFull = document.getElementById('quickSearchCuponesFull');
    const btnClearQuickSearch = document.getElementById('btnClearQuickSearchCupones');
    const btnClearQuickSearchFull = document.getElementById('btnClearQuickSearchCuponesFull');
    const modalFull = document.getElementById('modalEstadoCuentaCuponesFull');

    const contratanteSearch = document.getElementById('contratanteSearch');
    const btnContratanteToggle = document.getElementById('btnContratanteToggle');
    const contratanteSelected = document.getElementById('contratanteSelected');
    const contratanteHidden = document.getElementById('contratanteHidden');
    const contratanteResults = document.getElementById('contratanteResults');
    let searchTimeout = null;
    const multiSelects = [];
    const selectedContratantes = new Map();
    const polizaCuponInput = form ? form.querySelector('input[name="poliza_cupon"]') : null;
    let allRows = [];

    function escapeHtml(value) {
      return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    function renderPolizaCell(row) {
      const poliza = (row && row.poliza) ? String(row.poliza) : '';
      if (!row || !row.es_financiamiento_grupal || !row.poliza_fg_numero) {
        return escapeHtml(poliza);
      }
      const relacionadas = row.polizas_relacionadas
        ? `<span class="fg-poliza-rel">Polizas: ${escapeHtml(row.polizas_relacionadas)}</span>`
        : '';
      return (
        `<div class="fg-poliza">` +
        `${escapeHtml(row.poliza_fg_prefijo || 'FG-')}<span class="fg-poliza-numero">${escapeHtml(row.poliza_fg_numero)}</span>` +
        relacionadas +
        `</div>`
      );
    }

    function renderEstadoBadge(row) {
      const estado = (row && row.estado_cobranza) ? String(row.estado_cobranza) : '';
      const normalized = estado.toUpperCase();
      let badgeClass = 'bg-secondary';
      if (normalized === 'PAGADO') badgeClass = 'bg-success';
      else if (normalized === 'PENDIENTE') badgeClass = 'bg-warning text-dark';
      else if (normalized === 'CUPON ANULADO' || normalized === 'PRIMA ANULADA') badgeClass = 'bg-danger';
      return estado ? `<span class="badge ${badgeClass}">${escapeHtml(estado)}</span>` : '';
    }

    function isEstadoAnulado(row) {
      const estado = (row && row.estado_cobranza) ? String(row.estado_cobranza).toUpperCase() : '';
      return estado === 'CUPON ANULADO' || estado === 'PRIMA ANULADA';
    }

    function getRowClass(row) {
      return isEstadoAnulado(row) ? 'estado-anulado-row' : '';
    }

    function renderDiasVencidos(row) {
      if (isEstadoAnulado(row)) {
        return '<span class="text-muted">-</span>';
      }
      const dias = row && row.dias_vencidos;
      return dias === null || dias === undefined ? '' : String(dias);
    }

    function initMultiSelect(root) {
      if (!root) return null;
      const name = root.getAttribute('data-ms-name');
      const defaultText = root.getAttribute('data-ms-default-text') || 'Seleccionar';
      const allLabel = root.getAttribute('data-ms-all-label') || 'Todos';
      const allText = root.getAttribute('data-ms-all-text') || 'Todos';
      const searchPlaceholder = root.getAttribute('data-ms-search-placeholder') || 'Buscar...';

      const btn = root.querySelector('button');
      const search = root.querySelector('.ms-search');
      const chkAll = root.querySelector('.ms-all');
      const options = Array.from(root.querySelectorAll('.ms-opt'));
      const hidden = root.querySelector('.ms-hidden');

      if (search) search.placeholder = searchPlaceholder;
      if (chkAll) {
        const lbl = root.querySelector(`label[for="${chkAll.id}"]`);
        if (lbl) lbl.textContent = allLabel;
      }

      function getSelected() {
        return options.filter(o => o.checked).map(o => o.value);
      }

      function updateHidden() {
        if (!hidden) return;
        hidden.innerHTML = '';
        const selected = getSelected();
        if (selected.length === 0 || selected.length === options.length) return;
        selected.forEach(function (val) {
          const inp = document.createElement('input');
          inp.type = 'hidden';
          inp.name = name;
          inp.value = val;
          hidden.appendChild(inp);
        });
      }

      function updateAllCheckbox() {
        if (!chkAll) return;
        const selectedCount = options.filter(o => o.checked).length;
        chkAll.checked = options.length > 0 && selectedCount === options.length;
        chkAll.indeterminate = selectedCount > 0 && selectedCount < options.length;
      }

      function updateButton() {
        if (!btn) return;
        const selected = getSelected();
        if (selected.length === 0) {
          btn.textContent = defaultText;
          return;
        }
        if (selected.length === options.length) {
          btn.textContent = allText;
          return;
        }
        if (selected.length <= 2) {
          btn.textContent = selected.join(', ');
          return;
        }
        btn.textContent = `${selected.length} seleccionados`;
      }

      function applyFilter(q) {
        const needle = (q || '').trim().toLowerCase();
        options.forEach(function (opt) {
          const wrap = opt.closest('.form-check');
          if (!wrap) return;
          const label = wrap.querySelector('label');
          const text = (label ? label.textContent : opt.value || '').toLowerCase();
          wrap.style.display = !needle || text.includes(needle) ? '' : 'none';
        });
      }

      function refresh() {
        updateHidden();
        updateAllCheckbox();
        updateButton();
      }

      if (options.length > 0 && !options.some(o => o.checked)) {
        options.forEach(function (opt) { opt.checked = true; });
      }

      if (chkAll) {
        chkAll.addEventListener('change', function () {
          const checked = chkAll.checked;
          options.forEach(function (opt) { opt.checked = checked; });
          refresh();
        });
      }

      options.forEach(function (opt) {
        opt.addEventListener('change', function () {
          refresh();
        });
      });

      if (search) {
        search.addEventListener('input', function () {
          applyFilter(search.value);
        });
      }

      root.addEventListener('hidden.bs.dropdown', function () {
        if (search) {
          search.value = '';
          applyFilter('');
        }
      });

      refresh();

      return {
        reset: function () {
          options.forEach(function (opt) { opt.checked = true; });
          if (chkAll) {
            chkAll.checked = options.length > 0;
            chkAll.indeterminate = false;
          }
          if (search) {
            search.value = '';
            applyFilter('');
          }
          refresh();
        }
      };
    }

    document.querySelectorAll('[data-ms-name]').forEach(function (el) {
      const ms = initMultiSelect(el);
      if (ms) multiSelects.push(ms);
    });

    function showAlert(message) {
      if (!message) return;
      if (!alertBox) {
        window.alert(message);
        return;
      }
      alertBox.innerHTML = '';
      const div = document.createElement('div');
      div.className = 'alert alert-warning alert-dismissible fade show';
      div.setAttribute('role', 'alert');
      div.textContent = message;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn-close';
      btn.setAttribute('data-bs-dismiss', 'alert');
      btn.setAttribute('aria-label', 'Close');
      div.appendChild(btn);
      alertBox.appendChild(div);
    }

    function clearAlert() {
      if (alertBox) alertBox.innerHTML = '';
    }

    function validateRequiredFilters() {
      if (!form) return true;
      clearAlert();

      const inpDesde = form.querySelector('input[name="fecha_desde"]');
      const inpHasta = form.querySelector('input[name="fecha_hasta"]');
      const contratanteInp = document.getElementById('contratanteSearch');

      const invalidEls = [];
      const missing = [];

      function markInvalid(el) {
        if (!el) return;
        el.classList.add('is-invalid');
        if (el.tagName === 'BUTTON') {
          el.classList.add('border', 'border-danger');
        }
        invalidEls.push(el);
      }

      function clearInvalid(el) {
        if (!el) return;
        el.classList.remove('is-invalid');
        el.classList.remove('border', 'border-danger');
      }

      [inpDesde, inpHasta, contratanteInp].forEach(clearInvalid);

      if (!inpDesde || !inpDesde.value) {
        missing.push('Del');
        markInvalid(inpDesde);
      }
      if (!inpHasta || !inpHasta.value) {
        missing.push('Al');
        markInvalid(inpHasta);
      }

      if (missing.length > 0) {
        showAlert('Debe completar: ' + missing.join(', ') + '.');
        const first = invalidEls.find(Boolean);
        if (first && typeof first.scrollIntoView === 'function') {
          first.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        return false;
      }
      return true;
    }

    function buildQuery() {
      const params = new URLSearchParams();
      const fd = new FormData(form);
      for (const [k, v] of fd.entries()) {
        const val = (v || '').toString().trim();
        if (val) params.append(k, val);
      }
      return params.toString();
    }

    function fmtMoney(val) {
      const num = parseFloat(val);
      if (isNaN(num)) return val === null || val === undefined ? '' : String(val);
      return num.toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function hideResults() {
      if (contratanteResults) contratanteResults.style.display = 'none';
    }

    function renderSelectedContratantes() {
      if (contratanteHidden) contratanteHidden.innerHTML = '';
      if (contratanteSelected) contratanteSelected.innerHTML = '';
      if (contratanteSearch) contratanteSearch.placeholder = selectedContratantes.size === 0 ? 'Todos los contratantes' : 'Seleccionar';
      if (selectedContratantes.size === 0) {
        if (contratanteSelected) {
          const badge = document.createElement('span');
          badge.className = 'badge text-bg-secondary';
          badge.textContent = 'Todos los contratantes';
          contratanteSelected.appendChild(badge);
        }
        return;
      }
      selectedContratantes.forEach(function (title, id) {
        if (contratanteHidden) {
          const inp = document.createElement('input');
          inp.type = 'hidden';
          inp.name = 'cliente_id';
          inp.value = id;
          contratanteHidden.appendChild(inp);
        }
        if (contratanteSelected) {
          const badge = document.createElement('span');
          badge.className = 'badge text-bg-primary d-inline-flex align-items-center';
          badge.textContent = title;

          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'btn-close btn-close-white ms-2';
          btn.setAttribute('aria-label', 'Quitar');
          btn.style.width = '0.5em';
          btn.style.height = '0.5em';
          btn.addEventListener('click', function () {
            selectedContratantes.delete(id);
            renderSelectedContratantes();
          });
          badge.appendChild(btn);
          contratanteSelected.appendChild(badge);
        }
      });
    }

    renderSelectedContratantes();

    function showResults(clientes) {
      contratanteResults.innerHTML = '';
      const allItem = document.createElement('div');
      allItem.className = 'list-group-item';
      allItem.innerHTML = `<div class="form-check m-0"><input class="form-check-input" type="checkbox"><label class="form-check-label">Todos los contratantes</label></div>`;
      const chk = allItem.querySelector('input');
      if (chk) chk.checked = selectedContratantes.size === 0;
      allItem.addEventListener('click', function (ev) {
        ev.preventDefault();
        selectedContratantes.clear();
        renderSelectedContratantes();
        if (chk) chk.checked = true;
        if (contratanteSearch) contratanteSearch.value = '';
      });
      contratanteResults.appendChild(allItem);

      clientes.forEach(function (c) {
        const a = document.createElement('a');
        a.href = '#';
        a.className = 'list-group-item list-group-item-action';
        const title = c.razon_social || c.nombre || c.numero_documento || '';
        const sub = (c.tipo_documento && c.numero_documento) ? `${c.tipo_documento}: ${c.numero_documento}` : '';
        a.innerHTML = `<div class="d-flex w-100 justify-content-between"><div>${title}</div><small class="text-muted">${sub}</small></div>`;
        a.addEventListener('click', function (ev) {
          ev.preventDefault();
          const id = c.idCliente === null || c.idCliente === undefined ? '' : String(c.idCliente);
          if (id) {
            selectedContratantes.set(id, title);
            renderSelectedContratantes();
          }
          contratanteSearch.value = '';
          hideResults();
        });
        contratanteResults.appendChild(a);
      });
      if (!clientes || clientes.length === 0) {
        const emptyItem = document.createElement('div');
        emptyItem.className = 'list-group-item text-muted';
        emptyItem.textContent = 'No se encontraron resultados';
        contratanteResults.appendChild(emptyItem);
      }
      contratanteResults.style.display = 'block';
    }

    function searchContratantes(q) {
      fetch(`/api/clientes/buscar?q=${encodeURIComponent(q)}`, { headers: { 'Accept': 'application/json' } })
        .then(r => r.json())
        .then(data => {
          if (!data.ok) { hideResults(); return; }
          const clientes = data.clientes || [];
          showResults(clientes);
        })
        .catch(() => hideResults());
    }

    if (contratanteSearch) {
      contratanteSearch.addEventListener('input', function () {
        const q = (contratanteSearch.value || '').trim();
        if (searchTimeout) clearTimeout(searchTimeout);
        if (!q) {
          searchTimeout = setTimeout(() => searchContratantes(''), 150);
          return;
        }
        if (q.length < 2) { hideResults(); return; }
        searchTimeout = setTimeout(() => searchContratantes(q), 250);
      });
      contratanteSearch.addEventListener('focus', function () {
        const q = (contratanteSearch.value || '').trim();
        if (!q) searchContratantes('');
      });
      contratanteSearch.addEventListener('blur', function () {
        setTimeout(hideResults, 150);
      });
    }
    if (btnContratanteToggle && contratanteSearch) {
      btnContratanteToggle.addEventListener('mousedown', function (ev) {
        ev.preventDefault();
      });
      btnContratanteToggle.addEventListener('click', function (ev) {
        ev.preventDefault();
        if (contratanteResults && contratanteResults.style.display === 'block') {
          hideResults();
          return;
        }
        const q = (contratanteSearch.value || '').trim();
        if (!q) {
          searchContratantes('');
          return;
        }
        if (q.length < 2) {
          searchContratantes('');
          return;
        }
        searchContratantes(q);
      });
    }

    function renderRows(rows) {
      if (!rows || rows.length === 0) {
        const emptyMain = '<tr><td colspan="12" class="text-center text-muted">No se encontraron resultados</td></tr>';
        const emptyFull = '<tr><td colspan="27" class="text-center text-muted">No se encontraron resultados</td></tr>';
        tbody.innerHTML = emptyMain;
        if (tbodyFull) tbodyFull.innerHTML = emptyFull;
        if (info) info.textContent = '';
        if (infoFull) infoFull.textContent = '';
        return;
      }
      const htmlMain = rows.map(function (r) {
        const rowClass = getRowClass(r);
        return (
          `<tr class="${rowClass}">` +
          `<td>${r.contratante || ''}</td>` +
          `<td>${r.ruc || ''}</td>` +
          `<td>${renderPolizaCell(r)}</td>` +
          `<td>${r.ejecutivo || ''}</td>` +
          `<td>${r.cia || ''}</td>` +
          `<td>${r.cupon || ''}</td>` +
          `<td>${r.num_cuota || ''}</td>` +
          `<td>${r.fec_vencimiento_cob || ''}</td>` +
          `<td>${r.mon || ''}</td>` +
          `<td class="text-end">${fmtMoney(r.importe)}</td>` +
          `<td>${renderEstadoBadge(r)}</td>` +
          `<td class="text-end">${renderDiasVencidos(r)}</td>` +
          '</tr>'
        );
      }).join('');
      const htmlFull = rows.map(function (r) {
        const rowClass = getRowClass(r);
        return (
          `<tr class="${rowClass}">` +
          `<td>${r.asegurado || ''}</td>` +
          `<td>${r.direccion || ''}</td>` +
          `<td>${r.telefono || ''}</td>` +
          `<td>${r.contratante || ''}</td>` +
          `<td>${r.ruc || ''}</td>` +
          `<td>${renderPolizaCell(r)}</td>` +
          `<td>${r.ejecutivo || ''}</td>` +
          `<td>${r.cia || ''}</td>` +
          `<td>${r.ram || ''}</td>` +
          `<td>${r.prod || ''}</td>` +
          `<td>${r.cupon || ''}</td>` +
          `<td>${r.num_cuota || ''}</td>` +
          `<td>${r.fec_vencimiento_cob || ''}</td>` +
          `<td>${r.mon || ''}</td>` +
          `<td class="text-end">${fmtMoney(r.importe)}</td>` +
          `<td>${r.fec_pago || ''}</td>` +
          `<td>${r.factura || ''}</td>` +
          `<td class="text-end">${renderDiasVencidos(r)}</td>` +
          `<td>${r.ult_gestion || ''}</td>` +
          `<td>${r.tp || ''}</td>` +
          `<td>${r.vig_del || ''}</td>` +
          `<td>${r.vig_al || ''}</td>` +
          `<td class="text-end">${fmtMoney(r.prima_total)}</td>` +
          `<td>${r.motivo || ''}</td>` +
          `<td>${r.tp_pago || ''}</td>` +
          `<td>${r.breve_descripcion || ''}</td>` +
          `<td>${renderEstadoBadge(r)}</td>` +
          '</tr>'
        );
      }).join('');
      tbody.innerHTML = htmlMain;
      if (tbodyFull) tbodyFull.innerHTML = htmlFull;
      const infoText = `Registros: ${rows.length}`;
      if (info) info.textContent = infoText;
      if (infoFull) infoFull.textContent = infoText;
    }

    function setRows(rows) {
      allRows = Array.isArray(rows) ? rows : [];
      applyQuickFilter();
    }

    function getQuickSearchValue() {
      if (polizaCuponInput && polizaCuponInput.value) return polizaCuponInput.value;
      if (quickSearchFull && quickSearchFull.value) return quickSearchFull.value;
      if (quickSearch && quickSearch.value) return quickSearch.value;
      return '';
    }

    function syncQuickSearchValue(val) {
      const v = (val || '').toString();
      if (polizaCuponInput) polizaCuponInput.value = v;
      if (quickSearch) quickSearch.value = v;
      if (quickSearchFull) quickSearchFull.value = v;
    }

    function applyQuickFilter() {
      const needle = (getQuickSearchValue() || '').trim().toLowerCase();
      if (!needle) {
        renderRows(allRows);
        return;
      }
      const filtered = allRows.filter(function (r) {
        const poliza = (r && r.poliza) ? String(r.poliza).toLowerCase() : '';
        const cupon = (r && r.cupon) ? String(r.cupon).toLowerCase() : '';
        const relacionadas = (r && r.polizas_relacionadas) ? String(r.polizas_relacionadas).toLowerCase() : '';
        return poliza.includes(needle) || cupon.includes(needle) || relacionadas.includes(needle);
      });
      renderRows(filtered);
    }

    function loadReporte() {
      const loadingMain = '<tr><td colspan="12" class="text-center text-muted">Cargando...</td></tr>';
      const loadingFull = '<tr><td colspan="27" class="text-center text-muted">Cargando...</td></tr>';
      tbody.innerHTML = loadingMain;
      if (tbodyFull) tbodyFull.innerHTML = loadingFull;
      const q = buildQuery();
      const url = '/api/cobranzas/estado-cuenta-cupones' + (q ? `?${q}` : '');
      fetch(url, { method: 'GET', headers: { 'Accept': 'application/json' } })
        .then(r => r.json())
        .then(data => {
          if (!data.ok) {
            const errMain = `<tr><td colspan="12" class="text-center text-danger">${data.error || 'Error'}</td></tr>`;
            const errFull = `<tr><td colspan="27" class="text-center text-danger">${data.error || 'Error'}</td></tr>`;
            tbody.innerHTML = errMain;
            if (tbodyFull) tbodyFull.innerHTML = errFull;
            if (info) info.textContent = '';
            if (infoFull) infoFull.textContent = '';
            return;
          }
          setRows(data.rows || []);
        })
        .catch(() => {
          const errMain = '<tr><td colspan="12" class="text-center text-danger">Error de conexión</td></tr>';
          const errFull = '<tr><td colspan="27" class="text-center text-danger">Error de conexión</td></tr>';
          tbody.innerHTML = errMain;
          if (tbodyFull) tbodyFull.innerHTML = errFull;
          if (info) info.textContent = '';
          if (infoFull) infoFull.textContent = '';
        });
    }

    if (form) {
      form.addEventListener('submit', function (ev) {
        ev.preventDefault();
        if (!validateRequiredFilters()) return;
        loadReporte();
      });
    }

    if (btnExport) {
      btnExport.addEventListener('click', function () {
        if (!validateRequiredFilters()) return;
        const q = buildQuery();
        const url = '/api/cobranzas/estado-cuenta-cupones/export/xlsx' + (q ? `?${q}` : '');
        window.open(url, '_blank');
      });
    }

    if (btnClear) {
      btnClear.addEventListener('click', function () {
        clearAlert();
        form.reset();
        const inpDesde = form.querySelector('input[name="fecha_desde"]');
        const inpHasta = form.querySelector('input[name="fecha_hasta"]');
        if (inpDesde) inpDesde.classList.remove('is-invalid');
        if (inpHasta) inpHasta.classList.remove('is-invalid');
        if (contratanteSearch) contratanteSearch.classList.remove('is-invalid');
        document.querySelectorAll('[data-ms-name]').forEach(function (root) {
          const btn = root.querySelector('button');
          if (btn) btn.classList.remove('is-invalid', 'border', 'border-danger');
        });
        contratanteSearch.value = '';
        hideResults();
        selectedContratantes.clear();
        renderSelectedContratantes();
        multiSelects.forEach(function (ms) { ms.reset(); });
        syncQuickSearchValue('');
        allRows = [];
        const initMain = '<tr><td colspan="12" class="text-center text-muted">Use los filtros y pulse Procesar Archivo.</td></tr>';
        const initFull = '<tr><td colspan="27" class="text-center text-muted">Use los filtros y pulse Procesar Archivo.</td></tr>';
        tbody.innerHTML = initMain;
        if (tbodyFull) tbodyFull.innerHTML = initFull;
        if (info) info.textContent = '';
        if (infoFull) infoFull.textContent = '';
      });
    }

    if (form) {
      const inpDesde = form.querySelector('input[name="fecha_desde"]');
      const inpHasta = form.querySelector('input[name="fecha_hasta"]');
      if (inpDesde) inpDesde.addEventListener('change', function () { inpDesde.classList.remove('is-invalid'); clearAlert(); });
      if (inpHasta) inpHasta.addEventListener('change', function () { inpHasta.classList.remove('is-invalid'); clearAlert(); });
    }

    document.querySelectorAll('[data-ms-name]').forEach(function (root) {
      root.addEventListener('change', function () {
        const btn = root.querySelector('button');
        if (btn) btn.classList.remove('is-invalid', 'border', 'border-danger');
        clearAlert();
      });
    });

    if (contratanteSearch) {
      contratanteSearch.addEventListener('input', function () {
        contratanteSearch.classList.remove('is-invalid');
      });
    }

    if (polizaCuponInput) {
      polizaCuponInput.addEventListener('input', function () {
        syncQuickSearchValue(polizaCuponInput.value);
        applyQuickFilter();
      });
    }
    if (quickSearch) {
      quickSearch.addEventListener('input', function () {
        syncQuickSearchValue(quickSearch.value);
        applyQuickFilter();
      });
    }
    if (quickSearchFull) {
      quickSearchFull.addEventListener('input', function () {
        syncQuickSearchValue(quickSearchFull.value);
        applyQuickFilter();
      });
    }
    if (btnClearQuickSearch) {
      btnClearQuickSearch.addEventListener('click', function () {
        syncQuickSearchValue('');
        applyQuickFilter();
      });
    }
    if (btnClearQuickSearchFull) {
      btnClearQuickSearchFull.addEventListener('click', function () {
        syncQuickSearchValue('');
        applyQuickFilter();
      });
    }
    if (modalFull && typeof modalFull.addEventListener === 'function') {
      modalFull.addEventListener('shown.bs.modal', function () {
        if (quickSearchFull) quickSearchFull.focus();
      });
    }
  });
})();
