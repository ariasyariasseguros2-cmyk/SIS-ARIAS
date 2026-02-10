
document.addEventListener('DOMContentLoaded', () => {
    console.log('Editar Avisos JS loaded');

    // Event Delegation para abrir el modal de edición y acciones dentro del modal
    document.addEventListener('click', function(e) {
        
        // --- Abrir Modal de Edición ---
        const btnEditar = e.target.closest('.btn-editar');
        if (btnEditar) {
            const id = btnEditar.getAttribute('data-id');
            if (id) {
                const modalEl = document.getElementById('editarAvisosModal');
                if (typeof bootstrap !== 'undefined') {
                    let modal = bootstrap.Modal.getInstance(modalEl);
                    if (!modal) modal = new bootstrap.Modal(modalEl);
                    modal.show();

                    const modalBody = document.getElementById('editarAvisosModalBody');
                    modalBody.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Cargando...</span></div></div>';

                    fetch(`/menu/avisos-editar-form?id=${id}`)
                        .then(res => res.text())
                        .then(html => {
                            modalBody.innerHTML = html;
                        })
                        .catch(err => {
                            console.error(err);
                            modalBody.innerHTML = '<div class="alert alert-danger">Error al cargar el formulario</div>';
                        });
                }
            }
        }

        // --- Guardar Aviso (Upload/Update) ---
        const btnGuardar = e.target.closest('#btnGuardarAviso');
        if (btnGuardar) {
            e.preventDefault();
            const form = document.getElementById('editAvisosForm');
            if (!form) return;

            const fileInput = form.querySelector('input[type="file"]');
            const idInput = form.querySelector('input[name="id"]');
            const modalEl = document.getElementById('editarAvisosModal');
            
            // Caso 1: Se seleccionó un archivo nuevo
            if (fileInput && fileInput.files.length > 0) {
                 const file = fileInput.files[0];
                 const formData = new FormData();
                 formData.append('file', file);
                 
                 // UI Loading state
                 const originalText = btnGuardar.innerHTML;
                 btnGuardar.disabled = true;
                 btnGuardar.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Guardando...';

                 fetch('/upload', { method: 'POST', body: formData })
                    .then(r => r.json())
                    .then(data => {
                        if(data.error) throw new Error(data.error);
                        
                        // Update DB with new PDF URL
                        return fetch('/primas/update', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ 
                                idPrima: idInput.value, 
                                pdf_url: `polizas/${data.filename}` 
                            })
                        });
                    })
                    .then(r => r.json())
                    .then(res => {
                        if(!res.ok) throw new Error(res.error || 'Error al actualizar');
                        
                        // Success
                        alert('Aviso actualizado correctamente');
                        if(modalEl) {
                            const modal = bootstrap.Modal.getInstance(modalEl);
                            if(modal) modal.hide();
                        }
                        location.reload(); // Recargar para ver cambios
                    })
                    .catch(err => {
                        console.error(err);
                        alert('Error: ' + err.message);
                    })
                    .finally(() => {
                        btnGuardar.disabled = false;
                        btnGuardar.innerHTML = originalText;
                    });
            } else {
                // Caso 2: Solo guardar datos (si hubiera otros campos)
                // Por ahora solo hay archivo, así que si no hay archivo y no se borró, no hacemos nada o avisamos
                // Verificamos si hay intención de guardar cambios sin archivo (no aplica mucho aquí aun)
                alert('No se ha seleccionado ningún archivo nuevo.');
            }
        }

        // --- Eliminar Documento ---
        const btnDelete = e.target.closest('.btn-delete-document');
        if (btnDelete) {
             e.preventDefault();
             const id = btnDelete.getAttribute('data-id');
             
             if(confirm('¿Estás seguro de eliminar este documento permanentemente?')) {
                 const originalHtml = btnDelete.innerHTML;
                 btnDelete.disabled = true;
                 btnDelete.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

                 fetch('/primas/update', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ 
                        idPrima: id, 
                        pdf_url: '' // Empty string to clear
                    })
                 })
                 .then(r => r.json())
                 .then(res => {
                     if(!res.ok) throw new Error(res.error || 'Error al eliminar');
                     
                     alert('Documento eliminado');
                     // Recargar formulario o cerrar modal
                     location.reload();
                 })
                 .catch(err => {
                     console.error(err);
                     alert('Error: ' + err.message);
                     btnDelete.disabled = false;
                     btnDelete.innerHTML = originalHtml;
                 });
             }
        }
    });
});
