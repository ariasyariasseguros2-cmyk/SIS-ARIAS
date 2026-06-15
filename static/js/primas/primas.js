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

    // Modal Confirmation Helper
    let confirmModal = null;
    let confirmMessageEl = null;
    let confirmOkBtn = null;
    let confirmCallback = null;

    function openConfirm(message, onAccept) {
        // Inicializar elementos si no existen
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
        if (t.classList.contains('btn-detalles')) {
            const id = t.getAttribute('data-id');
            if (id) {
                // Open modal
                const modalEl = document.getElementById('detallesPrimasModal');
                // Check if modal instance already exists
                let modal = bootstrap.Modal.getInstance(modalEl);
                if (!modal) {
                    modal = new bootstrap.Modal(modalEl);
                }
                modal.show();

                // Load content
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
        }
        if (t.classList.contains('btn-editar')) {
            const id = t.getAttribute('data-id');
            if (id) {
                // Open modal
                const modalEl = document.getElementById('editarPrimasModal');
                const modal = new bootstrap.Modal(modalEl);
                modal.show();

                // Load content
                const modalBody = document.getElementById('editarPrimasModalBody');
                modalBody.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Cargando...</span></div></div>';

                fetch(`/menu/primas-editar-form?id=${id}`)
                    .then(res => res.text())
                    .then(html => {
                        modalBody.innerHTML = html;
                        // Init logic from editar-primas.js
                        if (window.initEditarPrimasLogic) {
                            window.initEditarPrimasLogic(true); // true = isModal
                        }
                    })
                    .catch(err => {
                        console.error(err);
                        modalBody.innerHTML = '<div class="alert alert-danger">Error al cargar el formulario</div>';
                    });
            } else {
                alert('No se pudo obtener el ID del registro.');
            }
        }
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
        if (t.classList.contains('btn-eliminar')) {
            const tr = t.closest('tr');
            const id = t.getAttribute('data-id') || tr?.querySelector('.btn-detalles')?.getAttribute('data-id') || '';
            if (!id) {
                alert('No se pudo obtener el ID del registro.');
                return;
            }
            const poliza = tr?.querySelector('td:nth-child(2)')?.textContent?.trim() || '';
            const avisoCell = tr?.querySelector('td:nth-child(1)')?.textContent?.trim() || '';
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
                        if (tr) {
                            tr.remove();
                        }
                        const totalEl = document.querySelector('.card-footer small.text-muted');
                        if (totalEl) {
                            const m = totalEl.textContent.match(/(\d+)/);
                            if (m) {
                                const n = Math.max(0, (parseInt(m[1], 10) || 1) - 1);
                                totalEl.textContent = `Total de registros: ${n}`;
                            }
                        }
                        const tbody = table?.querySelector('tbody');
                        if (tbody && tbody.querySelectorAll('tr').length === 0) {
                            const row = document.createElement('tr');
                            const td = document.createElement('td');
                            td.colSpan = 13;
                            td.className = 'text-center text-muted py-4';
                            td.textContent = 'Sin datos';
                            row.appendChild(td);
                            tbody.appendChild(row);
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
        }
    });
    // Contador de caracteres del motivo de anulación
    const motivoTextarea = document.getElementById('anularPrimaMotivo');
    const motivoCount = document.getElementById('anularPrimaMotivoCount');
    if (motivoTextarea && motivoCount) {
        motivoTextarea.addEventListener('input', () => {
            motivoCount.textContent = motivoTextarea.value.length;
        });
    }

    // Confirmar anulación de prima
    const btnConfirmar = document.getElementById('btnConfirmarAnularPrima');
    if (btnConfirmar) {
        btnConfirmar.addEventListener('click', async () => {
            const id = document.getElementById('anularPrimaId').value;
            const motivo = (document.getElementById('anularPrimaMotivo').value || '').trim();
            const fecha = document.getElementById('anularPrimaFecha').value || null;
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

                    // Marcar la fila como anulada (badge + opacidad) en lugar de eliminarla
                    const tr = table?.querySelector(`button.btn-anular-prima[data-id="${id}"]`)?.closest('tr');
                    if (tr) {
                        tr.classList.add('table-secondary', 'text-muted');
                        tr.style.opacity = '0.72';

                        // Agregar badge ANULADA junto al aviso (primera celda)
                        const firstTd = tr.querySelector('td:first-child');
                        if (firstTd && !firstTd.querySelector('.badge')) {
                            const badge = document.createElement('span');
                            badge.className = 'badge bg-danger ms-1';
                            badge.style.fontSize = '.65em';
                            badge.textContent = 'ANULADA';
                            firstTd.appendChild(badge);
                        }

                        // Eliminar botones de acción (editar, anular, eliminar) de la fila
                        tr.querySelectorAll('.btn-editar, .btn-anular-prima, .btn-eliminar').forEach(btn => btn.remove());
                    }
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
})();
