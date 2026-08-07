(function () {
    const input = document.getElementById('primasSearch');
    const table = document.getElementById('primasTable');
    const pageSizeSelect = document.getElementById('page-size');

    let currentPage = 1;
    let currentPageSize = parseInt((pageSizeSelect && pageSizeSelect.value) || '0', 10);
    if (Number.isNaN(currentPageSize)) currentPageSize = 0;

    function applySearchAndPagination() {
        if (!table) return;
        const tbody = table.querySelector('tbody');
        if (!tbody) return;

        const rows = Array.from(tbody.querySelectorAll('tr.prima-row'));
        const q = (input ? input.value || '' : '').toLowerCase();

        let matched = [];
        for (const tr of rows) {
            const text = (tr.innerText || tr.textContent || '').toLowerCase();
            const passes = !q || text.includes(q);
            if (passes) matched.push(tr);
            tr.style.display = 'none';
        }

        const showAll = (currentPageSize <= 0);
        const size = showAll ? matched.length : currentPageSize;
        const totalPages = Math.max(1, Math.ceil(matched.length / Math.max(1, size)));
        if (currentPage > totalPages) currentPage = 1;
        const start = (currentPage - 1) * size;
        const end = start + size;

        for (let i = 0; i < matched.length; i++) {
            if (i >= start && i < end) {
                matched[i].style.display = '';
            }
        }

        const emptyRow = tbody.querySelector('tr.prima-empty-row');
        if (matched.length === 0 && emptyRow) {
            emptyRow.style.display = '';
        } else if (emptyRow) {
            emptyRow.style.display = 'none';
        }

        updateTotalCounter(matched.length, showAll);
    }

    function updateTotalCounter(visibleCount, showAll) {
        const footer = document.querySelector('.primas-footer .primas-total-text');
        if (footer) {
            const total = (table?.querySelectorAll('tbody tr.prima-row') || []).length || 0;
            if (showAll || visibleCount === total) {
                footer.textContent = `Total de registros: ${total}`;
            } else {
                footer.textContent = `Mostrando ${visibleCount} de ${total} registros`;
            }
        }
    }

    function markNegativeNumbers() {
        if (!table) return;
        const selectors = [
            { cls: 'num-neto' },
            { cls: 'num-comercial' },
            { cls: 'num-total' }
        ];
        table.querySelectorAll('tbody tr.prima-row').forEach(tr => {
            selectors.forEach(({ cls }) => {
                const el = tr.querySelector(`.${cls}`);
                if (!el) return;
                const raw = (el.textContent || '').replace(/[, ]/g, '').trim();
                const n = parseFloat(raw);
                if (!Number.isNaN(n) && n < 0) {
                    el.setAttribute('data-negative', 'true');
                } else {
                    el.removeAttribute('data-negative');
                }
            });
        });
    }

    if (input) {
        input.addEventListener('input', () => {
            currentPage = 1;
            applySearchAndPagination();
        });
    }

    if (pageSizeSelect) {
        pageSizeSelect.addEventListener('change', () => {
            const v = parseInt(pageSizeSelect.value || '0', 10);
            currentPageSize = Number.isNaN(v) ? 0 : v;
            currentPage = 1;
            applySearchAndPagination();
        });
    }

    // Modal Confirmation Helper
    let confirmModal = null;
    let confirmMessageEl = null;
    let confirmOkBtn = null;
    let confirmCallback = null;

    function openConfirm(message, onAccept) {
        if (!confirmModal) {
            const modalEl = document.getElementById('primasConfirmModal');
            if (modalEl && window.bootstrap) {
                confirmModal = new bootstrap.Modal(modalEl);
                confirmMessageEl = document.getElementById('primasConfirmMessage');
                confirmOkBtn = document.getElementById('btnPrimasConfirmOk');

                if (confirmOkBtn) {
                    confirmOkBtn.addEventListener('click', () => {
                        if (confirmCallback) {
                            const fn = confirmCallback;
                            confirmCallback = null;
                            fn();
                        }
                        confirmModal.hide();
                    });
                }
            }
        }

        if (!confirmModal || !confirmMessageEl) {
            if (confirm(message)) onAccept();
            return;
        }

        confirmMessageEl.textContent = message;
        confirmCallback = onAccept;
        confirmModal.show();
    }

    document.addEventListener('click', (e) => {
        const t = e.target.closest('button, a');
        if (!t) return;

        // ============ CUOTAS ============
        if (t.classList.contains('btn-cuotas')) {
            const poliza = t.getAttribute('data-poliza')
                || t.closest('tr')?.querySelector('.cell-poliza')?.textContent?.trim()
                || '';
            const idPrima = t.getAttribute('data-idprima') || '';
            const aviso = t.getAttribute('data-aviso') || '';
            if (poliza) {
                const params = new URLSearchParams();
                params.set('poliza', poliza);
                if (idPrima) params.set('idPrima', idPrima);
                if (aviso) params.set('aviso', aviso);
                window.location.href = `/menu/cuotas?${params.toString()}`;
            } else {
                alert('No se pudo obtener el número de póliza.');
            }
            return;
        }

        // ============ PDF (botón gris - antiguo .btn-pdf) ============
        if (t.classList.contains('btn-pdf')) {
            const isAnchor = t.tagName === 'A';
            const url = t.getAttribute('data-pdf') || t.getAttribute('href');
            if (isAnchor && t.getAttribute('href')) {
                return;
            }
            if (url) {
                window.location.href = url;
            } else {
                alert('No hay PDF disponible para este registro.');
            }
            return;
        }

        // ============ DETALLES ============
        if (t.classList.contains('btn-detalles')) {
            const id = t.getAttribute('data-id');
            if (id) {
                const modalEl = document.getElementById('detallesPrimasModal');
                let modal = bootstrap.Modal.getInstance(modalEl);
                if (!modal) {
                    modal = new bootstrap.Modal(modalEl);
                }
                modal.show();

                const modalBody = document.getElementById('detallesPrimasModalBody');
                modalBody.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Cargando...</span></div></div>';

                fetch(`/menu/detalles-primas?id=${id}&partial=true`)
                    .then(res => res.text())
                    .then(html => {
                        modalBody.innerHTML = html;
                    })
                    .catch(err => {
                        console.error(err);
                        modalBody.innerHTML = '<div class="alert alert-danger m-3">Error al cargar detalles.</div>';
                    });
            } else {
                alert('No se pudo obtener el ID para ver detalles.');
            }
            return;
        }

        // ============ EDITAR ============
        if (t.classList.contains('btn-editar')) {
            const id = t.getAttribute('data-id');
            if (id) {
                const modalEl = document.getElementById('editarPrimasModal');
                const modal = new bootstrap.Modal(modalEl);
                modal.show();

                const modalBody = document.getElementById('editarPrimasModalBody');
                modalBody.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Cargando...</span></div></div>';

                fetch(`/menu/primas-editar-form?id=${id}`)
                    .then(res => res.text())
                    .then(html => {
                        modalBody.innerHTML = html;
                        if (window.initEditarPrimasLogic) {
                            window.initEditarPrimasLogic(true);
                        }
                    })
                    .catch(err => {
                        console.error(err);
                        modalBody.innerHTML = '<div class="alert alert-danger">Error al cargar el formulario</div>';
                    });
            } else {
                alert('No se pudo obtener el ID del registro.');
            }
            return;
        }

        // ============ ANULAR PRIMA ============
        if (t.classList.contains('btn-anular-prima')) {
            const id = t.getAttribute('data-id');
            if (!id) { alert('No se pudo obtener el ID del registro.'); return; }

            const modalEl = document.getElementById('anularPrimaModal');
            let modal = bootstrap.Modal.getInstance(modalEl);
            if (!modal) modal = new bootstrap.Modal(modalEl);

            document.getElementById('anularPrimaId').value = id;
            document.getElementById('anularPrimaMotivo').value = '';
            document.getElementById('anularPrimaMotivoCount').textContent = '0';
            document.getElementById('anularPrimaFecha').value = new Date().toISOString().slice(0, 10);
            document.getElementById('anularPrimaError').classList.add('d-none');
            document.getElementById('anularPrimaError').textContent = '';

            modal.show();
            return;
        }

        // ============ ELIMINAR ============
        if (t.classList.contains('btn-eliminar') || t.classList.contains('action-delete')) {
            const tr = t.closest('tr');
            const id = t.getAttribute('data-id') || tr?.querySelector('.btn-detalles')?.getAttribute('data-id') || '';
            if (!id) {
                alert('No se pudo obtener el ID del registro.');
                return;
            }
            const poliza = tr?.querySelector('.cell-poliza')?.textContent?.trim() || '';
            const avisoCell = tr?.querySelector('.aviso-text')?.textContent?.trim() || '';
            const aviso = (avisoCell && avisoCell !== '—') ? avisoCell : '';

            openConfirm('¿Eliminar este registro?', async () => {
                try {
                    t.disabled = true;
                    const res = await fetch('/primas/delete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ idPrima: id, idPoliza: id, poliza, aviso })
                    });
                    const data = await res.json().catch(() => ({}));
                    if (res.ok && data && data.ok) {
                        if (tr) tr.remove();
                        applySearchAndPagination();
                        const tbody = table?.querySelector('tbody');
                        const rowsLeft = tbody ? tbody.querySelectorAll('tr.prima-row').length : 0;
                        if (tbody && rowsLeft === 0) {
                            let emptyRow = tbody.querySelector('tr.prima-empty-row');
                            if (!emptyRow) {
                                emptyRow = document.createElement('tr');
                                emptyRow.className = 'prima-empty-row';
                                const td = document.createElement('td');
                                td.colSpan = 14;
                                td.innerHTML = `
                                    <div class="primas-empty-state">
                                        <i class="bi-inbox"></i>
                                        <span>Sin registros de primas para esta póliza</span>
                                    </div>
                                `;
                                emptyRow.appendChild(td);
                                tbody.appendChild(emptyRow);
                            }
                            emptyRow.style.display = '';
                        }
                    } else {
                        const msg = (data && (data.error || (data.errors && data.errors.join(', ')))) || 'No se pudo eliminar';
                        alert(msg);
                    }
                } catch (err) {
                    console.error(err);
                    alert('Error al eliminar');
                } finally {
                    t.disabled = false;
                }
            });
            return;
        }
    });

    // ============ Modal anular prima handlers ============
    const motivoTextarea = document.getElementById('anularPrimaMotivo');
    const motivoCount = document.getElementById('anularPrimaMotivoCount');
    if (motivoTextarea && motivoCount) {
        motivoTextarea.addEventListener('input', () => {
            motivoCount.textContent = String(motivoTextarea.value.length);
        });
    }

    const btnConfirmar = document.getElementById('btnConfirmarAnularPrima');
    if (btnConfirmar) {
        btnConfirmar.addEventListener('click', async () => {
            const id = (document.getElementById('anularPrimaId') || {}).value || '';
            const motivo = ((document.getElementById('anularPrimaMotivo') || {}).value || '').trim();
            const fecha = (document.getElementById('anularPrimaFecha') || {}).value || null;
            const errorEl = document.getElementById('anularPrimaError');

            if (!motivo) {
                errorEl.textContent = 'El motivo es obligatorio.';
                errorEl.classList.remove('d-none');
                return;
            }
            if (motivo.length > 200) {
                errorEl.textContent = 'El motivo supera los 200 caracteres.';
                errorEl.classList.remove('d-none');
                return;
            }
            errorEl.classList.add('d-none');
            errorEl.textContent = '';

            btnConfirmar.disabled = true;
            try {
                const res = await fetch('/api/primas/anular', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ idPrima: id, motivo, fechaAnulacion: fecha })
                });
                const data = await res.json().catch(() => ({}));
                if (res.ok && data && data.ok) {
                    const modalEl = document.getElementById('anularPrimaModal');
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    if (modal) modal.hide();

                    const tr = table
                        ? table.querySelector(`button.btn-anular-prima[data-id="${id}"]`)?.closest('tr')
                        : null;
                    if (tr) {
                        tr.classList.add('prima-anulada');
                        const firstTd = tr.querySelector('td:first-child .cell-wrap');
                        if (firstTd && !firstTd.querySelector('.prima-badge-danger')) {
                            const badge = document.createElement('span');
                            badge.className = 'prima-badge prima-badge-danger';
                            badge.textContent = 'ANULADA';
                            firstTd.appendChild(badge);
                        }

                        // Ocultar todos los botones excepto PDF y DETALLES
                        tr.querySelectorAll('.btn-cuotas, .btn-editar, .btn-anular-prima, .btn-eliminar').forEach(btn => {
                            btn.remove();
                        });

                        // Si no quedó ningún botón, mostrar el mensaje
                        const col = tr.querySelector('.action-buttons-col');
                        if (col && col.querySelectorAll('.action-btn').length === 0) {
                            col.innerHTML = '<span class="prima-sin-acciones">Prima anulada</span>';
                        }
                    }
                    applySearchAndPagination();
                } else {
                    const msg = (data && (data.error || (data.errors && data.errors.join(', ')))) || 'No se pudo anular';
                    errorEl.textContent = msg;
                    errorEl.classList.remove('d-none');
                }
            } catch (err) {
                console.error(err);
                errorEl.textContent = 'Error de conexión al anular la prima.';
                errorEl.classList.remove('d-none');
            } finally {
                btnConfirmar.disabled = false;
            }
        });
    }

    markNegativeNumbers();
    applySearchAndPagination();
})();
