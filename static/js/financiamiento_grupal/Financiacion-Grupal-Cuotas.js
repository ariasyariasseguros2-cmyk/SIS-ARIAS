const FinanciamientoGrupalCuotas = (() => {
  let allRows = [];
  let filteredRows = [];
  let pageSize = 20;
  let currentPage = 1;
  let pagerWrap = null;
  let pagerPrevBtn = null;
  let pagerNextBtn = null;
  let pagerInfoEl = null;

  function init() {
    const tbody = document.querySelector('#fg-cuotas-table tbody');
    if (!tbody) return;

    allRows = Array.from(tbody.querySelectorAll('tr')).filter((tr) => !tr.classList.contains('fg-cuotas-empty-row'));
    filteredRows = [...allRows];
    ensurePager();
    renderPage();
  }

  function ensurePager() {
    if (pagerWrap) return;
    const toolbar = document.querySelector('.table-toolbar');
    if (!toolbar) return;

    pagerWrap = document.createElement('div');
    pagerWrap.className = 'd-flex align-items-center gap-2';
    pagerWrap.innerHTML = `
      <button type="button" class="btn btn-sm btn-outline-secondary" id="fg-cuotas-pager-prev">Anterior</button>
      <span class="small text-secondary" id="fg-cuotas-pager-info"></span>
      <button type="button" class="btn btn-sm btn-outline-secondary" id="fg-cuotas-pager-next">Siguiente</button>
    `;

    toolbar.appendChild(pagerWrap);
    pagerPrevBtn = document.getElementById('fg-cuotas-pager-prev');
    pagerNextBtn = document.getElementById('fg-cuotas-pager-next');
    pagerInfoEl = document.getElementById('fg-cuotas-pager-info');

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
    const emptyRow = document.querySelector('.fg-cuotas-empty-row');

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

    if (emptyRow) {
      emptyRow.style.display = total === 0 ? '' : 'none';
    }

    if (pagerWrap) pagerWrap.style.display = total > 0 ? '' : 'none';
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

  return {
    init,
    onSearch,
    onPageSize
  };
})();
