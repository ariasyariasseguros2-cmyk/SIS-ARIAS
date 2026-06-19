const FinanciacionGrupal = (() => {
  let allRows = [];
  let filteredRows = [];
  let pageSize = 20;
  let currentPage = 1;
  let pagerWrap = null;
  let pagerPrevBtn = null;
  let pagerNextBtn = null;
  let pagerInfoEl = null;
  let addModal = null;
  let addModalEl = null;
  let addForm = null;
  let convenioPdfInput = null;
  let convenioPdfStatusEl = null;
  let optionsLoaded = false;
  const searchableSelects = {};

  function init() {
    const tbody = document.querySelector('#financiacion-grupal-table tbody');
    addModalEl = document.getElementById('addFinanciacionGrupalModal');
    addForm = document.getElementById('addFinanciacionGrupalForm');
    convenioPdfInput = document.getElementById('fgConvenioPdf');
    convenioPdfStatusEl = document.getElementById('fgConvenioPdfStatus');

    if (tbody) {
      allRows = Array.from(tbody.querySelectorAll('tr')).filter((tr) => !tr.classList.contains('fg-empty-row'));
      filteredRows = [...allRows];
      ensurePager();
      renderPage();
    }

    if (addModalEl && window.bootstrap) {
      addModal = window.bootstrap.Modal.getOrCreateInstance(addModalEl);
      addModalEl.addEventListener('show.bs.modal', async () => {
        await loadOptions();
      });
    }

    if (addForm) {
      addForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        await submitForm(false);
      });
    }

    convenioPdfInput?.addEventListener('change', async (event) => {
      const file = event.target?.files?.[0];
      if (!file) {
        setPdfStatus('');
        return;
      }
      await extractPdfData(file);
    });

    const btnGuardarOtro = document.getElementById('btnGuardarYAgregarOtroFG');
    btnGuardarOtro?.addEventListener('click', async () => {
      await submitForm(true);
    });

    setupSearchableSelect('fgCliente', 'fgClienteSearch', 'Buscar cliente...');
    setupSearchableSelect('fgCompania', 'fgCompaniaSearch', 'Buscar compania...');

    if (String(window.financiamientoGrupalOpenAdd || '') === '1') {
      setTimeout(() => onAdd(), 100);
    }
  }

  function ensurePager() {
    if (pagerWrap) return;
    const toolbar = document.querySelector('.fg-toolbar-right');
    if (!toolbar) return;

    pagerWrap = document.createElement('div');
    pagerWrap.className = 'd-flex align-items-center gap-2';
    pagerWrap.innerHTML = `
      <button type="button" class="btn btn-sm btn-outline-secondary" id="fg-pager-prev">Anterior</button>
      <span class="small text-secondary" id="fg-pager-info"></span>
      <button type="button" class="btn btn-sm btn-outline-secondary" id="fg-pager-next">Siguiente</button>
    `;

    toolbar.appendChild(pagerWrap);
    pagerPrevBtn = document.getElementById('fg-pager-prev');
    pagerNextBtn = document.getElementById('fg-pager-next');
    pagerInfoEl = document.getElementById('fg-pager-info');

    pagerPrevBtn?.addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage -= 1;
        renderPage();
      }
    });

    pagerNextBtn?.addEventListener('click', () => {
      const totalPages = Math.max(1, Math.ceil(filteredRows.length / Math.max(1, pageSize)));
      if (currentPage < totalPages) {
        currentPage += 1;
        renderPage();
      }
    });
  }

  function setPdfStatus(message, tone = 'muted') {
    if (!convenioPdfStatusEl) return;
    convenioPdfStatusEl.textContent = message || '';
    convenioPdfStatusEl.className = 'small mt-1';
    if (tone === 'success') {
      convenioPdfStatusEl.classList.add('text-success');
    } else if (tone === 'error') {
      convenioPdfStatusEl.classList.add('text-danger');
    } else {
      convenioPdfStatusEl.classList.add('text-muted');
    }
  }

  function normalizeDateForInput(value) {
    const raw = String(value || '').trim();
    if (!raw) return '';
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
    const match = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    if (!match) return '';
    return `${match[3]}-${match[2].padStart(2, '0')}-${match[1].padStart(2, '0')}`;
  }

  function normalizeMonedaForSelect(value) {
    const moneda = String(value || '').trim().toUpperCase();
    if (['PEN', 'S/', 'S/.', 'SOLES'].includes(moneda)) return 'PEN';
    if (['USD', 'US$', '$', 'DOLARES'].includes(moneda)) return 'USD';
    return '';
  }

  function normalizeNumberInput(value) {
    const raw = String(value || '').trim();
    if (!raw) return '';
    const cleaned = raw.replace(/[^\d.,-]/g, '');
    if (!cleaned) return '';
    const lastDot = cleaned.lastIndexOf('.');
    const lastComma = cleaned.lastIndexOf(',');
    if (lastDot > -1 && lastComma > -1) {
      return lastDot > lastComma ? cleaned.replace(/,/g, '') : cleaned.replace(/\./g, '').replace(',', '.');
    }
    if (lastComma > -1) {
      return cleaned.replace(/\./g, '').replace(',', '.');
    }
    return cleaned;
  }

  function applyExtractedData(data) {
    const cuotas = Array.isArray(data?.cuotas) ? data.cuotas : [];
    const firstCuota = cuotas[0] || {};
    const moneda = normalizeMonedaForSelect(data?.moneda || firstCuota?.moneda || '');
    const numeroCupones = String(data?.numero_cupones || cuotas.length || '').trim();
    const primerCupon = String(data?.primer_cupon || firstCuota?.cupon || '').trim();
    const importe = normalizeNumberInput(data?.importe || firstCuota?.importe || '');
    const fechaPrimerVencimiento = normalizeDateForInput(data?.fecha_vencimiento || firstCuota?.fecha_vencimiento || '');

    if (moneda) {
      const monedaSelect = document.getElementById('fgMoneda');
      if (monedaSelect) monedaSelect.value = moneda;
    }
    if (numeroCupones) {
      const el = document.getElementById('fgNumeroCupones');
      if (el) el.value = numeroCupones;
    }
    if (primerCupon) {
      const el = document.getElementById('fgPrimerCupon');
      if (el) el.value = primerCupon;
    }
    if (importe) {
      const el = document.getElementById('fgImporte');
      if (el) el.value = importe;
    }
    if (fechaPrimerVencimiento) {
      const el = document.getElementById('fgFechaPrimerVencimiento');
      if (el) el.value = fechaPrimerVencimiento;
    }
  }

  async function extractPdfData(file) {
    const filename = String(file?.name || '').toLowerCase();
    if (!filename.endsWith('.pdf')) {
      setPdfStatus('Selecciona un archivo PDF valido.', 'error');
      return;
    }

    try {
      await loadOptions();
      setPdfStatus('Extrayendo datos del PDF...', 'muted');
      if (convenioPdfInput) convenioPdfInput.disabled = true;

      const formData = new FormData();
      formData.append('file', file);

      const resp = await fetch('/cuotas/extract', {
        method: 'POST',
        body: formData
      });
      const result = await resp.json().catch(() => ({}));
      if (!resp.ok || !result.ok) {
        throw new Error(result.error || 'No se pudieron extraer los datos del PDF.');
      }

      const data = result.data || {};
      applyExtractedData(data);

      const cuotas = Array.isArray(data.cuotas) ? data.cuotas : [];
      const convenio = String(data.convenio || '').trim();
      let status = cuotas.length > 0 ? `Se extrajeron ${cuotas.length} cuota(s) del PDF.` : 'Se completaron datos desde el PDF.';
      if (convenio) {
        status += ` Convenio: ${convenio}.`;
      }
      setPdfStatus(status, 'success');
    } catch (error) {
      setPdfStatus(error.message || 'Error extrayendo datos del PDF.', 'error');
      showError(error.message || 'Error extrayendo datos del PDF.');
    } finally {
      if (convenioPdfInput) convenioPdfInput.disabled = false;
    }
  }

  function renderPage() {
    const safePageSize = Math.max(1, pageSize);
    const total = filteredRows.length;
    const totalPages = Math.max(1, Math.ceil(total / safePageSize));

    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    allRows.forEach((row) => {
      row.style.display = 'none';
    });

    const start = (currentPage - 1) * safePageSize;
    const end = start + safePageSize;
    filteredRows.slice(start, end).forEach((row) => {
      row.style.display = '';
    });

    if (pagerWrap) {
      pagerWrap.style.display = total > 0 ? '' : 'none';
    }
    if (pagerInfoEl) {
      pagerInfoEl.textContent = total > 0 ? `Pagina ${currentPage} de ${totalPages} (${total})` : '';
    }
    if (pagerPrevBtn) pagerPrevBtn.disabled = currentPage <= 1;
    if (pagerNextBtn) pagerNextBtn.disabled = currentPage >= totalPages;
  }

  function onSearch(value) {
    const query = (value || '').trim().toLowerCase();
    currentPage = 1;
    filteredRows = allRows.filter((row) => row.innerText.toLowerCase().includes(query));
    renderPage();
  }

  function onPageSize(value) {
    pageSize = parseInt(value || '20', 10);
    currentPage = 1;
    renderPage();
  }

  function onFilter() {
    showInfo('Los filtros avanzados todavia no estan conectados.');
  }

  async function onAdd() {
    if (!addModal) {
      showInfo('No se encontro el modal de registro.');
      return;
    }
    resetForm();
    await loadOptions();
    addModal.show();
  }

  function onAvisos(id) {
    if (!id) {
      showInfo('No se encontro el financiamiento grupal seleccionado.');
      return;
    }
    const params = new URLSearchParams();
    params.set('id', id);
    window.location.href = `/menu/financiamiento-grupal-avisos?${params.toString()}`;
  }

  function onCuotas(id) {
    if (!id) {
      showInfo('No se encontro el financiamiento grupal seleccionado.');
      return;
    }
    const params = new URLSearchParams();
    params.set('id', id);
    window.location.href = `/menu/financiamiento-grupal-cuotas?${params.toString()}`;
  }

  function onEdit(id) {
    showInfo(`Editar financiamiento grupal #${id}.`);
  }

  function onDelete(id) {
    showInfo(`Eliminar financiamiento grupal #${id}.`);
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

  async function loadOptions() {
    if (optionsLoaded) return;
    try {
      const resp = await fetch('/api/financiamiento-grupal/options');
      const result = await resp.json();
      if (!resp.ok || !result.ok) {
        throw new Error(result.error || 'No se pudieron cargar las opciones.');
      }

      fillSelect('fgCliente', result.clientes || [], '** Selecciona un Cliente');
      fillSelect('fgCompania', result.companias || [], '** Selecciona un Compañía');
      fillSelect('fgMoneda', result.monedas || [], '** Selecciona un Moneda');
      optionsLoaded = true;
    } catch (error) {
      showError(error.message || 'Error cargando opciones del formulario.');
    }
  }

  function fillSelect(id, items, placeholder) {
    const select = document.getElementById(id);
    if (!select) return;
    const currentValue = select.value;
    const sortedItems = [...items].sort((a, b) => String(a?.nombre || '').localeCompare(String(b?.nombre || ''), 'es', {
      sensitivity: 'base',
      numeric: true
    }));

    if (searchableSelects[id]) {
      searchableSelects[id].items = sortedItems;
      searchableSelects[id].placeholder = placeholder;
      searchableSelects[id].selectedValue = currentValue;
      renderSearchableSelectOptions(id);
      return;
    }

    renderPlainSelectOptions(select, sortedItems, placeholder, currentValue);
  }

  function setupSearchableSelect(id, searchInputId, searchPlaceholder) {
    const select = document.getElementById(id);
    const existingSearchInput = document.getElementById(searchInputId);
    if (!select || searchableSelects[id]) return;

    const searchInput = existingSearchInput || document.createElement('input');
    if (!existingSearchInput) {
      searchInput.type = 'text';
      searchInput.className = 'form-control form-control-sm mb-2';
      searchInput.placeholder = searchPlaceholder;
      searchInput.autocomplete = 'off';
      select.parentNode?.insertBefore(searchInput, select);
    }
    searchableSelects[id] = {
      select,
      searchInput,
      items: [],
      placeholder: '',
      selectedValue: '',
    };

    searchInput.addEventListener('input', () => {
      renderSearchableSelectOptions(id);
    });

    select.addEventListener('change', () => {
      searchableSelects[id].selectedValue = select.value || '';
    });
  }

  function renderSearchableSelectOptions(id) {
    const state = searchableSelects[id];
    if (!state) return;

    const query = (state.searchInput.value || '').trim().toLowerCase();
    const filteredItems = state.items.filter((item) => String(item?.nombre || '').toLowerCase().includes(query));
    renderPlainSelectOptions(state.select, filteredItems, state.placeholder, state.selectedValue);

    if (state.selectedValue) {
      state.select.value = state.selectedValue;
      if (state.select.value !== state.selectedValue) {
        state.selectedValue = '';
      }
    }
  }

  function renderPlainSelectOptions(select, items, placeholder, selectedValue) {
    if (!select) return;
    select.innerHTML = '';

    const first = document.createElement('option');
    first.value = '';
    first.textContent = placeholder;
    select.appendChild(first);

    items.forEach((item) => {
      const option = document.createElement('option');
      option.value = item.id;
      option.textContent = item.nombre;
      select.appendChild(option);
    });

    if (selectedValue) {
      select.value = selectedValue;
    }
  }

  function resetForm() {
    if (!addForm) return;
    addForm.reset();
    addForm.classList.remove('was-validated');
    setPdfStatus('');
    Object.values(searchableSelects).forEach((state) => {
      state.selectedValue = '';
      if (state.searchInput) {
        state.searchInput.value = '';
      }
      renderSearchableSelectOptions(state.select.id);
    });
  }

  async function submitForm(keepAdding) {
    if (!addForm) return;
    if (!addForm.reportValidity()) {
      addForm.classList.add('was-validated');
      return;
    }

    const btnGuardar = document.getElementById('btnGuardarFG');
    const btnGuardarOtro = document.getElementById('btnGuardarYAgregarOtroFG');
    const activeBtn = keepAdding ? btnGuardarOtro : btnGuardar;
    const originalHtml = activeBtn ? activeBtn.innerHTML : '';

    try {
      if (btnGuardar) btnGuardar.disabled = true;
      if (btnGuardarOtro) btnGuardarOtro.disabled = true;
      if (activeBtn) {
        activeBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando...';
      }

      const payload = {
        nombre: document.getElementById('fgNombre')?.value?.trim() || '',
        cliente_id: document.getElementById('fgCliente')?.value || '',
        compania_id: document.getElementById('fgCompania')?.value || '',
        moneda: document.getElementById('fgMoneda')?.value || '',
        numero_cupones: document.getElementById('fgNumeroCupones')?.value || '',
        primer_cupon: document.getElementById('fgPrimerCupon')?.value?.trim() || '',
        importe: document.getElementById('fgImporte')?.value || '',
        fecha_primer_vencimiento: document.getElementById('fgFechaPrimerVencimiento')?.value || ''
      };

      const resp = await fetch('/api/financiamiento-grupal/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      const result = await resp.json();
      if (!resp.ok || !result.ok) {
        throw new Error(result.error || 'No se pudo guardar el registro.');
      }

      if (keepAdding) {
        showSuccess('Registro guardado correctamente.');
        window.location.href = `${window.location.pathname}?openAdd=1`;
        return;
      }

      const newId = result.id;
      showSuccess('Registro guardado correctamente.', () => {
        if (newId) {
          const params = new URLSearchParams();
          params.set('id', newId);
          window.location.href = `/menu/financiamiento-grupal-cuotas?${params.toString()}`;
          return;
        }
        window.location.reload();
      });
    } catch (error) {
      showError(error.message || 'Error guardando el financiamiento grupal.');
    } finally {
      if (btnGuardar) btnGuardar.disabled = false;
      if (btnGuardarOtro) btnGuardarOtro.disabled = false;
      if (activeBtn) activeBtn.innerHTML = originalHtml;
    }
  }

  function showSuccess(message, onClose) {
    if (window.Swal) {
      window.Swal.fire({
        icon: 'success',
        title: 'Correcto',
        text: message,
        confirmButtonText: 'Aceptar'
      }).then(() => {
        if (typeof onClose === 'function') onClose();
      });
      return;
    }
    window.alert(message);
    if (typeof onClose === 'function') onClose();
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

  return {
    init,
    onSearch,
    onPageSize,
    onFilter,
    onAdd,
    onAvisos,
    onCuotas,
    onEdit,
    onDelete
  };
})();
