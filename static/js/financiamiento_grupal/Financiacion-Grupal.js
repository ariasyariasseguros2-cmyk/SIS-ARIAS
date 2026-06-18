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
  let optionsLoaded = false;

  function init() {
    const tbody = document.querySelector('#financiacion-grupal-table tbody');
    addModalEl = document.getElementById('addFinanciacionGrupalModal');
    addForm = document.getElementById('addFinanciacionGrupalForm');

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

    const btnGuardarOtro = document.getElementById('btnGuardarYAgregarOtroFG');
    btnGuardarOtro?.addEventListener('click', async () => {
      await submitForm(true);
    });

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
    showInfo(`Avisos del financiamiento grupal #${id}.`);
  }

  function onCuotas(id) {
    showInfo(`Cuotas del financiamiento grupal #${id}.`);
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

    if (currentValue) {
      select.value = currentValue;
    }
  }

  function resetForm() {
    if (!addForm) return;
    addForm.reset();
    addForm.classList.remove('was-validated');
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

      showSuccess('Registro guardado correctamente.', () => {
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
