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
            alert('Acción Cuotas pendiente de implementación.');
        }
        if (t.classList.contains('btn-detalles')) {
            alert('Acción Detalles pendiente de implementación.');
        }
        if (t.classList.contains('btn-editar')) {
            alert('Acción Editar pendiente de implementación.');
        }
        if (t.classList.contains('btn-eliminar')) {
            if (confirm('¿Eliminar este registro?')) {
                alert('Eliminado (demo).');
            }
        }
    });
})();