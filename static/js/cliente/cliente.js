(function () {
    document.addEventListener('DOMContentLoaded', function () {
        const input = document.getElementById('searchInput');
        const table = document.getElementById('clientesTable');
        let rows = table ? Array.from(table.querySelectorAll('tbody tr')) : [];
        const initialRows = [...rows]; // Keep a copy of initial rows
        const polizasUrl = table ? table.getAttribute('data-polizas-url') : null;
        const currentPage = window.currentPage || '';
        const canEdit = !!document.querySelector('.btn-edit-cliente');
        const canDelete = !!document.querySelector('.btn-delete-cliente');
        const canRestore = !!document.querySelector('.btn-restore-cliente');

        function debounce(func, wait) {
            let timeout;
            return function(...args) {
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(this, args), wait);
            };
        }

        function filterRows(term) {
            const q = term.trim();
            const tbody = table.querySelector('tbody');
            if (!tbody) return;

            if (!q) {
                tbody.innerHTML = '';
                initialRows.forEach(row => tbody.appendChild(row));
                rows = initialRows;
                return;
            }

            fetch(`/api/clientes/search?q=${encodeURIComponent(q)}`)
                .then(r => r.json())
                .then(data => {
                    if (data.ok) {
                        tbody.innerHTML = '';
                        const newRows = [];
                        data.rows.forEach(r => {
                            const tr = document.createElement('tr');
                            tr.setAttribute('data-idcliente', r.idCliente);

                            let actionCellHtml = '';
                            if (currentPage === 'clientes-anulados') {
                                actionCellHtml = `
                                <td class="text-end">
                                    <div class="d-flex gap-2 justify-content-end">
                                        ${canRestore ? `<button type="button" class="btn btn-sm btn-info btn-lift btn-restore-cliente" data-id="${r.idCliente}"><i class="bi-arrow-clockwise"></i> Restaurar</button>` : ''}
                                    </div>
                                </td>
                                `;
                            } else {
                                actionCellHtml = `
                                <td class="text-end">
                                    <div class="d-flex gap-2 justify-content-end">
                                        ${canEdit ? `<button type="button" class="btn btn-warning btn-sm btn-lift btn-edit-cliente" data-id="${r.idCliente}"><i class="bi-pencil"></i> Editar</button>` : ''}
                                        <button type="button" class="btn btn-primary btn-sm btn-lift">Pólizas</button>
                                        <button type="button" class="btn btn-success btn-sm btn-lift">Contactos</button>
                                        ${canDelete ? `<button type="button" class="btn btn-danger btn-sm btn-lift btn-delete-cliente" data-id="${r.idCliente}" data-nombre="${r.razon_social}"><i class="bi-trash"></i> Eliminar</button>` : ''}
                                    </div>
                                </td>
                                `;
                            }

                            tr.innerHTML = `
                                <td>${r.fec_reg || ''}</td>
                                <td>${r.razon_social || ''}</td>
                                <td>${r.doc || ''}</td>
                                <td>${r.n_doc || ''}</td>
                                <td>${r.tel || ''}</td>
                                <td>${r.subagente || ''}</td>
                                <td><a href="mailto:${r.email || ''}">${r.email || ''}</a></td>
                                <td>${r.direccion || ''}</td>
                                ${actionCellHtml}
                            `;
                            tbody.appendChild(tr);
                            newRows.push(tr);
                        });
                        rows = newRows;
                    }
                })
                .catch(console.error);
        }

        const debouncedFilter = debounce(filterRows, 300);

        if (input) {
            input.addEventListener('input', (e) => debouncedFilter(e.target.value));
        }

        // filtros y ordenamiento
        let currentSort = { column: null, ascending: true };
        const orderLinks = document.querySelectorAll('[data-order]');

        orderLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const orderBy = e.target.getAttribute('data-order');

                // Si es la misma columna, alternar ascendente/descendente
                if (currentSort.column === orderBy) {
                    currentSort.ascending = !currentSort.ascending;
                } else {
                    currentSort.column = orderBy;
                    currentSort.ascending = true;
                }

                sortTable(orderBy, currentSort.ascending);
                updateSortIndicator(link);
            });
        });

        function updateSortIndicator(activeLink) {

            orderLinks.forEach(link => {
                const icon = link.querySelector('i');
                const iconHTML = icon ? icon.outerHTML : '';
                const text = link.textContent.replace(' ↑', '').replace(' ↓', '').trim();
                link.innerHTML = iconHTML + ' ' + text;
            });


            const icon = activeLink.querySelector('i');
            const iconHTML = icon ? icon.outerHTML : '';
            const text = activeLink.textContent.replace(' ↑', '').replace(' ↓', '').trim();
            const arrow = currentSort.ascending ? ' <span style="color: #4caf50; font-weight: bold;">↑</span>' : ' <span style="color: #f44336; font-weight: bold;">↓</span>';
            activeLink.innerHTML = iconHTML + ' ' + text + arrow;
        }

        function sortTable(orderBy, ascending) {
            const tbody = table.querySelector('tbody');
            const sortedRows = [...rows].sort((a, b) => {
                let valA, valB;
                let comparison = 0;

                switch(orderBy) {
                    case 'F. Reg.':
                        valA = a.querySelector('td:nth-child(1)').textContent.trim();
                        valB = b.querySelector('td:nth-child(1)').textContent.trim();
                        comparison = compareDates(valA, valB);
                        break;

                    case 'Razón Social':
                        valA = a.querySelector('td:nth-child(2)').textContent.trim().toLowerCase();
                        valB = b.querySelector('td:nth-child(2)').textContent.trim().toLowerCase();
                        comparison = valA.localeCompare(valB);
                        break;

                    case 'Doc':
                        valA = a.querySelector('td:nth-child(3)').textContent.trim();
                        valB = b.querySelector('td:nth-child(3)').textContent.trim();
                        comparison = valA.localeCompare(valB);
                        break;

                    case 'N.Doc':
                        valA = parseInt(a.querySelector('td:nth-child(4)').textContent.trim()) || 0;
                        valB = parseInt(b.querySelector('td:nth-child(4)').textContent.trim()) || 0;
                        comparison = valA - valB;
                        break;

                    case 'Tel':
                        valA = a.querySelector('td:nth-child(5)').textContent.trim();
                        valB = b.querySelector('td:nth-child(5)').textContent.trim();
                        comparison = valA.localeCompare(valB);
                        break;

                    case 'Subagente':
                        valA = a.querySelector('td:nth-child(6)').textContent.trim().toLowerCase();
                        valB = b.querySelector('td:nth-child(6)').textContent.trim().toLowerCase();
                        comparison = valA.localeCompare(valB);
                        break;

                    case 'Email':
                        valA = a.querySelector('td:nth-child(7)').textContent.trim().toLowerCase();
                        valB = b.querySelector('td:nth-child(7)').textContent.trim().toLowerCase();
                        comparison = valA.localeCompare(valB);
                        break;

                    case 'Dirección':
                        valA = a.querySelector('td:nth-child(8)').textContent.trim().toLowerCase();
                        valB = b.querySelector('td:nth-child(8)').textContent.trim().toLowerCase();
                        comparison = valA.localeCompare(valB);
                        break;

                    default:
                        comparison = 0;
                }

                // Invertir el orden si es descendente
                return ascending ? comparison : -comparison;
            });

            tbody.innerHTML = '';
            sortedRows.forEach(row => tbody.appendChild(row));
        }

        function compareDates(dateA, dateB) {
            const parseDate = (str) => {
                const [day, month, year] = str.split('-');
                return new Date(year, month - 1, day);
            };

            const d1 = parseDate(dateA);
            const d2 = parseDate(dateB);
            return d1 - d2;
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
