(function () {
  document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('polizasSearch');
    const table = document.getElementById('polizasTable');
    const rows = table ? Array.from(table.querySelectorAll('tbody tr')) : [];

    function filterRows(term) {
      const q = term.trim().toLowerCase();
      rows.forEach(tr => {
        const text = tr.textContent.toLowerCase();
        tr.style.display = text.includes(q) ? '' : 'none';
      });
    }

    input?.addEventListener('input', (e) => filterRows(e.target.value));

    // Acciones (placeholders)
    table?.addEventListener('click', (e) => {
      const btn = e.target.closest('button');
      if (!btn) return;
      const label = btn.textContent.trim();
      const row = e.target.closest('tr');
      const poliza = row?.querySelector('td:nth-child(6)')?.textContent?.trim() || '';
      alert(`${label} — Póliza: ${poliza}`);
    });
  });
})();