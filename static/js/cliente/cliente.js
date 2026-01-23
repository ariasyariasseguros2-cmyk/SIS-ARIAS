(function () {
    document.addEventListener('DOMContentLoaded', function () {
        const input = document.getElementById('searchInput');
        const table = document.getElementById('clientesTable');
        const rows = table ? Array.from(table.querySelectorAll('tbody tr')) : [];
        const polizasUrl = table ? table.getAttribute('data-polizas-url') : null;

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

        // Acciones: pólizas, contactos, PDF
        if (table) {
            table.addEventListener('click', (e) => {
                const btn = e.target.closest('button');
                if (!btn) return;
                // Ignorar botones de restaurar para no activar la rama que redirige a pólizas
                if (btn.classList.contains('btn-restore-cliente')) return;

                const row = e.target.closest('tr');
                const razon = row?.querySelector('td:nth-child(2)')?.textContent?.trim() || '';

                if (btn.classList.contains('btn-primary') || btn.classList.contains('btn-outline-primary')) {
                    // Ir a la vista Pólizas EN SEGURO (sin parámetros en URL)
                    if (polizasUrl) {
                        const tipoDoc = row?.querySelector('td:nth-child(3)')?.textContent?.trim() || '';
                        const numeroDoc = row?.querySelector('td:nth-child(4)')?.textContent?.trim() || '';
                        const telefono = row?.querySelector('td:nth-child(5)')?.textContent?.trim() || '';
                        const subAgente = row?.querySelector('td:nth-child(6)')?.textContent?.trim() || '';
                        const idCliente = row?.dataset?.idcliente || null;

                        fetch('/clientes/select', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                nombre: razon,
                                tipo_doc: tipoDoc,
                                n_doc: numeroDoc,
                                tel: telefono,
                                subagente: subAgente,
                                idCliente: idCliente
                            })
                        })
                        .then(r => r.json())
                        .then(res => {
                            if (res.ok) {
                                window.location.href = polizasUrl; // sin query string
                            } else {
                                alert(res.errors?.[0] || 'No se pudo seleccionar el cliente.');
                            }
                        })
                        .catch(() => alert('Error al seleccionar el cliente.'));
                    } else {
                        alert(`Abrir pólizas de: ${razon}`);
                    }
                    return;
                } else if (btn.classList.contains('btn-success') || btn.classList.contains('btn-outline-success')) {
                    alert(`Abrir contactos de: ${razon}`);
                } else if (btn.classList.contains('btn-delete-cliente')) {
                    // Eliminar cliente (borrado lógico)
                    const idCliente = btn.getAttribute('data-id');
                    const nombreCliente = btn.getAttribute('data-nombre');

                    if (!confirm(`¿Está seguro de eliminar al cliente "${nombreCliente}"?\n\nEsta acción se puede revertir desde la base de datos.`)) {
                        return;
                    }

                    fetch('/clientes/delete', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({idCliente: idCliente})
                    })
                    .then(r => r.json())
                    .then(data => {
                        if (data.ok) {
                            alert('Cliente eliminado correctamente');
                            location.reload();
                        } else {
                            alert('Error: ' + (data.errors || ['Desconocido']).join(', '));
                        }
                    })
                    .catch(err => alert('Error de red: ' + err));
                } else if (btn.classList.contains('btn-danger') || btn.classList.contains('btn-outline-danger')) {
                    alert(`Generar PDF para: ${razon}`);
                }
            });
        }
    });
})();