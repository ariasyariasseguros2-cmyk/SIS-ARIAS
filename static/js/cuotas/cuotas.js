const Cuotas = (() => {
  let allRows = [];
  let pageSize = 20;

  function bootstrap() {
    const tbody = document.querySelector('#cuotas-table tbody');
    if (!tbody) return;
    allRows = Array.from(tbody.querySelectorAll('tr'));
    applyFilter('');
  }

  function applyFilter(query) {
    const q = (query || '').toLowerCase();
    let shown = 0;
    allRows.forEach(tr => {
      const text = tr.innerText.toLowerCase();
      const match = text.indexOf(q) !== -1;
      if (match && shown < pageSize) {
        tr.style.display = '';
        shown++;
      } else {
        tr.style.display = 'none';
      }
    });
  }

  function onSearch(val) { applyFilter(val); }
  function onPageSize(val) {
    pageSize = parseInt(val || '20', 10);
    const input = document.getElementById('cuotas-search');
    applyFilter(input ? input.value : '');
  }

  // Action stubs
  function onPDF(idx) { alert(`Descargar PDF fila ${idx + 1}`); }
  function onRevert(idx) { alert(`Revertir fila ${idx + 1}`); }
  function onDetails(idx) { alert(`Ver detalles fila ${idx + 1}`); }
  function onEdit(idx) { alert(`Editar fila ${idx + 1}`); }
  function onDelete(idx) {
    const tbody = document.querySelector('#cuotas-table tbody');
    const tr = tbody.querySelectorAll('tr')[idx];
    if (tr && confirm('¿Eliminar esta cuota?')) tr.remove();
  }
  function onAdd() { alert('Añadir nueva cuota (pendiente de implementación)'); }

  return { bootstrap, onSearch, onPageSize, onPDF, onRevert, onDetails, onEdit, onDelete, onAdd };
})();