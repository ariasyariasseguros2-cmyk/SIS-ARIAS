(function () {
    const input = document.getElementById('primasSearch');
    const table = document.getElementById('primasTable');
    if (input && table) {
        input.addEventListener('input', () => {
            const q = input.value.toLowerCase();
            for (const tr of table.querySelectorAll('tbody tr')) {
                const text = tr.innerText.toLowerCase();
                tr.style.display = text.includes(q) ? '' : 'none';
            }
        });
    }

    document.addEventListener('click', (e) => {
        const t = e.target.closest('button');
        if (!t) return;
        if (t.classList.contains('btn-pdf')) {
            const url = t.getAttribute('data-pdf');
            if (url) {
                window.open(url, '_blank', 'noopener');
            } else {
                alert('No hay PDF disponible para este registro.');
            }
        }
        if (t.classList.contains('btn-cuotas')) {
            const poliza = t.getAttribute('data-poliza')
                || t.closest('tr')?.querySelector('td:nth-child(2)')?.textContent?.trim()
                || '';
            if (poliza) {
                window.location.href = `/menu/cuotas?poliza=${encodeURIComponent(poliza)}`;
            } else {
                alert('No se pudo obtener el número de póliza.');
            }
            return;
        }
        if (t.classList.contains('btn-detalles')) {
            const id = t.getAttribute('data-id');
            if (id) {
                window.location.href = `/menu/detalles-primas?id=${id}`;
            } else {
                alert('No se pudo obtener el ID para ver detalles.');
            }
        }
        if (t.classList.contains('btn-editar')) {
            const id = t.getAttribute('data-id');
            if (id) {
                window.location.href = `/menu/editar-primas?id=${id}`;
            } else {
                alert('No se pudo obtener el ID del registro.');
            }
        }
        if (t.classList.contains('btn-eliminar')) {
            if (confirm('¿Eliminar este registro?')) {
                alert('Eliminado (demo).');
            }
        }
    });
})();