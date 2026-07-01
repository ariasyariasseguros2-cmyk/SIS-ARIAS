const FinanciamientoGrupalAvisos = (() => {
  let financiamientoId = '';
  let allRows = [];
  let filteredRows = [];
  let pageSize = 20;
  let currentPage = 1;

  let searchInput = null;
  let pageSizeSelect = null;
  let prevBtn = null;
  let nextBtn = null;
  let infoEl = null;
  let totalRecordsEl = null;
  let tableBody = null;

  let addModalEl = null;
  let addModal = null;
  let candidatesBody = null;
  let candidatesSearchInput = null;
  let candidatesInfoEl = null;
  let candidatesPrevBtn = null;
  let candidatesNextBtn = null;
  let candidates = [];
  let filteredCandidates = [];
  let candidatesPage = 1;
  const candidatesPageSize = 10;

  async function init() {
    financiamientoId = String(window.financiamientoGrupalId || '').trim();
    tableBody = document.querySelector('#fgAvisosTable tbody');
    if (!financiamientoId || !tableBody) return;

    searchInput = document.getElementById('fgAvisosSearch');
    pageSizeSelect = document.getElementById('fgAvisosPageSize');
    prevBtn = document.getElementById('fgAvisosPrev');
    nextBtn = document.getElementById('fgAvisosNext');
    infoEl = document.getElementById('fgAvisosInfo');
    totalRecordsEl = document.getElementById('fgAvisosTotalRecords');

    addModalEl = document.getElementById('fgAvisosAddModal');
    if (addModalEl && window.bootstrap) {
      addModal = window.bootstrap.Modal.getOrCreateInstance(addModalEl);
    }
    candidatesBody = document.querySelector('#fgAvisosCandidatesTable tbody');
    candidatesSearchInput = document.getElementById('fgAvisosCandidatesSearch');
    candidatesInfoEl = document.getElementById('fgAvisosCandidatesInfo');
    candidatesPrevBtn = document.getElementById('fgAvisosCandidatesPrev');
    candidatesNextBtn = document.getElementById('fgAvisosCandidatesNext');

    searchInput?.addEventListener('input', () => {
      const query = (searchInput.value || '').trim().toLowerCase();
      currentPage = 1;
      filteredRows = allRows.filter((row) => row._search.includes(query));
      renderMainTable();
    });

    pageSizeSelect?.addEventListener('change', () => {
      pageSize = Math.max(1, parseInt(pageSizeSelect.value || '20', 10));
      currentPage = 1;
      renderMainTable();
    });

    prevBtn?.addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage -= 1;
        renderMainTable();
      }
    });

    nextBtn?.addEventListener('click', () => {
      const totalPages = Math.max(1, Math.ceil(filteredRows.length / Math.max(1, pageSize)));
      if (currentPage < totalPages) {
        currentPage += 1;
        renderMainTable();
      }
    });

    candidatesPrevBtn?.addEventListener('click', () => {
      if (candidatesPage > 1) {
        candidatesPage -= 1;
        renderCandidates();
      }
    });

    candidatesNextBtn?.addEventListener('click', () => {
      const totalPages = Math.max(1, Math.ceil(filteredCandidates.length / candidatesPageSize));
      if (candidatesPage < totalPages) {
        candidatesPage += 1;
        renderCandidates();
      }
    });

    candidatesSearchInput?.addEventListener('input', () => {
      candidatesPage = 1;
      applyCandidatesFilter();
      renderCandidates();
    });

    document.addEventListener('click', async (e) => {
      const addBtn = e.target.closest('[data-fg-add-aviso]');
      if (addBtn) {
        e.preventDefault();
        const polizaId = addBtn.getAttribute('data-fg-add-aviso');
        await addAviso(polizaId, addBtn);
        return;
      }

      const detBtn = e.target.closest('[data-fg-detalles-item]');
      if (detBtn) {
        e.preventDefault();
        const itemId = detBtn.getAttribute('data-fg-detalles-item');
        showInfo(`Detalles del aviso #${itemId}.`);
        return;
      }

      const removeBtn = e.target.closest('[data-fg-remove-item]');
      if (removeBtn) {
        e.preventDefault();
        const itemId = removeBtn.getAttribute('data-fg-remove-item');
        await removeAviso(itemId, removeBtn);
      }
    });

    await reloadMainRows();

    if (String(window.financiamientoGrupalOpenAdd || '') === '1') {
      setTimeout(() => onAdd(), 150);
    }
  }

  function showInfo(message) {
    if (window.Swal) {
      window.Swal.fire({
        icon: 'info',
        title: 'Aviso',
        text: message,
        confirmButtonText: 'Aceptar'
      });
      return;
    }
    window.alert(message);
  }

  function showError(message) {
    if (window.Swal) {
      window.Swal.fire({
        icon: 'error',
        title: 'Error',
        text: message,
        confirmButtonText: 'Aceptar'
      });
      return;
    }
    window.alert(message);
  }

  function showSuccess(message) {
    if (window.Swal) {
      window.Swal.fire({
        icon: 'success',
        title: 'Correcto',
        text: message,
        confirmButtonText: 'Aceptar'
      });
      return;
    }
    window.alert(message);
  }

  async function fetchJson(url, options) {
    const resp = await fetch(url, options);
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || !data.ok) {
      const msg = data.error || 'Error de servidor';
      throw new Error(msg);
    }
    return data;
  }

  async function reloadMainRows() {
    try {
      const data = await fetchJson(`/api/financiamiento-grupal/${encodeURIComponent(financiamientoId)}/avisos`);
      allRows = (data.rows || []).map((r) => ({
        ...r,
        _search: `${r.aviso || ''} ${r.poliza || ''} ${r.contratante || ''} ${r.compania || ''} ${r.ramo || ''} ${r.tipo || ''} ${r.moneda || ''} ${r.vig_inicio || ''} ${r.vig_fin || ''} ${r.nro_operacion || ''} ${r.motivo || ''}`.toLowerCase()
      }));
      const query = (searchInput?.value || '').trim().toLowerCase();
      filteredRows = query ? allRows.filter((row) => row._search.includes(query)) : [...allRows];
      currentPage = 1;
      renderMainTable();
    } catch (err) {
      allRows = [];
      filteredRows = [];
      renderMainTable();
      showError(err.message || 'No se pudo cargar la lista.');
    }
  }

  function renderMainTable() {
    const safePageSize = Math.max(1, pageSize);
    const total = filteredRows.length;
    const totalPages = Math.max(1, Math.ceil(total / safePageSize));
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    const start = (currentPage - 1) * safePageSize;
    const pageRows = filteredRows.slice(start, start + safePageSize);

    if (tableBody) {
      if (pageRows.length === 0) {
        tableBody.innerHTML = '<tr class="fg-avisos-empty-row"><td colspan="15" class="text-center py-4">No tenemos datos disponibles</td></tr>';
      } else {
        tableBody.innerHTML = pageRows.map(renderMainRow).join('');
      }
    }

    if (infoEl) {
      infoEl.textContent = total > 0 ? `Pagina ${currentPage} de ${totalPages} (${total})` : 'Pagina 0 de 0 (0)';
    }
    if (prevBtn) prevBtn.disabled = total === 0 || currentPage <= 1;
    if (nextBtn) nextBtn.disabled = total === 0 || currentPage >= totalPages;
    if (totalRecordsEl) totalRecordsEl.textContent = `Total de registros: ${total}`;
  }

  function renderMainRow(r) {
    const safe = (v) => (v === null || v === undefined || String(v).trim() === '' ? '—' : String(v));
    const safeMoney = (v) => (v === null || v === undefined || String(v).trim() === '' ? '0.00' : String(v));
    const formatMoneda = (v) => {
      const moneda = String(v || '').trim().toUpperCase();
      if (['PEN', 'S/', 'S/.', 'SOLES'].includes(moneda)) return 'S/';
      if (['USD', 'US$', '$', 'DOLARES'].includes(moneda)) return 'US$';
      return safe(v);
    };
    const itemId = safe(r.id_item);
    return `
      <tr class="fg-avisos-data-row">
        <td>${safe(r.aviso)}</td>
        <td>${safe(r.poliza)}</td>
        <td>${safe(r.contratante)}</td>
        <td>${safe(r.compania)}</td>
        <td>${safe(r.ramo)}</td>
        <td>${safe(r.tipo)}</td>
        <td>${formatMoneda(r.moneda)}</td>
        <td>${safeMoney(r.prima_comercial)}</td>
        <td>${safeMoney(r.prima_neta)}</td>
        <td>${safeMoney(r.prima_total)}</td>
        <td>${safe(r.vig_inicio)}</td>
        <td>${safe(r.vig_fin)}</td>
        <td>${safe(r.nro_operacion)}</td>
        <td>${safe(r.motivo)}</td>
        <td class="text-end">
          <div class="action-buttons justify-content-end">
            <button type="button" class="btn-action btn-danger" data-fg-remove-item="${itemId}">Eliminar</button>
            <button type="button" class="btn-action btn-info" data-fg-detalles-item="${itemId}">Detalles</button>
          </div>
        </td>
      </tr>
    `;
  }

  async function onAdd() {
    if (!addModal) {
      showError('No se encontro el modal de seleccion.');
      return;
    }
    try {
      await loadCandidates();
      addModal.show();
    } catch (err) {
      showError(err.message || 'No se pudieron cargar los candidatos.');
    }
  }

  async function loadCandidates() {
    const data = await fetchJson(`/api/financiamiento-grupal/${encodeURIComponent(financiamientoId)}/avisos/candidatos`);
    candidates = (data.rows || []).map((row) => ({
      ...row,
      _search: `${row.poliza || ''} ${row.aviso || ''}`.toLowerCase()
    }));
    candidatesPage = 1;
    if (candidatesSearchInput) candidatesSearchInput.value = '';
    applyCandidatesFilter();
    renderCandidates();
  }

  function applyCandidatesFilter() {
    const query = (candidatesSearchInput?.value || '').trim().toLowerCase();
    filteredCandidates = query
      ? candidates.filter((row) => row._search.includes(query))
      : [...candidates];
  }

  function renderCandidates() {
    const total = filteredCandidates.length;
    const totalPages = Math.max(1, Math.ceil(total / candidatesPageSize));
    if (candidatesPage > totalPages) candidatesPage = totalPages;
    if (candidatesPage < 1) candidatesPage = 1;

    const start = (candidatesPage - 1) * candidatesPageSize;
    const slice = filteredCandidates.slice(start, start + candidatesPageSize);

    if (candidatesBody) {
      if (slice.length === 0) {
        candidatesBody.innerHTML = '<tr class="fg-avisos-candidates-empty"><td colspan="9" class="text-center text-muted py-4">No tenemos datos disponibles</td></tr>';
      } else {
        candidatesBody.innerHTML = slice.map(renderCandidateRow).join('');
      }
    }

    if (candidatesInfoEl) {
      if (total === 0) {
        candidatesInfoEl.textContent = '';
      } else {
        const from = start + 1;
        const to = Math.min(total, start + slice.length);
        candidatesInfoEl.textContent = `Mostrando registros del ${from} al ${to} de un total de ${total} registros`;
      }
    }
    if (candidatesPrevBtn) candidatesPrevBtn.disabled = total === 0 || candidatesPage <= 1;
    if (candidatesNextBtn) candidatesNextBtn.disabled = total === 0 || candidatesPage >= totalPages;
  }

  function renderCandidateRow(r) {
    const safe = (v) => (v === null || v === undefined || String(v).trim() === '' ? '—' : String(v));
    const safeMoney = (v) => (v === null || v === undefined || String(v).trim() === '' ? '0.00' : String(v));
    const formatMoneda = (v) => {
      const moneda = String(v || '').trim().toUpperCase();
      if (['PEN', 'S/', 'S/.', 'SOLES'].includes(moneda)) return 'S/';
      if (['USD', 'US$', '$', 'DOLARES'].includes(moneda)) return 'US$';
      return safe(v);
    };
    const polizaId = safe(r.idPoliza);
    return `
      <tr>
        <td><a href="#" data-fg-add-aviso="${polizaId}">Agregar</a></td>
        <td>${safe(r.poliza)}</td>
        <td>${safe(r.aviso)}</td>
        <td>${safe(r.vig_inicio)}</td>
        <td>${safe(r.vig_fin)}</td>
        <td>${formatMoneda(r.moneda)}</td>
        <td>${safeMoney(r.prima_comercial)}</td>
        <td>${safeMoney(r.prima_neta)}</td>
        <td>${safeMoney(r.prima_total)}</td>
      </tr>
    `;
  }

  async function addAviso(polizaId, triggerEl) {
    const originalHtml = triggerEl ? triggerEl.innerHTML : '';
    try {
      if (triggerEl) {
        triggerEl.classList.add('disabled');
        triggerEl.innerHTML = 'Agregando...';
      }
      await fetchJson(`/api/financiamiento-grupal/${encodeURIComponent(financiamientoId)}/avisos/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ poliza_id: polizaId })
      });
      showSuccess('Agregado correctamente.');
      candidates = candidates.filter((c) => String(c.idPoliza) !== String(polizaId));
      applyCandidatesFilter();
      renderCandidates();
      await reloadMainRows();
    } catch (err) {
      showError(err.message || 'No se pudo agregar.');
    } finally {
      if (triggerEl) {
        triggerEl.classList.remove('disabled');
        triggerEl.innerHTML = originalHtml;
      }
    }
  }

  async function removeAviso(itemId, triggerEl) {
    if (!itemId) {
      showError('No se encontro el aviso seleccionado.');
      return;
    }

    const confirmed = await confirmDelete(
      '¿Eliminar aviso?',
      'Si es el ultimo aviso del grupo, las cuotas quedaran en 0.'
    );
    if (!confirmed) return;

    const originalHtml = triggerEl ? triggerEl.innerHTML : '';
    try {
      if (triggerEl) {
        triggerEl.disabled = true;
        triggerEl.innerHTML = 'Eliminando...';
      }
      await fetchJson(`/api/financiamiento-grupal/${encodeURIComponent(financiamientoId)}/avisos/remove/${encodeURIComponent(itemId)}`, {
        method: 'DELETE'
      });
      showSuccess('Eliminado correctamente.', () => {
        window.location.reload();
      });
    } catch (err) {
      showError(err.message || 'No se pudo eliminar.');
    } finally {
      if (triggerEl) {
        triggerEl.disabled = false;
        triggerEl.innerHTML = originalHtml;
      }
    }
  }

  async function confirmDelete(title, text) {
    if (window.Swal) {
      const result = await window.Swal.fire({
        icon: 'warning',
        title,
        text,
        showCancelButton: true,
        confirmButtonText: 'Eliminar',
        cancelButtonText: 'Cancelar',
        confirmButtonColor: '#dc3545'
      });
      return Boolean(result?.isConfirmed);
    }
    return window.confirm(text || title);
  }

  return {
    init,
    onAdd
  };
})();
