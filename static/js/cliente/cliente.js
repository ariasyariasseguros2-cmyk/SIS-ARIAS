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

        function showContactosModal(message) {
            const modalEl = document.getElementById('clienteContactosModal');
            const msgEl = document.getElementById('clienteContactosMessage');
            if (!modalEl || !msgEl || typeof bootstrap === 'undefined') {
                alert(message);
                return;
            }
            msgEl.textContent = message;
            bootstrap.Modal.getOrCreateInstance(modalEl).show();
        }

        function confirmDeleteCliente(message) {
            return new Promise((resolve) => {
                const modalEl = document.getElementById('clienteDeleteConfirmModal');
                const msgEl = document.getElementById('clienteDeleteConfirmMessage');
                const okBtn = document.getElementById('btnClienteDeleteOk');
                const cancelBtn = document.getElementById('btnClienteDeleteCancel');
                if (!modalEl || !msgEl || !okBtn || !cancelBtn || typeof bootstrap === 'undefined') {
                    resolve(window.confirm(message));
                    return;
                }

                msgEl.textContent = message;
                const modal = bootstrap.Modal.getOrCreateInstance(modalEl);

                const cleanup = () => {
                    okBtn.removeEventListener('click', onOk);
                    cancelBtn.removeEventListener('click', onCancel);
                    modalEl.removeEventListener('hidden.bs.modal', onHidden);
                };

                const onOk = () => {
                    cleanup();
                    try { modal.hide(); } catch (_) {}
                    resolve(true);
                };
                const onCancel = () => {
                    cleanup();
                    resolve(false);
                };
                const onHidden = () => {
                    cleanup();
                    resolve(false);
                };

                okBtn.addEventListener('click', onOk, { once: true });
                cancelBtn.addEventListener('click', onCancel, { once: true });
                modalEl.addEventListener('hidden.bs.modal', onHidden, { once: true });
                modal.show();
            });
        }

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
                                const polizasLabel = (r.ramo_btn_label || 'Póliza');
                                actionCellHtml = `
                                <td class="text-end">
                                    <div class="d-flex gap-2 justify-content-end">
                                        ${canEdit ? `<button type="button" class="btn btn-warning btn-sm btn-lift btn-edit-cliente" data-id="${r.idCliente}"><i class="bi-pencil"></i> Editar</button>` : ''}
                                        <button type="button" class="btn btn-primary btn-sm btn-lift">${polizasLabel}</button>
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

        const voiceBtn = document.getElementById('voiceSearchBtn');
        const voiceModalEl = document.getElementById('voiceSearchModal');
        const voiceStopBtn = document.getElementById('voiceStopBtn');
        const voiceStatus = document.getElementById('voiceStatus');
        const voiceText = document.getElementById('voiceText');
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        let recognition = null;
        let listening = false;

        if (voiceBtn) {
            voiceBtn.addEventListener('click', (e) => {
                if (!SR) {
                    alert('Tu navegador no soporta búsqueda por voz.');
                    e.preventDefault();
                    e.stopPropagation();
                }
            });
        }

        if (SR && voiceModalEl) {
            recognition = new SR();
            recognition.lang = 'es-ES';
            recognition.interimResults = true;
            recognition.maxAlternatives = 1;
            recognition.continuous = true;

            voiceModalEl.addEventListener('shown.bs.modal', () => {
                if (!recognition) return;
                voiceStatus.textContent = 'Escuchando...';
                voiceText.textContent = '';
                try { recognition.start(); listening = true; } catch (_) {}
            });

            voiceModalEl.addEventListener('hidden.bs.modal', () => {
                if (!recognition) return;
                if (listening) {
                    try { recognition.stop(); } catch (_) {}
                    listening = false;
                }
            });

            if (voiceStopBtn) {
                voiceStopBtn.addEventListener('click', () => {
                    if (!recognition) return;
                    if (listening) {
                        try { recognition.stop(); } catch (_) {}
                        listening = false;
                        voiceStatus.textContent = 'Detenido';
                    }
                });
            }

            recognition.addEventListener('result', (event) => {
                let finalText = '';
                let interim = '';
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) finalText += transcript;
                    else interim += transcript;
                }
                const shown = finalText || interim;
                voiceText.textContent = shown;
                if (finalText) {
                    const normalized = normalizeSpoken(finalText);
                    if (input) input.value = normalized;
                    debouncedFilter(normalized);
                    const m = (window.bootstrap && window.bootstrap.Modal.getInstance(voiceModalEl)) || (window.bootstrap && new window.bootstrap.Modal(voiceModalEl));
                    if (m) m.hide();
                }
            });

            recognition.addEventListener('error', () => {
                voiceStatus.textContent = 'Error de reconocimiento';
            });

            recognition.addEventListener('end', () => {
                listening = false;
                voiceStatus.textContent = 'Finalizado';
            });
        }

        function normalizeSpoken(text) {
            let t = (text || '').toLowerCase();
            t = t.replace(/\./g, ' ');
            t = t.replace(/\b(punto)\b/g, ' ');
            t = t.replace(/\b(punto\s+y\s+coma)\b/g, ';');
            t = t.replace(/\b(dos\s+puntos)\b/g, ':');
            t = t.replace(/\b(arroba)\b/g, '@');
            t = t.replace(/\b(guion\s+bajo|guión\s+bajo)\b/g, '_');
            t = t.replace(/\b(guion|guión)\b/g, '-');
            t = t.replace(/\b(numeral|hashtag|almohadilla)\b/g, '#');
            t = t.replace(/\b(coma)\b/g, ',');
            t = t.replace(/\b(porcentaje)\b/g, '%');
            t = t.replace(/\b(ampersand|y\s+comercial)\b/g, '&');
            t = t.replace(/\b(slash|barra|diagonal)\b/g, '/');
            t = t.replace(/\b(backslash|barra\s+invertida)\b/g, '\\\\');
            t = t.replace(/\b(mas|más|signo\s+mas|signo\s+de\s+mas)\b/g, '+');
            t = t.replace(/\b(menos|signo\s+menos)\b/g, '-');
            t = t.replace(/\b(igual|signo\s+igual)\b/g, '=');
            t = t.replace(/\b(asterisco)\b/g, '*');
            t = t.replace(/\b(interrogacion|interrogación|signo\s+de\s+interrogacion|signo\s+de\s+interrogación)\b/g, '?');
            t = t.replace(/\b(exclamacion|exclamación|signo\s+de\s+exclamacion|signo\s+de\s+exclamación)\b/g, '!');
            t = t.replace(/\b(parentesis\s+abre|paréntesis\s+abre)\b/g, '(');
            t = t.replace(/\b(parentesis\s+cierra|paréntesis\s+cierra)\b/g, ')');
            t = t.replace(/\b(corchete\s+abre)\b/g, '[');
            t = t.replace(/\b(corchete\s+cierra)\b/g, ']');
            t = t.replace(/\b(llave\s+abre)\b/g, '{');
            t = t.replace(/\b(llave\s+cierra)\b/g, '}');
            t = t.replace(/\b(comilla\s+simple)\b/g, "'");
            t = t.replace(/\b(comilla\s+doble)\b/g, '"');
            t = t.replace(/\b(be\s+larga)\b/g, 'b');
            t = t.replace(/\b(ve\s+larga)\b/g, 'v');
            t = t.replace(/\b(ve\s+corta)\b/g, 'v');
            t = t.replace(/\b(a)\b/g, 'a');
            t = t.replace(/\b(be)\b/g, 'b');
            t = t.replace(/\b(ce)\b/g, 'c');
            t = t.replace(/\b(de)\b/g, 'd');
            t = t.replace(/\b(e)\b/g, 'e');
            t = t.replace(/\b(efe)\b/g, 'f');
            t = t.replace(/\b(ge)\b/g, 'g');
            t = t.replace(/\b(hache)\b/g, 'h');
            t = t.replace(/\b(i)\b/g, 'i');
            t = t.replace(/\b(jota)\b/g, 'j');
            t = t.replace(/\b(ka)\b/g, 'k');
            t = t.replace(/\b(ele)\b/g, 'l');
            t = t.replace(/\b(elle)\b/g, 'll');
            t = t.replace(/\b(eme)\b/g, 'm');
            t = t.replace(/\b(ene)\b/g, 'n');
            t = t.replace(/\b(eñe)\b/g, 'ñ');
            t = t.replace(/\b(o)\b/g, 'o');
            t = t.replace(/\b(pe)\b/g, 'p');
            t = t.replace(/\b(cu)\b/g, 'q');
            t = t.replace(/\b(erre)\b/g, 'r');
            t = t.replace(/\b(ese)\b/g, 's');
            t = t.replace(/\b(te)\b/g, 't');
            t = t.replace(/\b(u)\b/g, 'u');
            t = t.replace(/\b(uve|ve)\b/g, 'v');
            t = t.replace(/\b(uve\s+doble|doble\s+ve|doble\s+u)\b/g, 'w');
            t = t.replace(/\b(equis)\b/g, 'x');
            t = t.replace(/\b(ye|i\s+griega)\b/g, 'y');
            t = t.replace(/\b(zeta)\b/g, 'z');
            t = t.replace(/\s{2,}/g, ' ').trim();
            return t;
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
            table.addEventListener('click', async (e) => {
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
                    showContactosModal(`Abrir contactos de: ${razon}`);
                } else if (btn.classList.contains('btn-delete-cliente')) {
                    // Anular cliente (borrado lógico)
                    const idCliente = btn.getAttribute('data-id');
                    const nombreCliente = btn.getAttribute('data-nombre');

                    const ok = await confirmDeleteCliente(`¿Está seguro de anular al cliente "${nombreCliente}"?`);
                    if (!ok) {
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
                            alert('Cliente anulado correctamente');
                            location.reload();
                        } else {
                            alert('Error: ' + (data.errors || ['Desconocido']).join(', '));
                        }
                    })
                    .catch(err => alert('Error de red: ' + err));
                } else if (btn.classList.contains('btn-hard-delete-cliente')) {
                    // Eliminación física — solo BROKER
                    const idCliente = btn.getAttribute('data-id');
                    const nombreCliente = btn.getAttribute('data-nombre');

                    const ok = await confirmDeleteCliente(`⚠️ ELIMINAR PERMANENTEMENTE al cliente "${nombreCliente}" junto con todas sus pólizas y cuotas. Esta acción es irreversible. ¿Continuar?`);
                    if (!ok) {
                        return;
                    }

                    fetch('/clientes/hard-delete', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({idCliente: idCliente})
                    })
                    .then(r => r.json())
                    .then(data => {
                        if (data.ok) {
                            alert('Cliente eliminado permanentemente');
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
