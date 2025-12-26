document.addEventListener('DOMContentLoaded', () => {
  // Base URL para recargar con distintos parámetros
  const card = document.querySelector('.card[data-base-url]');
  const baseUrl = card?.getAttribute('data-base-url') || window.location.pathname;

  // Sincronizar tamaño de página con la URL
  const params = new URLSearchParams(window.location.search);
  const pageSizeSel = document.getElementById('page-size') || document.querySelector('.toolbar-pagesize select');
  if (pageSizeSel) {
    const current = parseInt(params.get('per_page') || '20', 10);
    pageSizeSel.value = String(current);
    pageSizeSel.addEventListener('change', () => {
      params.set('per_page', pageSizeSel.value);
      params.set('page', '1'); // reset a primera página al cambiar tamaño
      window.location.href = `${baseUrl}?${params.toString()}`;
    });
  }

  // Búsqueda local dentro de la página
  const searchInput = document.querySelector('.toolbar-search input');
  const table = document.getElementById('polizasListTable');
  if (searchInput && table) {
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    searchInput.addEventListener('input', () => {
      const q = searchInput.value.trim().toLowerCase();
      rows.forEach(tr => {
        tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }
});