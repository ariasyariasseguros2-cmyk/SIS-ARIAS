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

                fetch(`/menu/detalles-primas?id=${id}`)
                    .then(res => res.text())
                    .then(html => {
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(html, 'text/html');
                        // Extract the card body which contains the table
                        const content = doc.querySelector('.card-body');
                        
                        if (content) {
                            modalBody.innerHTML = '';
                            modalBody.appendChild(content);
                        } else {
                            // Fallback if structure is different
                            const container = doc.querySelector('.container-fluid');
                             if (container) {
                                modalBody.innerHTML = container.innerHTML;
                             } else {
                                modalBody.innerHTML = '<div class="alert alert-warning">No se pudo encontrar el contenido de detalles.</div>';
                             }
                        }
                    })
                    .catch(err => {
                        console.error(err);
                        modalBody.innerHTML = '<div class="alert alert-danger">Error al cargar los detalles</div>';
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
        if (t.classList.contains('btn-eliminar')) {
            openConfirm('¿Eliminar este registro?', () => {
                alert('Eliminado (demo).');
            });
        }
    });
})();
