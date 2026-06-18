const FinanciacionGrupal = (() => {
  let allRows = [];
  let filteredRows = [];
  let pageSize = 20;
  let currentPage = 1;
  let pagerWrap = null;
  let pagerPrevBtn = null;
  let pagerNextBtn = null;
  let pagerInfoEl = null;

  function init() {
    const tbody = document.querySelector('#financiacion-grupal-table tbody');
    if (!tbody) return;
    allRows = Array.from(tbody.querySelectorAll('tr')).filter((tr) => !tr.classList.contains('fg-empty-row'));
    filteredRows = [...allRows];
    ensurePager();
    renderPage();
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

  function onAdd() {
    showInfo('La pantalla de registro de financiamiento grupal sera conectada en el siguiente paso.');
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
