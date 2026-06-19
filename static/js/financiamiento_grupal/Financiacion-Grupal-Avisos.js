const FinanciamientoGrupalAvisos = (() => {
  let allRows = [];
  let filteredRows = [];
  let pageSize = 20;
  let currentPage = 1;
  let emptyRow = null;
  let searchInput = null;
  let pageSizeSelect = null;
  let prevBtn = null;
  let nextBtn = null;
  let infoEl = null;
  let totalRecordsEl = null;

  function init() {
    const tbody = document.querySelector('#fgAvisosTable tbody');
    if (!tbody) return;

    allRows = Array.from(tbody.querySelectorAll('.fg-avisos-data-row'));
    filteredRows = [...allRows];
    emptyRow = tbody.querySelector('.fg-avisos-empty-row');
    searchInput = document.getElementById('fgAvisosSearch');
    pageSizeSelect = document.getElementById('fgAvisosPageSize');
    prevBtn = document.getElementById('fgAvisosPrev');
    nextBtn = document.getElementById('fgAvisosNext');
    infoEl = document.getElementById('fgAvisosInfo');
    totalRecordsEl = document.getElementById('fgAvisosTotalRecords');

    searchInput?.addEventListener('input', () => {
      currentPage = 1;
      const query = (searchInput.value || '').trim().toLowerCase();
      filteredRows = allRows.filter((row) => row.innerText.toLowerCase().includes(query));
      renderPage();
    });

    pageSizeSelect?.addEventListener('change', () => {
      pageSize = Math.max(1, parseInt(pageSizeSelect.value || '20', 10));
      currentPage = 1;
      renderPage();
    });

    prevBtn?.addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage -= 1;
        renderPage();
      }
    });

    nextBtn?.addEventListener('click', () => {
      const totalPages = Math.max(1, Math.ceil(filteredRows.length / Math.max(1, pageSize)));
      if (currentPage < totalPages) {
        currentPage += 1;
        renderPage();
      }
    });

    renderPage();
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

    if (emptyRow) {
      emptyRow.style.display = total === 0 ? '' : 'none';
    }

    const start = (currentPage - 1) * safePageSize;
    const end = start + safePageSize;
    filteredRows.slice(start, end).forEach((row) => {
      row.style.display = '';
    });

    if (infoEl) {
      infoEl.textContent = total > 0 ? `Pagina ${currentPage} de ${totalPages} (${total})` : 'Pagina 0 de 0 (0)';
    }
    if (prevBtn) prevBtn.disabled = total === 0 || currentPage <= 1;
    if (nextBtn) nextBtn.disabled = total === 0 || currentPage >= totalPages;
    if (totalRecordsEl) {
      totalRecordsEl.textContent = `Total de registros: ${total}`;
    }
  }

  function onAdd() {
    const message = 'La carga de avisos para este financiamiento grupal aun no esta conectada.';
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
    onAdd
  };
})();
