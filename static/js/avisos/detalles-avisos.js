
document.addEventListener('DOMContentLoaded', () => {
    // Lógica específica para Detalles Avisos
    console.log('Detalles Avisos JS loaded');

    // Event Delegation para abrir el modal de detalles
    document.addEventListener('click', (e) => {
        const btnDetalles = e.target.closest('.btn-detalles');
        if (btnDetalles) {
            const id = btnDetalles.getAttribute('data-id');
            if (id) {
                const modalEl = document.getElementById('detallesAvisosModal');
                // Asegurarse de que bootstrap esté disponible
                if (typeof bootstrap !== 'undefined') {
                    let modal = bootstrap.Modal.getInstance(modalEl);
                    if (!modal) modal = new bootstrap.Modal(modalEl);
                    modal.show();

                    const modalBody = document.getElementById('detallesAvisosModalBody');
                    modalBody.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Cargando...</span></div></div>';

                    fetch(`/menu/detalles-avisos?id=${id}&partial=true`)
                        .then(res => res.text())
                        .then(html => {
                            modalBody.innerHTML = html;
                        })
                        .catch(err => {
                            console.error(err);
                            modalBody.innerHTML = '<div class="alert alert-danger m-3">Error al cargar detalles.</div>';
                        });
                } else {
                    console.error('Bootstrap no está cargado');
                }
            }
        }
    });
});
