(function () {
    document.addEventListener('DOMContentLoaded', function () {
        const input = document.getElementById('searchInput');
        const table = document.getElementById('clientesTable');
        const rows = table ? Array.from(table.querySelectorAll('tbody tr')) : [];

        function filterRows(term) {
            const q = term.trim().toLowerCase();
            rows.forEach(tr => {
                const text = tr.textContent.toLowerCase();
                tr.style.display = text.includes(q) ? '' : 'none';
            });
        }

        if (input) {
            input.addEventListener('input', (e) => filterRows(e.target.value));
        }

        // Acciones (placeholders): pólizas, contactos, PDF
        table.addEventListener('click', (e) => {
            const btn = e.target.closest('button');
            if (!btn) return;
            const row = e.target.closest('tr');
            const razon = row?.querySelector('td:nth-child(2)')?.textContent?.trim() || '';
            if (btn.classList.contains('btn-outline-primary')) {
                alert(`Abrir pólizas de: ${razon}`);
            } else if (btn.classList.contains('btn-outline-success')) {
                alert(`Abrir contactos de: ${razon}`);
            } else if (btn.classList.contains('btn-outline-danger')) {
                alert(`Generar PDF para: ${razon}`);
            }
        });
    });
})();